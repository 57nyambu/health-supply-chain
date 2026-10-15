# Payments — M-Pesa, cash, Equity, KCB, cards

Required methods: **M-Pesa**, **cash** (documented procedure — `docs/operations/CASH-HANDLING-SOP.md`), **two banks** (Equity via Jenga, KCB via Buni), **cards** (Pesapal hosted checkout online; PDQ terminals at the counter). Insurance remittances, deposits and credit notes reuse the same ledger.

Never invent provider fields. The endpoint names below come from the providers' published docs or widely used SDKs; confirm request/response bodies against the provider docs for your account tier before coding, and record anything that differs in PROGRESS.md "Spec gaps".

---

## 1. Ledger and state (`apps/payments`)

```
PaymentIntent  created → pending → succeeded | failed | cancelled | expired | unknown
Payment        posted → reversed            (immutable ledger row; corrections are new rows)
Allocation     payment → invoice amounts    (Σ allocations ≤ payment amount; remainder = unallocated credit)
Receipt        numbered per facility/year; reprints marked "Copy"
Refund         requested → approved → executing → completed | failed   (maker-checker, §7.9 of DESIGN)
CashierShift   open → closing → closed → signed_off
ProviderTransaction  raw provider record (callback, IPN, query result, statement row), encrypted payload
ReconciliationRun    per facility per day per provider; signed off by finance
```

Invariants (property-tested with hypothesis):
- A succeeded intent produces exactly one `Payment` (unique constraint on `(provider, provider_reference)`).
- Allocations never exceed the payment or the invoice balance; invoice balance = total − credits − allocations.
- A shift's expected cash = float + cash receipts − cash refunds − safe drops; closing records the counted amount and the variance.
- No floats: `Decimal` with 2 dp, `ROUND_HALF_UP`.

### The port

```python
class PaymentProvider(Protocol):
    code: str                     # "cash", "mpesa", "jenga", "buni", "pesapal", "pdq"
    def capabilities(self) -> ProviderCapabilities: ...
    def initiate(self, intent: PaymentIntent) -> InitiationResult: ...            # STK push, checkout URL, payment link…
    def query(self, intent: PaymentIntent) -> ProviderStatus: ...                 # authoritative status check
    def parse_notification(self, raw: WebhookInbox) -> ProviderEvent: ...        # verify + normalise callback/IPN
    def refund(self, refund: Refund) -> RefundResult: ...                         # where supported
    def import_statement(self, file_or_range) -> list[ProviderTransaction]: ...   # reconciliation input
```

Rules for every provider:
- `Idempotency-Key` on initiation; one intent per bill per method attempt.
- Callbacks/IPNs: verify (signature, credentials or secret path + IP allowlist), store raw encrypted in `WebhookInbox`, reply 2xx immediately, process in Celery. Duplicate notifications are expected — dedupe on the provider reference.
- **A callback alone never marks money as received when the provider offers a query API.** Confirm with the provider's status/query call, then post the payment.
- Never trust amounts or statuses sent by the browser.
- Timeouts: show the cashier a clear state ("Waiting for PIN", "No response — check status", "Failed: cancelled by customer") and a fallback method.

---

## 2. M-Pesa — Safaricom Daraja

Existing legacy code (STK push, transaction status) moves into `payments/adapters/mpesa/` and is rewritten to this design with tests (P2-PAY-03).

