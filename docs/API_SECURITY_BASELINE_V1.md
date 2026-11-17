# FINZANJIR API Security Baseline v1

## Scope

This baseline describes the current prototype API and its explicit data/authority boundaries. It does not claim bank-grade or regulator-certified security, and it does not change FINZANJIR's core risk logic, data contracts, or bank-authority model.

## Implemented controls

- Browser CORS is same-origin only by default. Cross-origin access requires an exact comma-separated `FINZANJIR_ALLOWED_ORIGINS` allowlist; wildcard origins, invalid schemes, and duplicate origins are rejected at startup.
- Credentialed CORS is enabled to support the Google owner-session cookie, but cross-origin access is limited to explicitly allowlisted origins. The configured methods are GET, POST, DELETE and OPTIONS; the only explicitly allowed request header is Content-Type.
- State-changing Google owner routes validate the request Origin against the API origin and the configured exact allowlist. This is an additional browser-origin/CSRF boundary, not a replacement for session authentication.
- The Google owner-session cookie is HttpOnly, Secure and SameSite=Lax. The current Google connector is single-owner, not a general multi-user or bank-operator identity system.
- API responses receive `Cache-Control: no-store` and `Pragma: no-cache`.
- Browser security headers include CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy and Cross-Origin-Resource-Policy.
- `/api/prototype/run` and the shadow-evaluation endpoints reject non-synthetic input. The prototype execution path overwrites client-supplied `cross_bank_authorized` with `false`; the public prototype cannot authorize cross-bank access.
- `/api/google/*` is a separately configured, owner-only Google connector. It uses OAuth Authorization Code + PKCE, encrypted server-side refresh tokens, read-only service scopes, owner-session checks, selected-item imports and private quarantine. Missing configuration fails closed.
- `/api/research/*` is a separate external-research path. Search results are labelled as external sources and are not automatically ingested into the canonical FINZANJIR knowledge base.

## API data boundaries

| Route family | Current boundary |
|---|---|
| `/api/prototype/*` | Synthetic-only demonstration and shadow evaluation; no real bank/customer transactions and no cross-bank authorization |
| `/api/ai/answer` | Project-grounded answer path; retrieved project evidence and provider generation remain subject to the grounded-answer and abstention rules |
| `/api/google/*` | Single configured owner; selected Google content is encrypted and kept in private quarantine, not automatically promoted to canonical project knowledge |
| `/api/research/*` | Explicit external search; returned sources remain external and separate from project facts |

The Google Drive and Gmail scopes currently requested are broad restricted scopes. A user selecting one item for import does not narrow the OAuth token's underlying permission. See the Google scope gate in `docs/architecture/SECURE_CLOUD_CONNECTORS.md` and `docs/operations/GOOGLE_CLOUD_SETUP.md`.

## Configuration

Example for a separately hosted approved frontend:

```bash
FINZANJIR_ALLOWED_ORIGINS=https://prototype.example
```

Leave the variable unset when the frontend is served from the same origin. Do not use `*`. When Google owner login is configured, `FINZANJIR_FRONTEND_URL` must exactly match one of the allowed HTTPS origins.

## Important limitations

- CORS is a browser policy, not user authentication or API authorization. The Google connector has a single-owner session boundary; the repository does not yet provide general multi-user RBAC, bank IAM, or bank-operator identity.
- The plugin capability registry and tool-call envelope are policy/validation components only. No live ChatGPT plugin inventory is connected, no permission can be granted by FINZANJIR, and the envelope does not execute tools.
- This baseline does not claim to provide bank-grade identity, privileged access management, general API rate limiting, durable production audit storage, cross-bank authorization, or a production incident-response/SOC capability.
- The current Render Free API service has ephemeral storage. Google imports must remain disabled until the database/media persistence, backup and restore gates in the Google setup runbook are satisfied.
- Google restricted-scope eligibility, OAuth verification and any required security assessment must be resolved before public activation. Read-only access is not automatically exempt from these requirements.

## External design references

- OWASP API Security Top 10 (2023): https://owasp.org/API-Security/editions/2023/en/0x00-header/
  - Relevant risks include broken object/function authorization, broken authentication, excessive exposure at object-property level, unrestricted resource consumption and security misconfiguration.
- NIST SP 800-207 Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/final
  - Network location alone must not imply trust; authenticate and authorize users/devices before access to protected resources.
- Starlette CORS middleware: https://www.starlette.io/middleware/#corsmiddleware
  - Credentialed CORS requires explicit origins, methods and headers rather than wildcard configuration.
- Google restricted-scope verification: https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification

These are technical and platform-policy references, not a statement that the prototype complies with a financial regulator or is certified to a security standard.
