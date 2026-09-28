# Anna reception knowledge review

Review date: 2026-09-25. Active area: mein-kuechenexperte.de.

## Delivery status and authority

This is a preparation record, not a runtime activation or deployment.
The prepared source is
`registry/tenants/mein-kuechenexperte/knowledge/anna.reception.draft.json`.
The runtime loader remains pointed at `anna.json`.
Chunk metadata `status=approved` means its public factual content passed this
review; `publication_status=draft-not-active-not-deployed` separately records
that the source is not activated. Review expiry is 2026-10-09.
The role contract in `docs/anna-reception-role.md` governs behavior. Public
website facts are only for understanding requests, never a mandate to advise.
No private CRM records were read and no CRM capability is established here.

Source repository:
`D:/Git-GitHub/Repositories/02_mein_kuechenexperte/mein-kuechenexperte`.
Reviewed the sitemap, navigation, corresponding local PHP content and shared
templates, then fetched fresh public HTML for the routes below. All 40 sitemap
routes and four supplemental routes returned HTTP 200 at their final destination.
This is content verification, not form submission, booking or browser testing.

## Route inventory

All paths below are relative to `https://mein-kuechenexperte.de`.
Except root routes, local page sources are `www/<route>.php`; the English
root is `www/en/index.php`. The German root renders
`www/includes/_shared/editorial-home.php` through `www/index.php`.

| Group | Reviewed routes | Result and treatment |
| --- | --- | --- |
| Home | /, /en/ | 200; German editorial homepage is current; English uses older presentation |
| New project situations | /neubau, /renovierung, /orientierung | 200; intake topic labels only |
| Rooms | /wohnen, /esszimmer, /hauswirtschaftsraum, /vorratsraum, /backkitchen | 200; room categories only |
| Services and fees | /leistungen, /preise, /en/services, /en/pricing | 200; current individually agreed scope and fees |
| Planning and review | /fachplanung, /angebot_und_planung_pruefen, /en/specialist_planning, /en/review_offer_and_planning | 200; topic scope and responsibility limits |
| People and examples | /ueber-uns, /en/about | 200; provider identity, no inferred staff routing |
| Questions | /faq, /en/faq | 200; current scope and process |
| Articles | /blog-article, /en/blog-article | 200; excluded from curated facts because legacy copy remains |
| Resources | /downloads, /en/downloads | 200; public checklist/template catalogue, not consultation instructions |
| Contact | /kontakt, /en/contact | 200; current email verified including Cloudflare email decoding |
| Upload | /datei-upload, /en/file-upload | 200; after agreement/approval; legacy German title excluded |
| Introduction | /quick_check_termin, /en/quick_check_appointment | 200; free 15-minute introduction and needs assessment |
| Legal notice | /impressum, /en/imprint | 200; legacy public phone is not Anna's telephony configuration |
| Privacy | /datenschutz, /en/privacy-policy | 200; not used as evidence of current CRM/Anna architecture |
| Terms | /agb, /en/terms-and-conditions | 200; current scope and existing agreements preserved |
| Accessibility | /barrierefreiheit, /en/accessibility | 200; not used for runtime promises |
| Supplemental guide | /ratgeber | 200; legacy package wording excluded |
| Supplemental references | /referenzen | redirects to /ueber-uns; final 200 |
| Legacy supervision | /projektbegleitung | redirects to /leistungen; final 200 |
| Supplemental special services | /spezialleistungen | 200; no new detailed advisory facts imported |

The sitemap contains 24 German and 16 English routes. The supplemental routes
were checked because navigation or legacy service references exposed them.
This inventory covers public content pages, not internal APIs, CRM screens,
payment handlers or every downloadable document.

## Curated facts and excluded advice

The draft contains nine public chunks: company identity, request topics, rooms,
human service process, free introduction, individually agreed fees, professional
responsibilities, existing agreements and current public email.
Ankleiden, sideboards and wall units are explicitly covered in specialist
planning/FAQ despite not having standalone sitemap routes.

