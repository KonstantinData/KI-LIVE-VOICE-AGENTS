# Deployment Runbook

## Production Backend

- Hetzner project: `KI-TEAM`
- Hetzner project ID: `13631345`
- Server name: `ki-team-prod-nbg1-01`
- Server ID: `122362831`
- Direct SSH host: `46.225.221.42`
- Runtime path: `/var/www/ki-team`
- systemd service: `ki-team-api`
- Public API hostname: `api.mein-kuechenexperte.de`

Do not SSH to `api.mein-kuechenexperte.de`. The public API hostname is proxied
through Cloudflare and resolves to Cloudflare edge IPs, not the Hetzner VM.

If SSH reports a host key mismatch, verify the current server in the Hetzner
Console before updating `known_hosts`. As of 2026-07-07, the expected known host
fingerprints for `46.225.221.42` were:

- ED25519: `SHA256:Xv6ky9ckxSVA2pQ1GJXgVn0WJiyd4f+z7NCnqBt5fd8`
- RSA: `SHA256:IVQj/Zhbb5yH2wGQumOAgiKUM5f6IZ1zbOK5ZAQtZfQ`
- ECDSA: `SHA256:+RZ6GCUQY8NMFnaLWEqsj0VmD7+4L/0UTvtZmQiq1kw`

## Backend Deploy

```bash
ssh root@46.225.221.42 "cd /var/www/ki-team && \
  git fetch origin main && \
  git merge --ff-only origin/main && \
  venv/bin/pip install -r requirements.txt && \
  venv/bin/alembic upgrade head && \
  systemctl restart ki-team-api && \
  systemctl is-active ki-team-api && \
  git rev-parse --short HEAD"
```

## Verification

```bash
curl https://api.mein-kuechenexperte.de/health
```

CRM/dashboard routes are intentionally not served by this backend. For example,
`/dashboard/costs` should return `404`; AI usage and contact data are handed off
to the CRM endpoints in the `mein-kuechenexperte` repository.
