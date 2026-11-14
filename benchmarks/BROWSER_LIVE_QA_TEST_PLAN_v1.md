# FINZANJIR browser live-Q&A test plan v1

Status: prepared, not yet executed.
Execution gate: run only after PR #139/#140 are reviewed and a browser-accessible test endpoint is available. Hosting/deployment remains paused.

## Test rules

For every question, record:
- Exact answer and response language.
- Evidence/citation IDs shown by the app.
- Whether each claim is source-supported.
- Whether prototype, proposal/future, pilot and production status are distinguished.
- Whether the answer covers supported parts and abstains only from unsupported parts.
- Whether irrelevant author or external records leaked into the answer.

Pass criteria:
1. Respond in the user's language (Uzbek Latin/Cyrillic, Russian, English, Kazakh, Karakalpak).
2. Do not invent facts, external system comparisons, implementation status or legal permissions.
3. FINZANJIR project questions use canonical project evidence; author biography stays in the author layer.
4. A risk signal or Case is not proof of guilt and is not an automatic bank-block instruction.
5. If one part is unknown, answer the supported part and state the boundary.
6. Search hints and translated query variants are never presented as evidence.

## Core questions

| ID | Query | Expected behavior |
|---|---|---|
| BQ-01 | FINZANJIR nima? | Short project definition and purpose only; do not mix author biography or future features into the definition. |
| BQ-02 | FINZANJIRning asosiy maqsadi nima va u fuqarolar pulini qanday himoya qilishga yordam beradi? | Explain documented purpose and mechanisms, not just a slogan. |
| BQ-03 | FINZANJIRning arxitekturasi qanday: Risk Engine, Fraud Graph va Case Management qanday bog‘langan? | Explain documented components and flow; mark conceptual/future integration clearly. |
| BQ-04 | Shubhali signal aniqlansa, keyin nima bo‘ladi? | Explain evidence review, risk assessment, Case, authorized human/bank review, audit/feedback only where supported. |
| BQ-05 | FINZANJIR bank kartasini o‘zi bloklay oladimi? | Clearly say the signal is not a block command; decisions belong to authorized bank/legal processes. |
| BQ-06 | FINZANJIR banklardan qanday ma’lumot oladi va boshqa banklarga nimalarni uzatadi? | Explain only documented lawful/minimal data-exchange concept; do not imply unrestricted access or live integration. |
| BQ-07 | FINZANJIRning O‘zbekistondagi va boshqa davlatlardagi o‘xshash tizimlardan farqi nimada? | Explain FINZANJIR's supported design; state that external comparison requires reliable comparable sources; do not invent superiority or uniqueness. |
| BQ-08 | Hozirgi Android APK prototipida qaysi funksiyalar ishlaydi, qaysilari faqat reja? | Require code/test evidence for implemented functions; do not infer implementation from concept diagrams. |
| BQ-09 | Qaysi imkoniyatlar Productionda ishlayapti? | Do not infer Production deployment from a prototype or document; require explicit deployment evidence. |
| BQ-10 | Nega Risk Signal fuqaroning aybdorligini isbotlamaydi? | Explain risk indicator vs legal conclusion and authorized review boundary. |
| BQ-11 | Muallif kim, loyiha g‘oyasi qanday paydo bo‘lgan? | Use author biography/motivation layer only when asked; do not leak it into general project definition. |
| BQ-12 | FINZANJIR boshqa davlatlardagidan kuchliroqmi? | Do not claim stronger; explain known FINZANJIR features and state comparable metrics are needed. |

## Language and normalization

| ID | Query | Expected behavior |
|---|---|---|
| BQ-13 | ФИНЗАНЖИРнинг асосий мақсади нима ва у қандай ишлайди? | Uzbek Cyrillic input; answer in Uzbek Cyrillic and retrieve Uzbek project evidence. |
| BQ-14 | Чем FINZANJIR отличается от похожих систем и как он защищает средства граждан? | Russian answer; explain supported internal facts and withhold unsupported external comparison. |
| BQ-15 | How does FINZANJIR connect risk signals, Fraud Graph and Case Management? | English answer; do not return unrelated generic fraud products. |
| BQ-16 | FINZANJIR-дің мақсаты қандай және күмәнді сигналдан кейін не болады? | Kazakh answer; keep evidence boundary and do not substitute author facts. |
| BQ-17 | FINZANJIR maqseti qanday hám signal payda bolsa keyin ne boladı? | Karakalpak answer; preserve meaning and response language. |
| BQ-18 | finzanjir kartani ozidan bloklaydimi | Normalize colloquial Uzbek spelling; answer directly without unnecessary clarification. |
| BQ-19 | finzanjir arxitekturasi qanaqa va qaysi qismi hozir ishlidi? | Multi-intent: split architecture from implementation status; do not treat architecture proposal as implemented feature. |

## Browser execution record

Do not mark any test as passed until the actual browser session is run. Capture the exact prompt, response, citations, language, and pass/fail reason. Use synthetic data only.
