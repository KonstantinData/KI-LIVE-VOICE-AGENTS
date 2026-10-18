# MKX agents

MKX (Mein Kuechenexperte) is the tenant. Its agents have separate roles:

- **KEA**: website reception and controlled project intake. Runtime and text/voice
  prompt sections live in [`kea`](kea). Identity comes from the tenant registry;
  studio knowledge comes from `registry/tenants/mein-kuechenexperte/knowledge`.
- **MIA**: planning assistant. Existing requirements and architecture live in
  [`docs/mia`](../../../docs/mia/README.md). [`mia`](mia) contains independent
  prompt sections and offline text/voice builders only. It is not part of KEA;
  no runtime MIA agent, endpoint, registry activation or planner is supplied by
  this content cleanup.
- **Anna**: telephone assistant. Her independent prompt, knowledge and calendar
  package lives in [`anna`](anna). Shared telephone transport remains in
  [`src/telephony`](../../telephony).

Approved follow-up, 2026-10-18: relocate all of the former `src/agents/anna`
package, including `calendar`, under this MKX directory and update imports/start
assets. Telephone/calendar behavior, agent/profile IDs and authority do not
change. `deploy/anna` and `deploy/anna-server` remain in place. This is a local
source reorganization, not deployment or new live acceptance. Earlier inventory
and implementation receipts describe their historical paths and remain intact.

[`shared`](shared) holds selected role-neutral MKX conversation policy and
business context. Goals, examples, address/channel behavior and tool/contact
authority stay explicitly assigned to each agent; Anna does not automatically
inherit shared prompts. KEA owns its deterministic `text_flow.py` and
`text_flow_nodes.py` along with text/voice composition. Shared infrastructure
belongs to runtime/core rather than another agent's prompt package.

MIA's documented flow uses bounded prepared layouts in a raster scene before
actual-room adaptation. Initial dialogue is at most 120 seconds, with no room,
window, door or connection questions before the first draft, no spoken recap
and optional contact only after a visible concept and refinement. Offline
prompts express these requirements; they do not execute furniture selection,
rendering, revisions or booking. Agent-bound session/project authorization and
an explicit MIA runtime/profile remain separate work. Neither uninterrupted
long-speech handling nor the diagram's 10x10 m scene is decided here.

See [ADR 0003](../../../docs/adr/0003-mkx-agent-ownership.md) for approval and
validation boundaries. Historical structural-migration tests are not evidence
of a working or live-tested MIA planner.
