# FINZANJIR API Security Baseline v1

## Scope

This baseline hardens the public-facing prototype API without changing FINZANJIR's core risk logic, data contracts, synthetic-only boundary, or bank-authority model.

## Implemented controls

- Browser CORS is same-origin only by default. Cross-origin access requires an explicit comma-separated `FINZANJIR_ALLOWED_ORIGINS` environment allowlist.
- Wildcard origins, invalid schemes, and duplicate origins are rejected at startup.
- CORS credentials are disabled; only GET, POST and OPTIONS are allowed; only Content-Type is allowed as a request header.
- API responses receive `Cache-Control: no-store` and `Pragma: no-cache`.
- Browser security headers: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy and Cross-Origin-Resource-Policy.
- The prototype API still accepts only explicitly synthetic transaction/scenario input. The public endpoint does not trust client-supplied cross-bank authorization.

## Configuration

Example for a separately hosted approved frontend:

```bash
FINZANJIR_ALLOWED_ORIGINS=https://prototype.example
```

Leave the variable unset when the frontend is served from the same origin. Do not use `*`.

## Important limitation

CORS is a browser policy, not user authentication or API authorization. This change does not claim to provide bank-grade identity, role-based access, rate limiting, durable audit storage, or cross-bank authorization. Those controls require their own server-side identity and policy design before any real data or bank integration is enabled.

## External design references

- OWASP API Security Top 10 (2023): https://owasp.org/API-Security/editions/2023/en/0x00-header/
  - Relevant risks include broken object/function authorization, broken authentication, excessive exposure at object-property level, unrestricted resource consumption and security misconfiguration.
- NIST SP 800-207 Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/final
  - Network location alone must not imply trust; authenticate and authorize users/devices before access to protected resources.

These are technical design references, not a statement that the prototype is compliant with a financial regulator or certified security standard.
