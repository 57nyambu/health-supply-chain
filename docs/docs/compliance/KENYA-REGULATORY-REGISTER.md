# Kenya Regulatory Register — AfyaSync HMIS

Research snapshot: **15 October 2026**. Every requirement has an ID (`KE-…`). Code and tests reference these IDs (`@pytest.mark.req("KE-SHA-02")`, Playwright `test.info().annotations`), and `make traceability` turns them into `docs/generated/traceability.md`.

**How to use this file**
- It is a working register, not legal advice. Items marked **verify** were reported by secondary sources or could not be confirmed against the primary text during research. Before building anything that depends only on a *verify* item, check the primary source and record the result in `docs/agent/DECISIONS.md`.
- Regulators publish changes often (SHA/DHA deadlines moved several times in 2025–26). When an external spec contradicts this file, the external spec wins: update this file in the same commit as the code.
- Column "System implication" is the design consequence; "Evidence" is how COMPLETION.md proves it.

---

## 1. Digital Health Agency (DHA), HIE and certification

| ID | Requirement | Source | System implication | Evidence |
|---|---|---|---|---|
| KE-DHA-01 | Digital health solutions used in service delivery must be certified by DHA under its Certification Framework; vendors apply on the prescribed form (Form "HMIS 4" in the First Schedule) and DHA tests the solution. Certified systems appear on the public registry. | Digital Health Act 2023 s.6(m); Digital Health (Health Information Management Procedures) Regulations 2025 (Legal Notice 76/2025); certification.dha.go.ke registry | Build for certification from day one: standards conformance, evidence capture, security and backup policies, versioned releases. | P3-DOC-01 evidence pack; P3-SHA-08 UAT evidence |
| KE-DHA-02 | Practitioner guides list six items DHA expects for HMIS certification: self-attestation report (DHA HMIS form); ODPC registration; a DPIA; a security, privacy and confidentiality policy; a tested backup and recovery policy; proof of interoperability/standards compliance (FHIR, ICD-11). **verify** with DHA at application time. | Practitioner guides (Quecorex, Sept 2026; Afiacity opinion, Oct 2026) | COMPLETION.md evidence pack mirrors these six items. | P3-DOC-01 |
| KE-DHA-03 | HIE integration go-live path is four mandatory phases: development and testing; UAT demo with the HIE integration team covering PHC, SHIF and ECCIF workflows from the official UAT checklist; DHA certification; production credentials. Live integrations are monitored by DHA afterwards. | hie-docs.dha.go.ke/docs/goLive | UAT checklist runner and evidence capture (screenshots, request/response logs). Production credentials only after certification. | P3-SHA-08 |
| KE-DHA-04 | Exchange goes through the national HIE and its registries: Client Registry (patients, `CR…` IDs), Facility Registry (`FID-…`), Health Worker Registry (`PUID-…`), plus the Shared Health Record. | Digital Health (Data Exchange Component) Regulations 2025 (LN 77/2025); hie-docs registries; afyalink.dha.go.ke | Store CR ID, FID and PUID on patient, facility and practitioner records; registry lookups through the HIE adapter. | P1-PAT-02, P3-SHA-01 |
| KE-DHA-05 | Health data in the system must be retained for at least 20 years. | DHA HIM Regulations (retention clause) as summarised by Clyde & Co (Mar 2026) and the published draft regulations; Act s.25 (retention and disposal) | Retention engine: no hard deletes of clinical records; `retention_until` on records and documents; legal hold. | P1-DATA-02, P1-STO-01 |
| KE-DHA-06 | Health data must be stored/processed in Kenya; cross-border transfer only under prescribed conditions (Data Protection (General) Regulations 2021 localisation for primary and secondary healthcare data; Digital Health Act). | Carnegie Endowment analysis (Mar 2026) of DP (General) Regs 2021 and the Digital Health Act; Act Part on health tourism transfers | Residency guard (`DATA_RESIDENCY_MODE`), storage provider allowlist, backups in Kenya. **Contabo has no Kenyan region (EU/US/SIN only)**: using it for production PHI needs a documented legal basis or a Kenyan S3 endpoint. | P1-STO-01, ADR-006 |
| KE-DHA-07 | Health data controllers transfer records to the national health data bank (and county banks when operational) within the timelines in the HIM Regulations. **verify** exact obligations and mechanism. | Clyde & Co summary (Mar 2026) | FHIR export of patient records (bundle per patient/encounter) and SHR push capability behind a flag. | P3-SHA-07 |
| KE-DHA-08 | DHA is custodian of all health data (s.22); data portability is provided for in the Act. | Digital Health Act 2023 s.22, s.36 | Patient record export (FHIR + PDF) for portability and DSARs. | P1-DATA-02 |
| KE-DHA-09 | Exchange security per the Kenya eClaims FHIR IG (draft 0.1.0): OAuth 2.0/SMART on FHIR preferred, mTLS alternative for system-to-system, API keys never the sole auth for PHI, AuditEvents sent to the HIE audit repository. | build.fhir.org/ig/IntelliSOFT-Consulting/Kenya-eClaims-FHIR-IG (security page) | HIE client uses the token flow, TLS only, no PHI in query strings beyond what the API mandates; local AuditEvent for every exchange. | P3-SHA-01 |

