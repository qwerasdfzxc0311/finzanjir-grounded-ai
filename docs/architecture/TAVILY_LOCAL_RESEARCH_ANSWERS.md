# Tavily-backed local research answers

## Purpose

FINZANJIR can answer some stable general questions from its local, source-backed fact cards. When Auto mode receives a general-knowledge question that the local corpus cannot answer, it may use Tavily to discover public sources and then compose a response locally. Gemini and OpenRouter are not required for this path.

## Request flow

1. Classify the question. FINZANJIR project questions remain inside the project knowledge corpus; they are not silently replaced with public web results.
2. Prefer an existing local general-knowledge fact when one directly covers the question.
3. If the request is in Auto mode and the local corpus abstains, call Tavily Search with bounded result count and extracted page content.
4. The local composer filters unsafe URLs, extracts relevant sentences, ranks them using query overlap and Tavily relevance, removes duplicates, and returns source links.
5. If no relevant extract can be supported, abstain and show the candidate sources rather than inventing an answer.

## Model independence

- Tavily is the public-web discovery and extraction provider, not the required answer-generating LLM.
- The answer composer is deterministic and extractive. It selects and orders source passages; it does not claim free-form human-level reasoning or translate arbitrary source text.
- The search answer path reports `provider_status=not_attempted`; Gemini and OpenRouter are not called when Tavily provides enough extractable evidence.
- If Tavily is unavailable or its results cannot support an answer, Auto mode may fall back to the existing optional language-model gateway. Explicit Offline mode never calls Tavily or hosted LLMs.

## Trust and data boundaries

- Search requests still pass the existing sensitive-identifier guard. Do not send bank, customer, card, account, identity, or complaint data to public search.
- External pages are untrusted input. Their instructions are never executed or followed; the local composer only extracts and ranks text.
- Only HTTPS source links without embedded credentials are returned.
- Search results and extracted passages are not automatically promoted into the canonical FINZANJIR knowledge base or training data.
- Project-authoritative facts, external research, and author-provided material remain separate.
- The displayed confidence is a retrieval-quality heuristic, not a calibrated probability or a guarantee that the source claim is true.

## Acceptance checks

- A general-knowledge question outside local fact cards can be answered in Auto mode from Tavily results while the LLM gateway is not called.
- Existing local facts remain available without network access.
- Explicit Offline mode makes no external search request.
- FINZANJIR-specific questions do not silently fall back to public web sources.
- Insufficient evidence produces an honest abstention with source links.
