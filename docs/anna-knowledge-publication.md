# Anna knowledge publication - 2026-09-25

The owner requested immediate publication of the reviewed reception knowledge.
The nine reviewed chunks now replace the previous active `anna.json` contents.
The separate `anna.reception.draft.json` is retained as the review snapshot.
Earlier draft-only statements in the review describe the preparation stage.

Only the active knowledge file was uploaded to `/opt/anna`; the Anna image was
rebuilt and the Anna container recreated without restarting Asterisk.
The previous knowledge file is retained solely for rollback at
`/opt/anna/backups/knowledge-20260925/anna.json`.

Verification: 115 telephony tests passed. The running container loaded nine
approved, currently usable chunks with active publication metadata. Local and
container SHA-256 matched:
`6cc8f5dd7cc4884f05e21d4b7564a4c783bd53dae5441901bd6e1297a5225a36`.
Anna's SIP contact was present and Easybell remained registered.
No comparison phone call was performed for this content-only deployment.

This publication does not implement the proposed reception prompt, CRM caller
lookup, or phone-only CRM handoff. Those remain separate tracked work.
