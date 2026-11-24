# Integration Specifications

**Status:** Draft (documented). Provider selections/credentials are **Pending Approval**; interfaces and controls defined here.

## 1. Principles
- **Adapter/service pattern:** core business logic depends on internal interfaces, not provider SDK specifics; providers swappable.
- **Security:** credentials in environment variables or secrets manager only; never in code/logs/frontend.
- **Reliability:** webhook signature validation, idempotency keys, retries with exponential backoff, failure logging/inspection, replay controls where safe.
- **Correctness:** server-side verification and reconciliation for money-moving flows; **never** trust client-side redirect as proof of payment.

## 2. Payment Gateway (MVP-capable, provider TBD)
- **Capabilities:** initialize transaction (invoice/context ref, amount, currency NGN), redirect/checkout or inline as supported, receive webhook/callback, verify transaction status server-side via provider API, reconcile against invoices/payments.
- **Flow (required):** create pending payment intent/record with idempotency key → initiate with provider → on webhook/callback **verify with provider server-side** → post/allocate payment transactionally and idempotently → issue receipt/update invoice/balance → handle failures/timeouts/duplicates.
- **Data:** store provider reference, status, verified timestamp, safe response metadata; currency on transaction.
- **Edge cases:** partials (if supported by design), reversals/refunds via authorized workflow, duplicate webhooks, out-of-order events, mismatched amounts/currency.
- **Selection criteria (D-012):** NGN support, settlement/fees, webhook reliability, API quality, compliance, credentials availability. **Pending.**
- **Local slice (D-034, not go-live):** mock provider adapter and signed webhook endpoint `POST /api/v1/finance/webhooks/payments/{provider}/` implemented with `X-Webhook-Signature` HMAC-SHA256 verification, idempotent `PaymentWebhookEvent` recording by provider+event_id, amount/currency mismatch rejection, and server-verified payment/invoice reconciliation. Real provider adapters, secrets management, replay tooling, and settlement reconciliation remain pending.

## 3. Email
- **Use cases:** auth emails (password reset), notifications, receipts/statements (policy-dependent), announcements.
- **Interface:** send templated/plain messages, track message id/status, handle bounces/failures.
- **Controls:** verified sender domain, rate/volume awareness, avoid sensitive data in body (prefer secure portal links), consent/preferences.
- **Provider TBD** (D-013).

## 4. SMS
- **Use cases:** alerts (attendance/fees/events) per consent and policy.
- **Interface:** send, delivery status callback where available, logging/retry.
- **Controls:** opt-in/consent, message content minimization (no sensitive academic/financial detail), local regulatory compliance.
- **Provider TBD (NG-focused)** (D-013).

## 5. WhatsApp Business (Deferred R3)
- **Use cases:** opt-in notifications/communications.
- **Requirements when implemented:** official Business API provider, template approvals, webhook handling, consent tracking, strict data minimization.
- **Status:** not MVP; design adapter placeholder only.

## 6. File Storage (Object Storage)
- **Use cases:** private documents (student/staff/finance/transcripts/report cards/attachments) and public CMS media.
- **Requirements:** S3-compatible API (dev local, staging/prod provider per D-014), **separate buckets/prefixes/policies** for private vs public; private-by-default; server-side encryption as supported; presigned/expiring URLs or authenticated downloads for private content after authz check.
- **Operations:** lifecycle/retention policies aligned to data retention, backups/versioning, integrity metadata.

## 7. Biometric Attendance & GPS Tracking (Deferred R2/R3)
- **Biometric:** device/vendor-specific; require adapter, secure device enrollment, user mapping, event ingestion with dedupe/idempotency, fallback to manual attendance. **Deferred.**
- **GPS/transport:** provider/device integration, location events, privacy controls, parent visibility per policy. **Deferred.**

## 8. Identity/Document Verification (Optional/Future)
- Only if required; evaluate privacy, cost, accuracy, and legal basis. Not in MVP.

## 9. Webhook & Event Handling (cross-cutting)
- Dedicated endpoints per provider; signature/HMAC verification; timestamp/tolerance checks; idempotent processing (store event ids); async processing queue; structured logs; alert on repeated failures; replay tooling with safeguards.

## 10. Configuration & Secrets
- Per-environment configuration; secrets via env vars/secrets manager; no secrets in repo; document required keys in `.env.example` (placeholders only).
- Feature flags/toggles for enabling integrations safely.

## 11. Open Items (Pending Approval)
- D-012/D-013/D-014: provider choices, contracts, credentials, sandbox/test accounts.
- Data processing agreements and compliance requirements per provider.
- Reconciliation procedures and operational runbooks (to be produced with deployment/ops).
