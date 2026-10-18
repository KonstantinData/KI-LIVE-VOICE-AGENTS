# Conversation design

Status: user-directed behavior requirements, 2026-10-15. The local conversation sketch contains scripted examples only. No MIA voice runtime, emotional classifier or audible laughter has been implemented or live-tested.

Reconciled 2026-10-18: the later raster-first instruction takes precedence over
the earlier measured-room-first workshop. See [the current product requirements](PRODUCT_REQUIREMENTS.md)
and [raster-first draft](RASTER_FIRST_DRAFT_DE.md). Local offline prompt builders
are conversation artifacts; they do not select furniture, render concepts or
activate a MIA session/profile.

## Conversation leads

MIA conducts a short personal conversation. It listens, retains useful preferences in structured state, and moves to one relevant next question. It does not recite a visitor's answer, read a running requirements summary aloud, or repeatedly ask visitors to prioritize their own quoted words.

Do not use stock transitions such as “Für Ihr Konzept halte ich fest: …”, “Ich fasse zusammen: …” or an automatic “Habe ich alles richtig verstanden?” before every transition. Acknowledgments are optional and brief. Corrections are handled locally; clarify the specific ambiguity rather than replaying the whole brief.

Internal structured facts, provenance, uncertainty and selected version references remain necessary. They do not require a spoken recap. An optional editable overview may be available on request. Explicit consent for contact processing and exact booking/action confirmation remain required; this conversation rule does not remove those authority gates.

## Deliver value before requesting contact

The visitor must understand at entry that MIA will develop and display an initial kitchen concept during this experience. First-concept access and refinement require no name, email, phone or postcode form. Privacy/processing consent remains separately scoped; do not describe the experience as involving no data processing.

The first result must be a visible concept tied to the visitor's preferences and stated/assumed room model. A generic stock photo, hidden result, appointment request or promise to send something later does not close this product requirement. Do not promise a measured completion time or 70-80% match until evaluation supports it.

After the visitor has seen the concept and can adjust it, offer optional adviser follow-up/booking. Ask postcode, first name, last name, email and phone through the protected form at this point. Phone is optional in the proposed preview; production field requirements follow the actual chosen contact purpose. Never request these identifiers through uncontrolled voice, use them as a condition for the first image, or save them in visualization host state.

Example entry copy: “Hallo, ich bin MIA. Wir entwickeln gemeinsam eine erste Küchenidee, die Sie hier direkt sehen und verändern können. Kontaktdaten brauchen Sie nur, wenn Sie anschließend eine Beratung möchten.”

Example transition after showing the result: “Möchten Sie diese Idee mit einem Berater weiterentwickeln?” The visitor may continue exploring or leave without contact submission. Advisor handoff includes only the consented selected project/version and allowed context.

Cooking habits, renovation/new build, intended budget and target installation time may inform the concept or next-step timing; skip information already supplied. Ownership and decision-maker questions are conditional, not mandatory sales-qualification gates before value is delivered. A target date is a customer preference, not a delivery promise. Do not copy the reference budget slider's default as the visitor's stated budget.

Keep intake accepted, CRM delivered, verification email sent, email verified and appointment confirmed as separate authoritative states. The reference success screen supplies interaction inspiration only; it does not establish that MKE sends offers from three companies, operates the shown phone number, or has an email-verification service. Never display “sent/confirmed” without the corresponding real receipt.

## Natural examples

| Visitor | Example next turn |
|---|---|
| “Ich möchte mit meiner Familie kochen können. Es soll warm und gemütlich wirken, und ich brauche mehr freie Arbeitsfläche.” | “Kochen Sie meistens zu zweit, oder hilft die ganze Familie mit?” |
| “Beim Kochen muss ich dauernd etwas wegräumen. Das nervt mich inzwischen richtig.” | “Das kann einem die Freude am Kochen nehmen. Was steht Ihnen dabei am häufigsten im Weg?” |
| “Mein Mann ist der Chefkoch. Ich bin vor allem für die Qualitätskontrolle zuständig.” | “Die Qualitätskontrolle muss schließlich stimmen. Braucht Ihr Chefkoch viel freie Arbeitsfläche?” |
| Visitor taps a refrigerator option | “Soll auch ein Gefrierfach dabei sein?” |
| Visitor does not know an opening dimension | “Kein Problem, das lassen wir erst einmal offen.” |

Examples illustrate tone; they are not mandatory phrases or fixed branches for a production agent. Existing preferences must affect the next question: do not ask about a family, freezer, kitchen form or material again when that information is already known.

## Empathy and light humor

- Be warm, attentive and concise. Acknowledge a real frustration or meaningful wish when useful; do not invent emotions or agree with every statement reflexively.
- Match the visitor's tone. Gentle humor may respond to a humorous remark. A brief natural laugh or chuckle is allowed when the moment genuinely invites it.
- Never schedule laughter after a fixed number of turns or trigger it merely because a keyword appears. A family-cooking preference is not automatically a joke.
- Keep frustration, personal difficulties, cost concerns and sensitive disclosures free of joking or laughter. Do not ridicule a visitor or another person.
- Do not claim personal human experiences. MIA remains openly identified as AI.
- Do not speak stage directions such as “lacht” or inject canned laughter text. Whether the selected voice can deliver appropriate nonverbal expression requires actual voice evaluation. Text remains a natural sentence without artificial giggle markers.

