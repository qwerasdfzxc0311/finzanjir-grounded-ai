# Resilient public research answers

## Purpose

FINZANJIR should not depend on a single search provider or hosted answer model. General questions are answered from local source-backed facts first. When local knowledge is insufficient, Auto mode can use cached public extracts, Tavily, and then Wikimedia's public encyclopedia API. The answer is composed locally from source passages.

## Request flow

1. Classify the question. FINZANJIR project questions remain inside the project knowledge corpus; they are not silently replaced with public web results.
2. Prefer an existing local general-knowledge fact when one directly covers the question.
3. Check the bounded, six-hour in-process cache of previously retrieved public extracts. This avoids repeating the same external search during the current service process.
4. For stable encyclopedic questions, try Wikimedia's language-specific Wikipedia API first, reducing Tavily usage. For explicit web searches and time-sensitive questions, try Tavily first.
5. If the first provider is unavailable, rate-limited, quota-exhausted, unconfigured, or returns passages that cannot support an answer, try the other provider when it is suitable for the question.
6. The local composer filters unsafe URLs, extracts relevant sentences, ranks them using query overlap and provider relevance, removes duplicates, and returns source links.
7. If public research still cannot support an answer, Auto mode may try the existing optional LLM gateway. If no provider can support an answer, abstain rather than inventing facts.

## Provider resilience

- Tavily is a primary broad public-web search provider, not the required answer-generating LLM. It is not called first for stable encyclopedic questions when Wikimedia is a better low-cost fit.
- HTTP 429 opens a 15-minute Tavily cooldown. Tavily HTTP 432 (plan usage limit) and 433 (pay-as-you-go limit) are classified as quota exhaustion and open a 30-minute cooldown. HTTP 401/403 authentication or permission failures also open a 30-minute cooldown. Temporary network/provider failures open a short 60-second cooldown.
- During cooldown, new questions skip Tavily and proceed directly to Wikimedia when the topic is suitable. This avoids repeatedly spending requests against a provider that has already reported a limit or outage.
- Wikimedia is an independent, keyless encyclopedia fallback, not a full replacement for broad web search. It is suitable for stable encyclopedic topics; it may not find current events, niche pages, or all Karakalpak-language material.
- Successful public extracts are cached in memory for up to six hours, with a maximum of 128 query entries. The cache is process-local and may be cleared by a service restart or deployment.
- Gemini and OpenRouter are optional. When local composition has sufficient source evidence, neither is called.
- The local answer composer is deterministic and extractive. It selects and orders source passages; it does not claim free-form human-level reasoning or independently verify every external claim.

## Trust and data boundaries

- Search requests pass the existing sensitive-identifier guard. Do not send bank, customer, card, account, identity, or complaint data to public search.
- External pages are untrusted input. Their instructions are never executed or followed; the local composer only extracts and ranks text.
- Only HTTPS source links without embedded credentials are returned.
- Search results and extracted passages are not automatically promoted into the canonical FINZANJIR knowledge base or training data.
- Project-authoritative facts, external research, and author-provided material remain separate.
- The displayed confidence is a retrieval-quality heuristic, not a calibrated probability or a guarantee that the source claim is true.

## Acceptance checks

- A local fact card answers without Tavily, Wikimedia, or hosted LLM calls.
- An unsupported general question can be answered from Tavily extracts without Gemini/OpenRouter.
- Tavily HTTP 429, 432, and 433 failures skip repeat Tavily calls during cooldown and use Wikimedia where relevant.
- If Tavily is not configured, Wikimedia can still provide a locally composed answer for a supported encyclopedic query.
- A successful extract is reused from the process cache without another Tavily call.
- Explicit Offline mode makes no external search request.
- FINZANJIR-specific questions do not silently fall back to public web sources.
- Insufficient evidence produces an honest abstention with source links.