- Hosts: sandbox `https://sandbox.safaricom.co.ke`; production `https://api.safaricom.co.ke`.
- OAuth: `GET /oauth/v1/generate?grant_type=client_credentials` with basic auth (consumer key/secret); cache the token until shortly before expiry.
- **M-Pesa Express (STK push):** `POST /mpesa/stkpush/v1/processrequest` — `BusinessShortCode`, `Password` = base64(shortcode + passkey + timestamp), `Timestamp` (`YYYYMMDDHHmmss`, Nairobi time), `TransactionType` (`CustomerPayBillOnline` for a paybill, `CustomerBuyGoodsOnline` for a till), `Amount`, `PartyA` (payer phone `2547…`/`2541…`), `PartyB`, `PhoneNumber`, `CallBackURL`, `AccountReference` (our visit/invoice number — keep it short; Safaricom limits its length), `TransactionDesc`.
- Amounts are whole shillings. If a bill has cents, the facility setting decides: round the request up and keep the excess as patient credit, or add a rounding line. Default: round up, credit the difference.
- Result arrives on the callback (`Body.stkCallback`: `MerchantRequestID`, `CheckoutRequestID`, `ResultCode`, `ResultDesc`, metadata with `Amount`, `MpesaReceiptNumber`, `TransactionDate`, `PhoneNumber`).
- Confirm with **STK query** `POST /mpesa/stkpushquery/v1/query` (same password/timestamp scheme, `CheckoutRequestID`) before posting the payment. Use the query, too, when no callback arrives within 90 seconds.
- Common result codes (confirm in sandbox): `0` success; `1` insufficient balance; `1032` cancelled by the customer; `1037` phone unreachable/timed out; `2001` wrong PIN. Map each to a cashier-facing message and next action.
- **C2B (paybill/till fallback):** register validation and confirmation URLs (`/mpesa/c2b/v2/registerurl`). Validation only works once Safaricom enables it on the shortcode. Confirmation payloads carry the transaction ID, amount, bill reference (the account number the customer typed) and the payer — phone numbers may be masked, so match on bill reference + amount, never on phone alone.
- **Transaction status** (`/mpesa/transactionstatus/v1/query`) and **reversal** (`/mpesa/reversal/v1/request`) need an initiator name and a security credential (initiator password encrypted with Safaricom's certificate); results come back asynchronously on result/timeout URLs.
- Refunds: reversal (time-limited, needs Safaricom permissions) or B2C to the customer if a B2C shortcode is provisioned; otherwise cash refund with approval.
- Callbacks are not signed: unguessable secret path segment, HTTPS only, IP allowlist where Safaricom publishes ranges, confirmation by query.
- Sandbox: test shortcode `174379` with its published passkey; test MSISDN from the Daraja simulator. Env: `MPESA_MODE`, `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_SHORTCODE`, `MPESA_TILL` (optional), `MPESA_PASSKEY`, `MPESA_INITIATOR`, `MPESA_SECURITY_CREDENTIAL`, `MPESA_CALLBACK_BASE`.

## 3. Cash

No provider API. The system enforces the procedure in `docs/operations/CASH-HANDLING-SOP.md`:
- Only an open `CashierShift` can receive cash; opening float counted by denomination and confirmed by a supervisor.
- Every receipt numbered; voiding a receipt in the same shift needs a supervisor; after shift close it becomes a refund (maker-checker).
- Safe drops recorded during the shift; closing count by denomination; variance auto-calculated; supervisor sign-off; Z-report PDF.
- Bank deposits recorded against shifts with the bank slip reference; reconciliation matches deposits to bank statement lines.

## 4. Equity Bank — Jenga API (v3)

Docs: developer.jengahq.io (Jenga API v3). Merchant onboarding on JengaHQ gives the merchant code, API key and consumer secret; you upload a public key and sign requests with your private key.

- Auth: request a bearer token with the merchant credentials; every API call also carries a **signature** (RSA-SHA256 over the fields each endpoint specifies, base64). Keep key generation and signing in one module with tests against the documented examples.
- Collection options (choose per facility in configuration):
  1. **Bank paybill / bill payments** — patients pay to Equity's collection channels with the facility account and our reference; Jenga sends an **IPN** to the URL registered on JengaHQ.
  2. **Payment link API** — create a link (`/v3-apis/payment-api/v3.0/payment-link/create`) and send it by SMS/email; the patient pays by card, mobile money or bank; result via IPN.
  3. **Jenga Payment Gateway checkout** — hosted checkout for cards and mobile money (redirect/iframe).
- Query transaction status and pull account transactions/statements for reconciliation.
- Payouts/refunds (internal transfer, PesaLink) only with maker-checker; optional in v1.
- Env: `JENGA_MODE`, `JENGA_BASE_URL`, `JENGA_MERCHANT_CODE`, `JENGA_API_KEY`, `JENGA_CONSUMER_SECRET`, `JENGA_PRIVATE_KEY_PATH` (outside the repo), `JENGA_ACCOUNT_NUMBER`, `JENGA_IPN_TOKEN`.

## 5. KCB Bank — Buni

Portal: buni.kcbgroup.com (UAT `https://uat.buni.kcbgroup.com`). Production access needs a signed request letter to KCB (owner action).

- Auth: `POST /token?grant_type=client_credentials` with the consumer key/secret (basic auth).
- **STK push to a KCB paybill/till** (`/mm/api/request/1.0.0/stkpush`): the customer gets an M-Pesa prompt and funds settle into the facility's KCB account; Buni relays a Daraja-style callback. Field names vary between Buni products — map them from the docs for the subscribed product.
- **IPN** for account credits (any channel paying into the facility account): verify the `Signature` header (SHA256withRSA over the raw body with KCB's public key), check the source IP allowlist, acknowledge in the documented format, dedupe on the transaction reference.
- Transaction query and statement retrieval for reconciliation; Funds Transfer API for payouts/refunds is optional.
- Env: `BUNI_MODE`, `BUNI_BASE_URL`, `BUNI_CONSUMER_KEY`, `BUNI_CONSUMER_SECRET`, `BUNI_ACCOUNT_NUMBER`, `BUNI_TILL_OR_PAYBILL`, `BUNI_IPN_PUBLIC_KEY_PATH`, `BUNI_IPN_ALLOWED_IPS`.

## 6. Cards

### 6.1 Online / at-desk card payments — Pesapal API 3.0 (default)
- Hosts: sandbox `https://cybqa.pesapal.com/pesapalv3`; live `https://pay.pesapal.com/v3`.
- `POST /api/Auth/RequestToken` (consumer key/secret) → short-lived token.
- `POST /api/URLSetup/RegisterIPN` (URL + notification method) → `ipn_id`; register once per environment and store it.
- `POST /api/Transactions/SubmitOrderRequest` (our merchant reference, `currency: KES`, amount, description, callback URL, `notification_id`, billing contact) → `order_tracking_id` + `redirect_url`. Show the hosted page in a dialog/iframe or redirect.
- On IPN or callback, call `GET /api/Transactions/GetTransactionStatus?orderTrackingId=` and act on the returned status (completed / failed / reversed / invalid — confirm the status codes in the sandbox).
- Refunds: Pesapal refund request API with the confirmation code (maker-checker first).
- **PCI scope:** card numbers and CVVs are entered only on Pesapal's hosted page. Our pages never render card fields; logs never contain card data.
- Env: `PESAPAL_MODE`, `PESAPAL_BASE_URL`, `PESAPAL_CONSUMER_KEY`, `PESAPAL_CONSUMER_SECRET`, `PESAPAL_IPN_ID`.

### 6.2 Card-present terminals (PDQ)
Bank-supplied terminals stay standalone. The cashier records method `pdq`, terminal ID, approval code, RRN and amount; the payment is `posted` with `confirmation: pending_settlement`. The daily acquirer settlement file (CSV) is imported and matched on RRN/approval code + amount; mismatches go to the reconciliation queue. Store no card number (not even the last four digits) unless an ADR approves it.

## 7. Reconciliation (P3-REC-01)

Inputs: `ProviderTransaction` rows from callbacks/IPNs, queries, statement imports (Daraja, Jenga, Buni, Pesapal, PDQ settlement files, bank statements for cash deposits and SHA/insurer remittances).

Matching, in order:
1. Exact provider reference (M-Pesa receipt, bank reference, Pesapal confirmation code, RRN) → payment.
2. Account/bill reference (visit or invoice number) + amount + date window → candidate (auto-accept if unique).
3. Otherwise → **suspense**. Allocation from suspense needs maker-checker.

Daily run per facility and provider produces: matched count/amount, unmatched provider transactions, payments without provider confirmation (cash excluded), variances, shift ties. Finance signs off the day; signed-off days are locked (corrections via adjustment entries).

## 8. Refunds by method

| Method | Path |
|---|---|
| Cash | From an open shift after approval; refund receipt printed |
| M-Pesa | Reversal (if permitted and in window) or B2C; else cash/bank refund |
| Card (Pesapal) | Refund API |
| Card (PDQ) | Terminal refund by an authorised user; settlement file confirms |
| Bank (Jenga/Buni) | Transfer via API (optional) or manual bank transfer recorded with reference |

## 9. Testing
- Fakes for every provider (deterministic: success, cancel, timeout, duplicate callback, amount mismatch, late callback after query).
- Recorded sandbox fixtures (sanitised) for parsers and signature verification (include known-good signature vectors from provider docs).
- Property tests for ledger invariants; concurrency tests for double-callback races (`select_for_update` on the intent).
- Scenario E2E: cash shift close (E2E-13), M-Pesa STK + C2B fallback (E2E-01, E2E-06), banks (E2E-09), cards and refunds (E2E-10).
