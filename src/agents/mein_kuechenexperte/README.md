# MKX agents

MKX (Mein Kuechenexperte) is the tenant. Its agents have separate roles:

- **KEA**: website reception and controlled project intake. Runtime and text/voice
  prompt sections live in [`kea`](kea). Identity comes from the tenant registry;
  studio knowledge comes from `registry/tenants/mein-kuechenexperte/knowledge`.
- **MIA**: planning assistant. The current prompt journey is described in
  [`mia/README.md`](mia/README.md); earlier requirements and architecture live in
  [`docs/mia`](../../../docs/mia/README.md). [`mia`](mia) contains independent
  prompt sections and offline text/voice builders only. It is not part of KEA;
  no runtime MIA agent, endpoint, registry activation or planner is supplied by
  this content cleanup.
- **Anna**: telephone assistant. Her independent prompt, knowledge and calendar
  package lives in [`anna`](anna). Shared telephone transport remains in
  [`src/telephony`](../../telephony).

Anna's former `src/agents/anna` package, including `calendar`, is now under this
MKX directory. `deploy/anna` and `deploy/anna-server` remain operational asset
directories. Package ownership does not change telephone/calendar authority or
agent/profile IDs. Earlier inventory and implementation receipts describe their
historical paths and remain intact.

[`shared`](shared) holds selected role-neutral MKX conversation policy and
business context. Goals, examples, address/channel behavior and tool/contact
authority stay explicitly assigned to each agent; Anna does not automatically
inherit shared prompts. KEA owns its deterministic `text_flow.py` and
`text_flow_nodes.py` along with text/voice composition. Shared infrastructure
belongs to runtime/core rather than another agent's prompt package.

MIA aims for an approximately two-minute introduction covering five essentials:
coarse room situation and preferred kitchen form, style, colors/material
appearance, a central desired feature and explicit exclusions. It then guides
the visitor through a photorealistic design idea in an example room, qualitative
feedback and a few focused refinements. Budget orientation, uploads and personal
consultation are optional follow-up steps. Viewing, refining and downloading an
image must not require contact details; a private, time-limited continuation link
is also part of the intended journey. The prompts require each capability to
exist before MIA offers or confirms it. They do not implement image generation,
UI controls, storage, upload handling, continuation links or booking. An explicit
MIA runtime/profile and session/project authorization remain separate work.

See [ADR 0003](../../../docs/adr/0003-mkx-agent-ownership.md) for approval and
validation boundaries. Historical structural-migration tests are not evidence
of a working or live-tested MIA planner.