## 2. Social Health Authority (SHA) and claims

| ID | Requirement | Source | System implication | Evidence |
|---|---|---|---|---|
| KE-SHA-01 | SHA (Social Health Insurance Act 2023; launched 1 Oct 2024) runs three funds: Primary Healthcare Fund, Social Health Insurance Fund (SHIF), Emergency, Chronic and Critical Illness Fund (ECCIF); plus public officers' schemes (POMSF/PFMS) on the same rails. From the FY2026/28 contracting cycle facilities must use a DHA-certified HMIS integrated with the HIE; the compliance deadline was extended to 30 Sept 2026, with an October 2026 rapid-results extension. | SHI Act 2023; allAfrica/Capital FM (1 Sept 2026); Kenya Today (Oct 2026); afyalink.dha.go.ke | SHA integration is a Phase 3 must-have, and DHA certification is a business-critical milestone with a deadline already running. | P3-SHA-* |
| KE-SHA-02 | All SHA claims must carry valid **ICD-11** diagnosis codes, selected by clinicians through a search interface, validated, and linked to SHA intervention codes. | afyalink.dha.go.ke/claim-integration | ICD-11 is the primary diagnosis code system; only valid codes selectable; claim builder links diagnoses to interventions. | P2-CLI-03, P3-SHA-03 |
| KE-SHA-03 | Facilities map their services to SHA intervention codes (e.g. `SHA-12-001`) from the SHA Benefits and Tariffs spreadsheet: which services they are contracted for, pre-authorisation flags, reimbursement tariffs (some by KEPH level). | afyalink.dha.go.ke | Versioned import of the tariff spreadsheet; service ↔ intervention mapping; preauth flags drive gates. | P3-SHA-01, P2-BIL-01 |
| KE-SHA-04 | Every visit starts with patient search and eligibility (`GET /patients`, `/patients/eligibility`, `/patients/sub-benefits`, `/patients/benefits/interventions`) and needs patient consent: OTP to a confirmed contact, or biometrics via an authorisation iframe. The returned token is the consent handle for all later calls on that visit. | hie-docs.dha.go.ke/docs/scenarios/overview | Reception flow integrates eligibility and consent; consent tokens encrypted at rest, never logged, treated like passwords. | P3-SHA-02 |
| KE-SHA-05 | Eight integration scenarios: SHIF IP per diem; SHIF IP FFS normal preauth; SHIF IP FFS elective preauth; SHIF OP FFS elective preauth; SHIF OP FFS normal preauth; UHC OP capitation; ECCIF emergency identified; ECCIF emergency unidentified (emergency claims by protocol, doctor consent instead of preauth, **submit within 24 hours**). | hie-docs scenarios overview | Scenario-driven claim engine; emergency SLA timer; unidentified-patient support. | P3-SHA-03..06 |
| KE-SHA-06 | No claim is complete without a claim form, an itemised invoice and a discharge or case summary. | SHA notice, 15 Sept 2025 (Business Today, People Daily, Kenyans.co.ke) | Claim scrubber blocks submission until all three documents are attached; generated PDFs. | P3-CLM-01 |
| KE-SHA-07 | Claims are idempotent on claim ID; status states include queued, approved, rejected, in-review, clinical-review, sent-for-payment-processing, sent-to-surveillance, payment-completed, payment-declined; callbacks are POST, secured with basic auth (IP allowlisting optional). | afyalink.dha.go.ke integration checklist | Claim status model maps these states; callback endpoint with basic auth + allowlist; poller as fallback. | P3-SHA-03, P3-SHA-07 |
| KE-SHA-08 | PHC (capitation) claims carry a zero total; per-diem interventions (ICU/HDU/NICU, burns) are paid per day by KEPH-level tariff. | afyalink checklist; sha-claim SDK notes on per diem | Zero-total claim support; per-diem allowance shown as *unknown* when SHA publishes no rate (never coerced to 0). | P3-SHA-06 |
| KE-SHA-09 | SHA rejects about one in five county claims for errors and missing documents (June 2026). | The Star, 4 July 2026 | Pre-submission scrubbing and a rejection work queue are revenue-critical, not nice-to-have. | P3-CLM-01 |