## Selective visual support

The user's supplied reference screens illustrate kitchen shape, room openness, style, color, worktop materials, oven placement, refrigerator integration and refrigerator type. They are optional visual aids, not a mandatory sequential picture questionnaire. The duplicate worktop reference is one topic, not a second question.

Use a visual when it reduces ambiguity or visitor effort. Omit it when spoken information already answers the question. Keep an opened room diagram visible and update its openings during the conversation rather than replacing it with a new image after every turn.

Separate room openness from desired kitchen shape. Separate refrigerator integration, appliance type and nominal width. A broad choice such as “wood” establishes a visual/material preference, not a verified manufacturer SKU, price or specific solid-wood construction.

### Appliance appearance: customer choice

The user's correction replaces a blanket fully-integrated-appliance default with a short adaptive preference question. Example: “Möchten Sie Kühlschrank und Geschirrspüler hinter den Möbelfronten verschwinden lassen, oder sollen einzelne Geräte sichtbar bleiben?” Accept a mixed answer in the same turn; store integration separately for each appliance. A fully integrated dishwasher and a visible side-by-side refrigerator are a valid combination. Refrigerator type, integration and width remain separate fields; do not infer an exact width from “side-by-side”. Skip already answered parts and respect retained appliances. If time is short, leave unresolved choices open for refinement rather than adding a mandatory appliance questionnaire.

Furniture-led design and discreet extraction remain possible design preferences, not universal customer requirements. Ovens and the cooktop may remain visible in this design direction. Ask about extraction separately only when relevant; an answer about the refrigerator or dishwasher does not determine it. Any unconfirmed visual choice used in the first draft is a changeable proposal, not a stated customer preference.

Only after the first visible raster-room draft, when actual-room adaptation is
chosen, show a selected wall's interior-facing elevation with an unambiguous
left-to-right direction. Missing dimensions remain unknown. Ask exact opening
widths/offsets only when available and decision-relevant at that later stage.
Before the first draft, ask no room, window, door or connection questions;
unsolicited room information is retained for later without opening measurement intake.

The reference images are design inputs, not a verified dealer assortment or redistribution license. This change does not copy their photographs or catalog artwork into public assets.

## Current raster-first timing and discovery

The initial conversation is capped at 120 seconds, including both speakers,
pauses and interaction. The regular first presentation for every visitor is a
wish-driven draft in a neutral raster scene, using a prepared layout and bounded
allowed adjustments. No free CAD planning or actual-room fit is implied.

Adapt order to the visitor's answer and skip filled fields. Use one question per turn. Preserve short pauses and interruptions; avoid unnecessary confirmations, repeated paraphrases and a forced closing recap.

Prioritize cooking use, desired improvement, atmosphere and must-haves/retained
devices. Known answers replace questions. Ask no room, window, door or connection
questions before the first draft, including optional exceptions. Budget and
device details are not additional mandatory qualification. The workshop's
recommendation is to stop opening exploration topics around 90 seconds and
transition early: “Ich zeige Ihnen eine erste Idee. Danach können wir gezielt
etwas verändern.” This recommendation does not prove the 120-second cap.

Measure initial dialogue, rendering wait and complete start-to-visible-result
duration separately. The earlier 2-3-minute total-result target is historical
workshop guidance, not a replacement for the current dialogue cap or a proven
performance claim. Neither timing nor 70-80% perceived match has been validated.
Do not hide an unlimited render wait or relabel continued discovery as refinement.

Handling uninterrupted visitor speech past the cap remains unresolved; no hard
audio cut is approved. The diagram's 10x10 m scene is an unconfirmed assumption,
not a customer-room measurement or adopted scene constant. Both need decisions
before corresponding runtime behavior is implemented.

## Acceptance checks

- The family example advances to a relevant usage question without quoting or summarizing the answer.
- Existing answers are not asked again; interruptions and corrections update the next turn.
- Warm acknowledgment is proportionate; humor appears only with suitable context and never during distress/cost concerns.
- Real voice evaluation separately checks natural timing, interruptions and optional laughter/chuckles; text examples are not voice proof.
- Picture aids are conditional; “unknown” works without blocking concept discovery.
- Internal structured preferences remain consistent even when no recap is spoken.
- Secure-form consent and exact booking confirmation remain explicit and independently tested.
- The first concept and allowed refinements work with empty postcode/contact fields. Contact remains an optional next step after real visible value; a failed generation never triggers a forced lead form as a replacement result.
- The scripted contact preview does not send data, save identifiers in widget state, or claim an email/request was delivered. Production integration still requires its separate approved contracts and tests.
