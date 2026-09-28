"""Validate Anna's Realtime session while printing only safe status metadata."""

import asyncio
import json
import os
import re
from urllib.parse import quote

from src.telephony.profiles import phone_session_config
from websockets.asyncio.client import connect


def safe(value: object) -> str:
    text = str(value or "unknown")
    return text if re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", text) else "redacted"


async def main() -> None:
    session, _, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    model = quote(str(session["model"]), safe="")
    async with connect(
        f"wss://api.openai.com/v1/realtime?model={model}",
        additional_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        open_timeout=15,
        close_timeout=3,
    ) as socket:
        await socket.send(json.dumps({"type": "session.update", "session": session}))
        async with asyncio.timeout(15):
            while True:
                event = json.loads(await socket.recv())
                kind = event.get("type")
                if kind == "session.updated":
                    print("session_updated")
                    return
                if kind == "error":
                    error = event.get("error") or {}
                    print(
                        "error",
                        f"type={safe(error.get('type'))}",
                        f"code={safe(error.get('code'))}",
                        f"param={safe(error.get('param'))}",
                    )
                    return


asyncio.run(main())