## 3. Data protection (ODPC)

| ID | Requirement | Source | System implication | Evidence |
|---|---|---|---|---|
| KE-DPA-01 | Health data is sensitive personal data; processing needs a lawful basis, purpose limitation and minimisation. | Data Protection Act 2019 (definitions; Part on sensitive personal data, "personal data relating to health") | Data classification; collect only what each workflow needs; no PHI in logs/SMS. | DESIGN §8 |
| KE-DPA-02 | Data controllers and processors register with the ODPC (health service providers fall in the mandatory class). | DPA 2019 s.18; DP (Registration of Data Controllers and Data Processors) Regulations 2021 | Each facility (controller) and the vendor/host (processor) register; registration numbers stored in Facility settings and shown in the privacy notice. | P3-DOC-01 |
| KE-DPA-03 | A Data Protection Impact Assessment is required for high-risk processing. | DPA 2019 s.31 | DPIA draft generated from the data inventory; AI features stay off until a DPIA covers them. | P3-DOC-01 |
| KE-DPA-04 | Personal data breaches are notified to the Data Commissioner within 72 hours of awareness, and to data subjects where there is a real risk of harm. | DPA 2019 s.43 | Breach incident workflow with 72-hour clock; templates; audit evidence export. | P3-DOC-02, DESIGN §8.7 |
| KE-DPA-05 | Data subject rights: information, access, correction, deletion (limited by retention law), objection, portability. | DPA 2019 Part IV | DSAR register; export; amendment workflow; erasure requests answered with legal basis when retention law prevails. | P1-DATA-02 |
| KE-DPA-06 | Data protection by design and by default; security safeguards (pseudonymisation, encryption, access control). | DPA 2019 s.41 | Field-level encryption, default-deny authz, audit, least privilege. | P1-UAC-*, P1-DATA-01 |
| KE-DPA-07 | Transfers outside Kenya only under the Act's conditions (appropriate safeguards, adequacy, consent for sensitive data) — combined with KE-DHA-06 localisation. | DPA 2019 Part VI | Outbound integrations only to listed endpoints; no PHI to external AI/analytics services. | P1-STO-01, ADR-006 |

## 4. Health law and patient rights

