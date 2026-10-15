# Cash Handling — Standard Operating Procedure

Audience: cashiers, cashier supervisors, finance. The system enforces each step marked **[system]**; steps marked **[manual]** are done by people and recorded in the system. The agent keeps this document and the cashier features (P2-PAY-02) in sync: when one changes, update the other in the same commit.

## 1. Roles
- **Cashier** — receives payments during their own shift only.
- **Cashier supervisor** — opens/closes floats with the cashier, approves same-shift voids, signs off shift closes.
- **Finance manager** — approves refunds, investigates variances above threshold, signs off daily reconciliation.
A person never approves their own void, refund or variance **[system]**.

## 2. Opening a shift
1. Supervisor issues the float; cashier and supervisor count it together by denomination (notes KES 1,000 / 500 / 200 / 100 / 50; coins 20 / 10 / 5 / 1) **[manual]**.
2. Cashier opens the shift in the system with the denomination count; supervisor confirms with their PIN **[system]**.
3. The system refuses cash receipts without an open shift for that user at that till **[system]**.

## 3. Receiving cash
1. Select the patient's bill from the queue (or scan the ticket/bill barcode); confirm the patient's name and the amount aloud **[manual]**.
2. Enter amount tendered; the system shows change due **[system]**.
3. Post the payment; a numbered receipt prints (80 mm) and, if the patient opted in, an SMS/email receipt is sent without clinical details **[system]**.
4. Give change and the receipt; place notes in the drawer by denomination **[manual]**.
5. Partial payments are allowed; the remaining balance stays on the bill **[system]**.
6. Counterfeit suspicion: do not accept; ask for another note; record an incident note on the shift **[manual + system]**.

## 4. Voids, refunds and corrections
- **Void (same shift, before the patient leaves):** cashier requests, supervisor approves; receipt marked void, payment reversed, reason recorded **[system]**.
- **After shift close:** never void — raise a refund request; finance manager approves; paid from an open shift with a refund receipt **[system]**.
- Wrong allocation (paid to the wrong bill): reallocation request with approval; original receipt stays valid and shows the reallocation **[system]**.

## 5. Safe drops
When drawer cash exceeds the facility limit (default KES 20,000), the system prompts a safe drop. Count with the supervisor, record amount and envelope/bag number, both confirm **[system + manual]**.

## 6. Closing a shift
1. Stop receiving; count cash by denomination with the supervisor **[manual]**.
2. Enter the count; the system computes expected cash (float + cash receipts − cash refunds − safe drops) and the variance **[system]**.
3. Variance within tolerance (default ±KES 50): supervisor signs off. Outside tolerance: cashier records an explanation; supervisor signs off; finance is notified automatically **[system]**.
4. The Z-report (PDF) lists receipts by method, voids, refunds, safe drops, expected vs counted, variance and signatures **[system]**.
5. Float returned to the supervisor; takings sealed for banking with the Z-report reference **[manual]**.

## 7. Banking and reconciliation
1. Finance deposits cash; records the bank slip reference against the shifts it covers **[system]**.
2. Daily reconciliation matches deposits to bank statement lines (Equity/KCB statement import) **[system]**.
3. Finance signs off the day; signed-off days are locked **[system]**.

## 8. Controls and reviews
- Daily: variance report; voids and refunds by cashier.
- Weekly: unannounced spot count by the supervisor (recorded as a shift event).
- Monthly: finance review of variance trends; repeated variances trigger retraining or investigation.
- Every action above is in the audit log with user, time, workstation and reason.

## 9. Downtime (system unavailable)
Use pre-numbered manual receipt books issued by finance. When the system returns, back-enter each manual receipt against the right bill and shift with its manual number; the system marks them "back-entered" and finance reconciles the books.
