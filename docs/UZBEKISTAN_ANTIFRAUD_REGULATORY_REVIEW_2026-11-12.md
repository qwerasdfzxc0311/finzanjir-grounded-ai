# Uzbekistan Antifraud Regulatory Review — 2026-11-12

**Repository scope:** `finzanjir-grounded-ai` only.  
**Purpose:** identify legal/operational constraints for a synthetic FINZANJIR prototype and a future bank-approved pilot.  
**Status:** research note; not a legal opinion or regulatory approval.

## Executive finding

Uzbekistan already has a Central Bank centralized anti-fraud system and a regulatory requirement for banks/payment-system participants to integrate with it. The 2024 and 2025 Central Bank annual reports describe a pilot in which 34 banks and 9 payment organizations were integrated. Presidential Resolution PQ-153 (30 April 2025) also directed the Central Bank to integrate transaction and other necessary data from banks, payment-system operators, payment organizations and credit bureaus into a unified Central Bank platform, and to complete centralized and participant-level anti-fraud systems by 1 September 2025.

Therefore FINZANJIR must not assume it should become a second independent national transaction-data lake. A potentially safer direction is a bank-authorized supplementary intelligence/workflow layer that complements existing bank and Central Bank systems: signal-quality checks, explainable risk prioritization, false-positive reduction, evidence provenance, human review, case/complaint workflow, audit and KPI. Any connection to the Central Bank platform must use an approved interface, purpose, data contract and authorization.

**This is a material architecture decision. It remains pending project-owner confirmation.** Until resolved, the repository keeps all bank and cross-bank data paths synthetic-only and disabled.

## 1. Central Bank Regulation No. 3513

Central Bank Board Resolution No. 13/1, registered as No. 3513 on 21 May 2024 and effective 23 August 2024:
https://www.lex.uz/docs/-6933268

Relevant provisions:

- Paragraph 310 defines an anti-fraud system as a set of processes intended to prevent fraud in payments involving bank cards/accounts, mobile-app accounts and electronic wallets.
- Paragraph 3 requires continuous protection of payment information throughout creation, transmission, storage and processing, including identification, authentication, authorization, MFA/2FA, integrity controls and prevention of unauthorized disclosure.
- Paragraphs 13–15 require an information-security function, electronic logs of staff and user actions, restricted staff privileges, documented access rights, logging of permission allocation/changes, periodic review, and confidentiality controls for external service providers.
- Paragraph 16 requires device identification data such as IP/MAC and other identifiers to be recorded in relevant remote-service systems; it also addresses MFA and anti-fraud/biometric identity controls.
- Paragraphs 31–33 address data-center resilience, backup systems and electronic archives. Important payment-system operators must maintain primary and backup systems in Uzbekistan and keep required archive copies.
- Paragraph 41 requires the relevant anti-fraud service to connect remote card/account/mobile-app/e-wallet systems to the Central Bank centralized anti-fraud and biometric identification systems; maintain suspicious-transfer registers; collect information on cards involved in suspicious fraud; use anti-fraud systems to prevent suspicious operations; operate 24/7; and impose temporary restrictions of up to three days only on the basis of a mandatory Central Bank instruction.
- Paragraphs 42–46 require risk criteria and processes for identifying unauthorized transfers, transactional and session anti-fraud systems, customer notifications and repeat confirmation for suspicious payments, customer ability to stop payments on their own accounts, collection/analysis of fraud complaints, and timely provision of requested information to the Central Bank.

### FINZANJIR implications

1. FINZANJIR must not independently block or freeze a citizen's card/account. Any legally authorized restriction remains with the bank/competent process and, where paragraph 41 applies, the Central Bank mandatory instruction.
2. FINZANJIR's synthetic Case is not a legal finding and cannot replace a bank's 24/7 anti-fraud service or human authority.
3. A future product should support explainability, evidence quality, complaint handling, customer confirmation, false-positive review and audit alongside—not instead of—existing systems.
4. Device/network/biometric features require source-specific lawful purpose, necessity, retention and access checks. The fact that a regulator requires a bank to record a particular signal does not automatically authorize an independent third party to receive it.

## 2. Presidential Resolution PQ-153 (30 April 2025)

Official text:
https://www.lex.uz/uz/acts/-7511145

Relevant directions:
- Paragraph 1 appoints the Ministry of Internal Affairs as the authorized body to coordinate a unified national approach to cybercrime response.
- Paragraph 7(b) assigns the Central Bank a role in monitoring transactions for suspected fraudulent fundraising/financial-pyramid schemes and notifying law-enforcement bodies.
- Paragraph 9(a) directed integration of transactions and other necessary data from banks, payment-system operators, payment organizations and credit bureaus into a unified Central Bank platform by 1 September 2025.
- Paragraph 9(b) directed completion of the Central Bank centralized anti-fraud system and participant-level session, transactional and telecommunications anti-fraud systems by the same date.
- Paragraph 12 establishes rapid-response cooperation between the Ministry of Internal Affairs and Central Bank, including rapid card restrictions on competent law-enforcement requests and prompt provision of relevant card information.
- Paragraph 16 directs an electronic information-exchange platform between the Ministry of Internal Affairs, Prosecutor General's Office and Central Bank for urgent cybercrime response.

The deadline has passed. Public evidence reviewed:
- Central Bank 2024 Annual Report: centralized anti-fraud system introduced on a pilot basis; 34 banks and 9 payment organizations integrated.
  https://cbu.uz/upload/medialibrary/a53/wn6gcejpkxphv2v4guajin4x01h7iyxa/Yillik-hisobot-2024.pdf
