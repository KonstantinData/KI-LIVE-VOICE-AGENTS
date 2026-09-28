# Anna's public business knowledge

`anna.json` is the curated German telephone knowledge snapshot for
`anna-phone-assistant` only. It is loaded into each new call's instructions.
The website agent KEA continues using `chunks.json`; no other tenant inherits
Anna's scope. This is a maintained local knowledge base, not live web retrieval.

## Sources and review

Reviewed on **2026-09-21** using the public website source files in the separate
`mein-kuechenexperte` repository and public web retrieval of
[the website](https://mein-kuechenexperte.de/) and its service pages, particularly
[published prices](https://mein-kuechenexperte.de/preise).

Source checkout:
`D:/Git-GitHub/Repositories/02_mein_kuechenexperte/mein-kuechenexperte`.
HEAD: `a95fd465bca3d076e81331bb3b99524bc08f0f07`.
The checkout contains uncommitted content changes; hashes below identify the
actual inspected files rather than implying that HEAD contains this snapshot.
No CRM records, customer files, credentials, or private configuration were used.

Web retrieval exposed different cached publication ages. The price page agreed
with the current product catalog. A cached contact page still showed EUR 49.80
for an older strategy product; the current catalog and newer price page show
EUR 149. Direct HTTP verification returned 403 for both www and canonical hosts.
Accordingly, this snapshot is repository-verified and cross-checked against
available public page snapshots, not proof that every detail is currently deployed.
Each chunk records its supporting repository path(s), public URL and review window.
The approval marker means selected for this curated snapshot, not separate owner
sign-off or a live publication check.

## Conflict decisions and unknowns

- Use the current strategy consultation at EUR 149; exclude the stale EUR 49.80.
- Project support catalog entries declare hybrid delivery and a Stuttgart area
  check; detailed pages say coordination is online and implementation support
  has separately quoted onsite work. Do not promise nationwide booking eligibility
  or included onsite visits for those packages. Confirm project eligibility.
- Marketing mentions installation plans and all revisions. Detailed planning
  terms restrict these to preliminary interfaces, with at most two revisions in
  the highest planning package. Do not promise execution-ready trade plans.
- Published processing periods are package descriptions, not live availability;
  do not promise deadlines starting today.
- The imprint address is a correspondence address, not a verified showroom.
  Its phone number does not identify Anna's assigned incoming SIP number.
- Opening hours, live appointments, individual quotations and customer order
  status are unknown. Anna has no booking, transfer, callback or CRM tools.
- Website intake and booking workflows describe actions callers can take later.
  They do not grant Anna website, payment, upload or calendar capabilities.

## Maintenance

Review prices and service terms by **2026-10-21**, and stable identity/process facts
by **2026-12-20**. Expired, future-reviewed, unapproved, private or untraceable chunks
are omitted automatically; Anna then states that she cannot confirm missing facts.
An invalid file or incorrect tenant/scope fails closed. There is no automatic
crawler or scheduled refresh. Do not extend dates without rechecking the sources.

To update: inspect the current public catalog and corresponding service pages,
resolve discrepancies conservatively, edit `anna.json`, update source hashes and
review dates, then run `python -m pytest tests/test_telephony -q` and
`python -m ruff check src tests`. The loader reads the file for each new call;
an ongoing conversation retains its initial snapshot. After deploying loader or
prompt code changes, restart Anna when no call is in progress.

## Source file SHA-256 snapshot

| Public source path | SHA-256 |
| --- | --- |
| `www/includes/products.php` | `86e656a559593896540db234dcb0ffdbad7d89dee17a18571212dfba56217476` |
| `www/preise.php` | `a710c6c37416c9116c8bccde5b511ae00ca09159970b16e69ebbc86f522d2d47` |
| `www/fachplanung.php` | `38ea4e5249b951f352422b9c19457443dc36c9fdf0ab4e44374a548a0fb3a35a` |
| `www/coaching.php` | `e70b47b34f5d1f946db9ea7c9f1c6c4b3affb6d6bab59598eeab960e70ff70a2` |
| `www/angebot_und_planung_pruefen.php` | `e90b2bc4604646c2741cecdeca1d92f7e277f34678719a7813f900c3d9eb0208` |
| `www/projektbegleitung.php` | `b946087982cb802e5dd1f74d1ec509cb4eed3f1c9f69b7c28edbc63634ed1b5e` |
| `www/quick_check_termin.php` | `905c5972891bf240e963850dd7c9768ab6881c0960f91bd17df558f0998c69ce` |
| `www/strategie_check_termin.php` | `85f0eadb411f69a1316e6af064ef882b6d2571553d050b3cb96da8e7d731fcc7` |
| `www/kontakt.php` | `6a0f2f5bd77fd19f3e5e22eb2d2d9bea413929fd6f5b9bfcc9b2ceac7e1b79ee` |
| `www/impressum.php` | `363dcd5440462c9e86ec622bd8909f19970b8eb2a662c5ab4319e5db71d1844e` |
| `www/faq.php` | `26116ffe04a81644860007f368cdec8c8bf1b5cff939a7268ddb14c07ff8dab9` |
