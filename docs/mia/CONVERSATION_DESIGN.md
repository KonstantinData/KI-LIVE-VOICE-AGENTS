# Conversation design

Status: user-directed behavior requirements, 2026-10-15. The local conversation sketch contains scripted examples only. No MIA voice runtime, emotional classifier or audible laughter has been implemented or live-tested.

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

For a selected wall, always show the interior-facing wall elevation and an unambiguous left-to-right direction. Missing dimensions remain unknown. Only ask exact opening widths/offsets when available and decision-relevant; do not turn the discovery conversation into an unbounded measuring exercise.

The reference images are design inputs, not a verified dealer assortment or redistribution license. This change does not copy their photographs or catalog artwork into public assets.

## Two-to-three-minute target

Following the [senior workshop](TEAM_WORKSHOP_RESULTS.md), the primary target is conversation start to the first visible personalized furnished concept, including visitor speech, pauses, planning and rendering. Discovery duration is a diagnostic subinterval, not a substitute for that outcome. Later revisions are measured separately. The earlier scripted examples do not establish this speed.

Adapt order to the visitor's answer and skip filled fields. Use one question per turn. Preserve short pauses and interruptions; avoid unnecessary confirmations, repeated paraphrases and a forced closing recap.

Prioritize personal must-haves/must-avoids, coarse room feasibility, intended use, visual preferences and optional budget. After about 150 seconds, avoid opening optional detail topics. A short transition can be “Ich zeige Ihnen eine erste Idee. Danach können wir gezielt etwas verändern.”

Measure actual discovery duration including visitor speech and pauses, and the complete first-result interval above. The time target and 70-80% perceived-match hypothesis remain unproven until real participant tests. Do not claim that a fixed script or fast tapping guarantees them. Reaching 150 seconds is not a reason to begin an unbounded rendering wait; the end-to-end time remains the primary measure.

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