No old fixed packages, entry prices, credits for new purchases, guaranteed
variant counts, callback deadlines, savings guarantees, technical instructions,
staff availability, appointment-booking ability or private project status are
introduced. An existing contract remains subject to its original agreement;
the new website does not retroactively remove its agreed terms.

## Conflicts and ingestion precautions

- The unused `$homeContent` array in `www/index.php` still contains old packages.
  The actual current German page is the editorial shared template. Do not ingest
  raw PHP as if every string were visible current content.
- Live `/ratgeber` and `/blog-article` retain package/stage wording and fixed
  variant counts. The current pricing, FAQ, services and terms take precedence
  for this draft. Do not import those legacy claims.
- The German upload title still says documents for the Quick-Check. This does
  not create a current paid check product or authorize advance document intake.
- Privacy pages describe OVH/Brevo and older chatbot processing. They do not
  verify Anna's current processing, CRM identity lookup or actual retention.
- Legal pages publish +49 711 39080786; do not overwrite Anna's configured
  Easybell number from website text.
- Search-engine page retrieval returned cached old prices. Fresh HTTP confirmed
  the revised scope-based offer. Use rendered current content and dated evidence.
- Public contact email was verified by decoding Cloudflare protection:
  `kontakt@mein-kuechenexperte.de`. No internal mail transport credentials or
  private routing configuration belong in public knowledge.

Website consistency remediation is separate work in the website repository.
No source website files were edited by this review.

## Authoritative local source fingerprints

SHA-256 values below identify reviewed local source bytes. They are not hashes
of rendered HTTP responses. Paths are relative to the source repository above.

| Source | SHA-256 |
| --- | --- |
| www/includes/_shared/editorial-home.php | 69f22d84c16400a710d06a35fc54fb2149be1d6e6713fd17ef06f604905ec04e |
| www/preise.php | 0cf8b86050c17b31b19985cd5199417ca1e5c26a747aa3727865ea3b2c86e3ee |
| www/faq.php | f4269fa8875db72c497b328cbb5c31cfcdd7a9f9a821d0060d71c91e7082d1f3 |
| www/leistungen.php | e5fed34059ffecfcab716b808a2730a16705dd764998b962467ac9076038ea36 |
| www/fachplanung.php | e0b28d016780ce90bdb9854c00e2475dd7b2545c1bf6490c3ef2a1a108407e8b |
| www/angebot_und_planung_pruefen.php | ef3c39f3a0f40e5216009c1f0803cf9c9a8da4cb7bde8ce270cbf8e30f464e6b |
| www/kontakt.php | a60499ad74d5338b0d06486f492782a1cdb05630d6960ebba202032a4aa85b6d |
| www/quick_check_termin.php | 092e46cfeb7b6e96186c70d5b40cc163bf821e8086a880a9b4ac321f58ca7482 |
| www/agb.php | ccdb1f0e058dd3e5573a7e09f215f03122129edad635a693769e23038c03377d |
| www/sitemap.xml | 7afc48bb44b875f57cccd8bb3bea417aa607db72abb8d52192bc54c4dc2277f5 |

Representative fresh HTTP SHA-256 observations on 2026-09-25:

| URL path | SHA-256 |
| --- | --- |
| / | 965961f1f32eb2b9888ca74f27e01d56223d7e5af772cc302caaa5f4254425e9 |
| /preise | 616bee27855dfbc03ec6752c7fdf761eabb95f1d76c315ae3e1fbd608a71e611 |
| /faq | 0e249b74f116660e003f14c3ceb52c8eecd51ff01fb239befc7095cf758bb54d |
| /fachplanung | 423043dd566b8acd1b6b08b6eca3bedeaa99e9eef5dd0305394636b3abc9be35 |

Dynamic security tokens and Cloudflare processing can change full-page hashes
without changing visible facts; these are dated observations, not future
availability assertions.

## Activation boundary

Before activation, integrate and verify the reception role and its tools.
Validate the draft with `TenantKnowledgeSource` and each chunk with
`usable_public_fact(today=date(2026, 9, 25))`. Keep runtime loading `anna.json`
until the combined change is intentionally activated. This document does not
claim that the stale active knowledge has already been replaced.