- Central Bank 2025 Annual Report: again describes the centralized anti-fraud pilot and 34 banks/9 payment organizations integrated.
  https://cbu.uz/upload/medialibrary/f27/1pe2gj41x2s1qafmi548hnvzg4aoh87x/Annual-Report-2025_.pdf

These reports do **not**, by themselves, prove that every element of PQ-153 paragraph 9(a)'s unified platform was fully completed. The current status, interfaces, participants, data fields and governance need written confirmation from the Central Bank.

## 3. Banking secrecy — Law No. 530-II

Official text:
https://lex.uz/ru/mact/41882

- Article 4 defines third parties as persons other than the bank, its customer/correspondent and the Central Bank.
- Article 5 says it is not disclosure for a bank to provide banking-secret information to third parties in cases permitted by the Law, or to persons providing legal, accounting, audit, information and consulting services to the bank, if the information is necessary for that service and the recipient is bound by the Article 6 confidentiality restrictions.
- Article 6 prohibits disclosure or use for personal/third-party interests of information constituting banking secrecy.
- Article 7 requires organizational and technical measures, including information-security and cybersecurity controls, to protect banking secrecy.
- Article 8 and Articles 9–10 specify legally authorized recipients and formal request channels.
- Article 14 allows banks to exchange information about their customers/correspondents for the security of their operations, deposit guarantees, and repayment of loans/other investments, but only in the manner and limits established by law. A bank receiving another bank's customer information may not disclose it to third parties.
- Article 15 limits the information a bank provides to information about its own customer/correspondent, subject to the statutory rule for information about others contained in that customer's documents.

### FINZANJIR implications

- Article 14 is not a blanket authorization for FINZANJIR, as an independent third party, to collect raw interbank customer data into its own central pool.
- Article 5 may be relevant if FINZANJIR is genuinely contracted as a bank's information/consulting service provider and receives only information necessary for that service under confidentiality and access controls. This is a legal hypothesis requiring written counsel/CBU/bank confirmation, not an established permission.
- Cross-bank raw data exchange, central matching and onward disclosure remain disabled in the prototype.
- A privacy-preserving bank-side/CBU-authorized exchange may be more suitable than independent raw-data pooling.

## 4. Personal data localization and cross-border processing — Law No. O'RQ-1125 (26 March 2026)

Official amendment:
https://www.lex.uz/en/docs/-8099215

Effective 27 March 2026; it rewrote Article 27¹ of the Personal Data Law No. O'RQ-547.

The following categories must be stored within Uzbekistan:
- biometric data of individuals;
- genetic data of individuals;
- data of individuals using services of telecommunications operators operating in Uzbekistan.

Other personal data may be stored/processed outside Uzbekistan only if one of the statutory conditions is met: recognition of the foreign country as providing equivalent protection; approved standard contractual clauses or binding corporate rules meeting the authorized body's requirements; or compliance with approved international standards for personal-data management/storage.

Do not overgeneralize this as a blanket localization rule for every personal-data category. The category, role of controller/operator/third party, transfer destination and applicable implementing lists must be checked separately.

FINZANJIR currently uses synthetic data only. Future hosting region, cloud provider, biometric/telecom feature handling, database registration and cross-border processing must be reviewed before any real data is enabled.

## 5. Immediate prototype controls

Current implementation status in this repository:
- API CORS allowlist and browser security headers are implemented; this is not authentication/RBAC.
- SQLite history stores only aggregate synthetic run summaries; it is not an authoritative case/audit ledger.
- All 40 detector rules are marked synthetic-only and bank-internal; unknown identity/raw-data feature names are rejected.
- Cross-bank matching remains synthetic and has no real bank connector.
- No real transaction, card, account, biometric, telecom subscriber or customer data is accepted by the detector feature API.
- No payment blocking or authoritative bank action exists.

These controls are deliberately conservative and do not constitute legal or regulatory compliance certification.

## 6. Questions requiring written confirmation before a bank pilot

1. What is the current operational status and exact scope of the Central Bank unified platform and centralized anti-fraud system under PQ-153 paragraph 9?
2. Is there an approved API/contract for a bank-side service provider to contribute risk indicators, explanations, evidence references or quality signals?
3. Can FINZANJIR be classified as an information/consulting service provider under Article 5 of the Banking Secrecy Law for a defined bank service, and what exact data may be accessed?
4. What fields may be exchanged bank-to-bank under Article 14, who authorizes the exchange, and what onward-use restrictions apply?
5. Which source fields are permitted for each of the 40 signals, and what retention, masking, pseudonymization and access rules apply?
6. Which hosting locations, processors and transfer mechanisms are acceptable under the amended Article 27¹?
7. How must a FINZANJIR risk signal interact with bank/CBU confirmation, customer notification, complaint handling and temporary restriction processes under Regulation 3513?

## 7. Architecture decision — pending

Recommended direction for consideration:
- FINZANJIR complements the Central Bank centralized anti-fraud system and bank anti-fraud systems rather than replacing or duplicating them.
- Keep source data at the bank/authorized Central Bank boundary wherever possible.
- Use a formally approved adapter/contract to exchange minimum necessary signals and references.
- Position FINZANJIR's differentiating work in multi-signal explanation, evidence quality, false-positive reduction, case workflow, complaint/appeal handling, audit and KPI.
- No independent raw interbank data lake, real Cross-Bank Matcher, real bank connector, biometric ingestion or payment-blocking function until legal authority and integration agreements are confirmed.

**Project owner decision required before changing the existing architecture.** Existing synthetic prototype functionality is preserved in the meantime.
