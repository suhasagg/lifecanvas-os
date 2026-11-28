# Security

| Area | Control |
| --- | --- |
| Authentication | Email + password, PBKDF2-SHA256 with per-user salt; opaque session tokens stored hashed; HttpOnly, SameSite=Strict cookie; server-side revocation |
| Authorisation | Every query is scoped by the session's user id; cross-user access returns "not found" |
| CSRF | State-changing requests need `X-Requested-With: lifecanvas` and a same-origin `Origin` |
| Headers | Strict CSP (`script-src 'self'`, no inline scripts or handlers), `X-Frame-Options: DENY`, `nosniff`, trusted-host check |
| Input validation | Pydantic models with length limits, 200 KB body limit, per-client and login rate limits |
| Prompt injection | Sentinel screens requests; blocked requests call no tool or model |
| Untrusted content | Provider text is screened; instruction-like text is withheld from prompts, answers and memory |
| Least privilege | Per-agent read-tool allowlists enforced at call time; write adapters only in the action graph |
| Approvals | Digest-bound, single-use, expiring; duplicate detection; dependency checks; ledger of every transition |
| Unknown outcomes | Timeout or 5xx after sending is stored as `unknown` and never retried |
| Outbound requests | HTTPS only, host allowlists, private/loopback/link-local addresses rejected, no redirects |
| Output encoding | All dynamic HTML is escaped; links restricted to `https:` |
| Privacy | Secrets, emails, phone and card numbers redacted before storage; account deletion erases user rows |
| Audit | Hash-chained audit log with verification endpoint |

## Threat model

| Threat | What stops it |
| --- | --- |
| A web page or provider result tells the assistant to do something | Retrieved text is treated as data. Instruction-like text is withheld from prompts, answers and memory, and research agents have no write tools. |
| A request tries to make the assistant leak data or skip approval | The sentinel screens the request first; a blocked request calls no tool or model. Writes exist only in the action graph and need a human approval. |
| An approval is reused or the payload is swapped after approval | Approvals are bound to a digest of the exact payload, are single use and expire. The stored payload is re-checked against the digest at execution. |
| The same post or booking is sent twice | Duplicate detection on the payload, an idempotency key per action, and no automatic retry of writes. |
| A request was sent but the answer was lost | The action is stored as `unknown`, also when the run is cancelled mid-send or the service restarts, and is never re-sent. |
| One user reads another's data | Every query is scoped by the session's user id. Cross-user ids return "not found". |
| The server is used to reach internal addresses | Outbound calls are HTTPS only, limited to each provider's host allowlist, with private, loopback and link-local addresses rejected and redirects disabled. |
| Stored content runs as script in the browser | All dynamic HTML is escaped, links are limited to `https:`, and the CSP forbids inline scripts. |
| The audit trail is edited | Each audit record includes the hash of the previous one; `GET /api/security` verifies the chain. |

## Approval lifecycle

1. **Propose.** The payload is validated and normalised. Anything ambiguous (missing recipient, non-explicit channel, fare above the cap) is rejected here and nothing is stored as approvable.
2. **Show.** The approval card shows the destination, visibility, cost and the exact content.
3. **Decide.** Approval must quote the digest that was shown. A mismatch is recorded in the ledger and refused.
4. **Execute.** The action moves to `executing` in one atomic update, so it cannot run twice. Dependencies must already be `executed`.
5. **Record.** The outcome and receipt are written to the ledger: `executed`, `failed` (nothing sent) or `unknown`.

## Community and social agents

- Community profiles are opt-in, need adult confirmation, and expose a display name, city and interests only. Email addresses and exact locations are never shown to other members.
- Meetup agents exchange verdicts, not limits. The API returns only the caller's own limits.
- Video calls need an accepted connection and no block in either direction. A block between two participants closes their shared meetups to both.

## Data handling

- Stored: account, sessions (hashed tokens), conversations, memory items, runs and their events, actions and ledger, community profile, plans, meetups, telemetry and audit records.
- Redacted before storage: secrets, email addresses, phone numbers and card numbers found in free text.
- Deleted with the account: every user-scoped row and the graph checkpoints of the user's runs and approval batches.
- Not stored: provider credentials (read from the environment at call time) and payment details (never collected).

## Limits of these controls

- Pattern-based screening can be evaded. It is a first line of defence; the structural controls above are what prevent damage.
- Rate limiting is in-process and per instance.
- Provider tokens live in server environment variables and are shared by all users of an installation.
- Because of that, write connectors and Strava act as one account for everyone on the installation. Use a single-user installation, or leave those keys unset, until per-user sign-in exists.
- Video rooms are on the public Jitsi Meet service, which cannot revoke a link after a block.
- There is no email verification, password reset or MFA.
- Deploy behind HTTPS and set `LIFECANVAS_SECURE_COOKIES=1` and `LIFECANVAS_ALLOWED_HOSTS`.

## Reporting

Open a private security advisory on the repository.