| ID | Requirement | Source | System implication | Evidence |
|---|---|---|---|---|
| KE-HLT-01 | No person shall be denied emergency medical treatment; all providers (public and private) owe emergency treatment; ECCIF funds emergency care. | Constitution Art. 43(2); Health Act 2017 s.7 and s.12; SHI Act s.28 (as cited by the Solicitor General, Oct 2025) | Emergency visits bypass every payment and eligibility gate; no deposit demanded; tests enforce it. | P2-VIS-02, E2E-04 |
| KE-HLT-02 | Hospitals may not detain patients (or bodies) over unpaid bills; courts have repeatedly ruled it unlawful (latest High Court ruling 28 Apr 2026); the Health (Amendment) Bill 2025 (Senate Bills No. 12) proposes a new s.7A criminalising it. | High Court rulings (DLA Piper 2021; HapaKenya Apr 2026); Parliament bill digest (Apr 2026) | Discharge is never blocked by balance: balance becomes an invoice + debt agreement; no "gate pass blocked" state. Records released on discharge. | P2-IPD-03, P2-BIL-04, E2E-06 |
| KE-HLT-03 | Patients have rights to confidentiality, informed consent and information about their care (Constitution Art. 31; Health Act; National Patients' Rights Charter 2013 — **verify** current text). | Constitution; Health Act 2017 | Consent capture (treatment/procedure consents as documents); access to own records via DSAR export. | P1-DATA-02 |

## 5. Ministry of Health standards and reporting

| ID | Requirement | Source | System implication | Evidence |
|---|---|---|---|---|
| KE-MOH-01 | Facilities report routine data into KHIS (DHIS2): MOH 705A/705B (OPD morbidity under 5 / 5 and over), 710 (immunisation), 711 (integrated services), 717 (workload), 706 (laboratory), weekly 505 (IDSR), 731 (HIV). Monthly summaries reach the sub-county by about the 5th; KHIS entry by about the 15th. | KHIS reporting guides; CDC/PMC studies on Kenyan DHIS2 reporting | Registers derived from data; monthly summary generators; DHIS2 dataValueSets export with operator-maintained UID mappings (never hard-coded). | P2-REP-01, E2E-14 |
| KE-MOH-02 | Each facility has a KMHFL (Master Facility List) code used in reporting and SHA empanelment, and a KEPH level (1–6). | KMHFL; KHIS guides | Facility model stores MFL code, FID and KEPH level; reports keyed by MFL. | P1-FAC-01 |
| KE-MOH-03 | MOH EMR Standards and Guidelines (2010) set functional areas: demographics and clinical information, order entry and prescriptions, clinical decision support, reporting, security and confidentiality, information exchange. Older than the DPA; treat as a baseline, not the ceiling. | JMIR Med Inform 2018 (case study); CIPIT policy brief | Coverage of all seven areas; security sections superseded by DPA/DHA rules. | DESIGN §4 |
| KE-MOH-04 | Interoperability via national standards: Kenya Health Information Interoperability Framework, FHIR R4 implementation guides published by DHA (eClaims IG, Core IG), terminology on DHA's OCL instance (ilm-hie.dha.go.ke). | Kenya eClaims FHIR IG background page; NCCP FHIR IG | FHIR R4 mapping layer (`interop`), validated with `fhir.resources`; terminology adapter. | P3-SHA-07 |
| KE-MOH-05 | Triage: WHO ETAT+ (emergency / priority / non-urgent) is used for children; there is no single national adult A&E triage scale; KNH implemented the South African Triage Scale (red/orange/yellow/green, blue for dead). | Kenyan ETAT+ studies (KNH); SATS at KNH (Wangara et al.); 2023 Kenyan triage survey | Configurable triage scales per facility; defaults: ETAT+ for paediatrics, SATS-style five colours for adults. | P2-TRI-01 |

## 6. Medicines, professions, tax and payments

| ID | Requirement | Source | System implication | Evidence |
|---|---|---|---|---|
| KE-PPB-01 | Controlled drugs need a register with running balances and pharmacist accountability. **verify** current register format with the Pharmacy and Poisons Board. | Narcotic Drugs and Psychotropic Substances (Control) Act; Pharmacy and Poisons Act | Controlled-drug register: pharmacist-only dispensing, witness for wastage, running balance per batch, discrepancy workflow. | P2-PHA-03 |
| KE-PPB-02 | Adverse drug reactions are reported to PPB pharmacovigilance. **verify** current channel. | PPB | ADR capture on the patient record with export for PPB submission. | P2-PHA-01 |
| KE-PRF-01 | SHA identifies practitioners by regulator and registration number: KMPDC (doctors and dentists), COC (clinical officers), NCK (nurses); registry PUIDs come from the Health Worker Registry. Other cadres (pharmacists — PPB; lab — KMLTTB) also hold licences. | sha-claim SDK enums mirroring the HIE API; hie-docs registries | Professional licence model (regulator, number, expiry, PUID); clinical permissions gated on an active licence. | P1-UAC-07 |
| KE-KRA-01 | Businesses issue tax invoices through eTIMS (integration through OSCU/VSCU for system-to-system); medical services are generally VAT-exempt, but invoicing still runs through eTIMS. **verify** classification codes with KRA. | KRA eTIMS Taxpayer Guidelines 2024 | eTIMS adapter behind a flag: transmit invoices/credit notes, store control numbers and QR on PDFs, offline queue. | P3-TAX-01 |
| KE-PAY-01 | M-Pesa via Safaricom Daraja: OAuth, M-Pesa Express (STK push) and query, C2B URL registration, transaction status, reversal; HTTPS callbacks. | Safaricom Daraja docs and SDKs (Daraja 3.0, 2026) | Payment adapter with idempotent callbacks and status-query confirmation. | P2-PAY-03 |
| KE-PAY-02 | Card data (PAN/CVV) must never touch our servers; use a hosted checkout so PCI DSS scope stays minimal. | PCI DSS; Pesapal API 3.0 hosted checkout model | Card payments only through hosted pages/IPN; no card fields in our UI. | P3-CRD-01 |

---

## Sources (primary first)

- Digital Health Act 2023 — https://new.kenyalaw.org/akn/ke/act/2023/15/eng@2023-11-24
- Digital Health (Health Information Management Procedures) Regulations 2025, LN 76/2025 — https://new.kenyalaw.org/akn/ke/act/ln/2025/76/eng@2025-04-11 and DHA copy https://admin.dha.go.ke/uploads/The_Digital_Health_Health_Information_Management_Procedures_Regulations_2025_09301b40fa.pdf
- Digital Health (Data Exchange Component) Regulations 2025, LN 77/2025 — explanatory memorandum: https://libraryir.parliament.go.ke/bitstreams/f230813e-3b76-457d-9429-01619b97dd73/download
- DHA certification registry — https://certification.dha.go.ke/registry
- HIE developer docs (auth, registries, eClaims, consent, scenarios, go-live) — https://hie-docs.dha.go.ke/ ; https://hie-docs.dha.go.ke/docs/scenarios/overview ; https://hie-docs.dha.go.ke/docs/goLive ; https://hie-docs.dha.go.ke/auth/authentication
- AfyaLink claims submission guide (FHIR bundle path, ICD-11, checklist) — https://afyalink.dha.go.ke/claim-integration
- Kenya eClaims FHIR IG (draft) — https://build.fhir.org/ig/IntelliSOFT-Consulting/Kenya-eClaims-FHIR-IG/
- Data Protection Act 2019 — https://www.odpc.go.ke/wp-content/uploads/2024/02/TheDataProtectionAct__No24of2019.pdf
- Health data localisation analysis — https://carnegieendowment.org/research/2026/03/kenya-data-protection-america-first-global-health-strategy
- Health data obligations for insurers/controllers (retention, data banks) — https://www.clydeco.com/en/insights/2026/03/health-data-protection-in-kenya-strategic-complian
- SHA HMIS deadline extension — https://allafrica.com/stories/202609010210.html
- SHA mandatory claim documents — https://www.kenyans.co.ke/news/116272-sha-gives-hospitals-15-days-account-claims-worth-ksh3-billion
- SHA claim rejection rate — https://www.the-star.co.ke/news/2026-07-04-sha-rejects-one-in-five-claims-from-hospitals
- Detention over bills — https://hapakenya.com/2026/04/29/high-court-rules-nairobi-hospital-cannot-detain-stephen-gicheru-over-unpaid-bills/ ; bill digest https://parliament.go.ke/sites/default/files/2026-04/Bill%20Digest%20-%20The%20Health%20%28Amendment%29%20Bill%2C%20No.12%20of%202025.pdf
- Emergency treatment duty — https://eastleighvoice.co.ke/emergency medical services/222410/solicitor-general-calls-for-tougher-rules-on-emergency-care-body-detention
- KHIS reporting tools — https://open-exam-prep.com/study-guides/ke-coc-pre-internship/commodities-information-quality/health-information-systems-khis
- EMR Standards (2010) context — https://medinform.jmir.org/2018/2/e22
- KRA eTIMS guidelines — https://www.kra.go.ke/images/publications/eTIMS-Taxpayer-Guidelines_2024.pdf
- Contabo object storage regions — https://contabo.com/blog/de/kb/103000275473-wo-finde-ich-s3-verbindungseinstellungen-fuer-objektspeicher/
