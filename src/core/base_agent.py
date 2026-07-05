"""
Base Agent Class
================
What:    Abstract base class for all AI agents in the system.
Does:    Implements the 7-step agent loop: context loading, intent recognition, knowledge retrieval,
         tool provisioning, LLM invocation, tool execution, and result persistence.
Why:     Ensures all agents follow the same processing pattern; reduces code duplication.
Who:     All concrete agents (Lisa, Max, Anna, Tom, Sara) inherit from this.
Depends: sqlalchemy, structlog, src.core.{knowledge, llm, memory, tool_registry, tool_runner, types},
         src.db.models.{conversation, message, studio}
"""

from abc import ABC, abstractmethod
import json
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.knowledge import KnowledgeBase
from src.core.llm import LLMClient
from src.core.memory import MemoryManager
from src.core.tool_registry import ToolRegistry
from src.core.tool_runner import ToolRunner
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.studio import Studio

log = structlog.get_logger()


class BaseAgent(ABC):
    """
    Abstrakte Basisklasse für alle KI-Agenten.

    Jeder Agent durchläuft bei einer eingehenden Nachricht
    den gleichen 7-Schritte-Prozess:
    1. Kontext laden (Studio, Lead, History)
    2. Absicht erkennen
    3. Wissen abrufen (Wissensbasis durchsuchen)
    4. Tools bereitstellen
    5. LLM aufrufen (OpenAI mit System-Prompt + Tools)
    6. Tool-Calls ausführen (falls vorhanden)
    7. Ergebnis speichern + zurückgeben

    Subklassen implementieren:
    - get_system_prompt() -> str
    - get_tools() -> ToolRegistry
    - get_knowledge_categories() -> list[str]
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._llm = LLMClient()
        self._memory = MemoryManager(session)
        self._knowledge = KnowledgeBase(session)

    @abstractmethod
    def get_system_prompt(
        self,
        studio: Studio,
        knowledge_snippets: list[str],
        lead_summary: str | None,
    ) -> str:
        """Gibt den System-Prompt für diesen Agenten zurück."""
        ...

    @abstractmethod
    def get_tools(self) -> ToolRegistry:
        """Gibt die Tool-Registry mit allen verfügbaren Tools zurück."""
        ...

    @abstractmethod
    def get_knowledge_categories(self) -> list[str]:
        """Gibt die Kategorien zurück, die dieser Agent in der Wissensbasis sucht."""
        ...

    async def process_message(
        self,
        user_message: str,
        conversation: Conversation,
        studio: Studio,
    ) -> str:
        """
        The 7-step agent loop. NOT overridden by subclasses.

        Processes a message and returns the response as a string.
        
        Args:
            user_message: The user's input message
            conversation: Current conversation object
            studio: Studio configuration and context
            
        Returns:
            Agent's response as string
        """
        log.info(
            "agent.process_message",
            studio=studio.slug,
            conversation_id=str(conversation.id),
        )

        # Step 1: Load context (conversation history + lead summary)
        context = await self._memory.get_context(conversation.id, studio.id)

        # Step 2+3: Retrieve knowledge
        # NOTE: We search the knowledge base semantically using the user's message.
        # This allows the agent to reference studio-specific product info, pricing, etc.
        knowledge_chunks = await self._knowledge.search(
            query=user_message,
            studio_id=studio.id,
            categories=self.get_knowledge_categories(),
            limit=5,
        )
        knowledge_snippets = [
            f"**{chunk.title}**\n{chunk.content}" for chunk in knowledge_chunks
        ]

        # Step 4: Build system prompt with context
        system_prompt = self.get_system_prompt(
            studio=studio,
            knowledge_snippets=knowledge_snippets,
            lead_summary=context.lead_summary,
        )

        # Step 5: Call LLM with tools
        tool_registry = self.get_tools()
        tool_runner = ToolRunner(tool_registry)
        messages = context.messages + [{"role": "user", "content": user_message}]

        response = await self._llm.chat(
            system_prompt=system_prompt,
            messages=messages,
            tools=tool_runner.get_tool_definitions() or None,
        )

        # Step 6: Execute tool calls (if any)
        # NOTE: OpenAI may return tool calls instead of text. We execute those tools,
        # then call the model again with the results to get the final text response.
        final_response = response
        if response.tool_calls:
            tool_results = await tool_runner.execute_all(response.tool_calls)
            messages_with_tools = messages + [
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["input"]),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                },
                *tool_results,
            ]
            final_response = await self._llm.chat(
                system_prompt=system_prompt,
                messages=messages_with_tools,
            )

        # Step 7: Persist messages to database
        await self._save_message(conversation.id, "user", user_message)
        await self._save_message(
            conversation.id,
            "assistant",
            final_response.content,
            tool_calls=response.tool_calls if response.tool_calls else None,
            token_count=final_response.input_tokens + final_response.output_tokens,
        )

        return final_response.content

    async def _save_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        token_count: int | None = None,
    ) -> None:
        """
        Persists a message to the database.
        
        Args:
            conversation_id: ID of the conversation
            role: Message role ("user" or "assistant")
            content: Message text content
            tool_calls: Optional list of tool calls made by the agent
            token_count: Optional token usage for cost tracking
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            token_count=token_count,
        )
        self._session.add(message)
