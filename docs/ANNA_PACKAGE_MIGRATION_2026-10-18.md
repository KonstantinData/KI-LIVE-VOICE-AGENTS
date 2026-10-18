# Anna MKX package migration receipt

Date: 2026-10-18. Active area: mein-kuechenexperte.de / MKX.
State: explicitly approved migration implemented and checked locally.
No commit, push, deployment or real call was performed.

## Delivered layout

All eleven Python files from `src/agents/anna`, including its complete calendar
package, now live in `src/agents/mein_kuechenexperte/anna`. The verified empty
old directories were removed. KEA, MIA and Anna now have independent packages
under the same MKX owner; package placement conveys no shared authority.

The common telephone transport remains in `src/telephony`. Its only source
change is the import of Anna's prompt in `profiles.py`. `deploy/anna` and
`deploy/anna-server` remain operational directories at their previous locations.

Updated repository call sites include:

- Anna's internal knowledge import and the telephony profile loader.
- All affected phone/calendar tests and monkeypatch module paths.
- `activate-calendar.py`, `calendar-smoke.py` and
  `calendar-cleanup-test-events.py` in `deploy/anna-server`.
- Both the source/destination of the calendar Dockerfile's `COPY` instruction
  and the Uvicorn module entry point:
  `src.agents.mein_kuechenexperte.anna.calendar.app:app`.
- Current Anna/MKX ownership documentation and ADR 0003.

`Dockerfile.anna` already copies all of `src` and starts `src.telephony`, so its
entry point needs no change. The relocated calendar leaf remains usable in the
minimal calendar image without copying KEA, MIA or their dependencies.

Historical inventories and the earlier content-cleanup implementation receipt
retain their source paths as dated evidence. Old-path references there are not
current start instructions.

## Preserved behavior and authority

Both the parent verification and an independent review compared every relocated
Python file with its pre-move content. All eleven match after normalizing only
the old-to-new import namespace and line endings. No prompt wording, calendar
configuration, scheduling logic, OAuth logic or storage logic was rewritten.

SHA-256 checks also confirmed unchanged tenant registry, Anna knowledge JSON,
calendar policy JSON, telephone calendar tools, CLI/autostart source and primary
Anna/calendar Compose definitions. Tenant/agent IDs, phone routing, calendar
rights, service names, environment names and data paths therefore stay as before.
Knowledge discovery remains anchored through the tenant registry; no deeper
`__file__` adjustment was required inside the relocated package.

## Validation

Interpreter: `D:/Git-GitHub/Repositories/condata/KI-LIVE-VOICE-AGENTS/venv/Scripts/python.exe`.
Working directory: `mia-phase-zero` worktree.

- Ruff over `src tests`: passed.
- Ruff over the three changed deployment Python helpers: passed.
- Combined existing agent/API/upload/handoff/telephone/calendar selection:
  **630 passed**, one Starlette/httpx deprecation warning. Selection matches the
  command in the [content-cleanup receipt](AGENT_CLEANUP_IMPLEMENTATION_2026-10-18.md).
- `python -B -m src.telephony --help`: passed without starting call handling.
- Isolated Python import check: reproduced the calendar Dockerfile's actual
  `COPY` file layout in a temporary directory and imported its configured
  Uvicorn app from that directory. Passed, without importing KEA or MIA.
- Copied calendar smoke/cleanup helper scripts parsed successfully; their real
  provider actions were not executed.
- Independent namespace/source/deployment review: no blocking findings.
- No actionable old namespace remains in source, tests or deployment assets.

No Docker image build, container start, live calendar transaction or real phone
call is claimed. Those checks belong to the separate deployment/live acceptance
step. Current branch and working-tree changes remain local and uncommitted.
