# Sample data

11 synthetic MT103 messages. **All fictional** — no real bank, customer, or account data.
Format follows the public SWIFT MT103 field specification.

| File | What it tests |
|---|---|
| mt103_001_standard.txt | Clean baseline message, all common fields present |
| mt103_002_missing_optional_field.txt | Optional `:52A:` (Ordering Institution) omitted |
| mt103_003_multiline_remittance.txt | `:70:` spans multiple lines |
| mt103_004_charge_code_ben.txt | `:71A:` = BEN (beneficiary pays all charges, vs OUR/SHA) |
| mt103_005_foreign_characters.txt | Accented characters in names/addresses (José, Müller) |
| mt103_006_jpy_no_decimals.txt | JPY has no decimal places — `:32A:` amount ends in a bare comma |
| mt103_007_malformed_missing_beneficiary.txt | Mandatory `:59:` (Beneficiary) missing — should fail/flag, not silently parse |
| mt103_008_intermediary_institution.txt | Adds optional `:56A:` (Intermediary Institution), between ordering and account-with bank |
| mt103_009_high_value_anomaly.txt | Unusually large amount, vague beneficiary — anomaly-flagging test case |
| mt103_010_long_remittance_max_lines.txt | `:70:` at max length (4 lines x 35 chars, SWIFT's real limit) |
| mt103_011_special_chars_beneficiary.txt | Beneficiary name has a comma, full stop, and plus sign — needs cleaning before use |

## Field glossary (as used in this project)

- `:20:` Sender's Reference
- `:23B:` Bank Operation Code (`CRED` = standard credit transfer)
- `:32A:` Value Date + Currency + Amount
- `:50K:` Ordering Customer (payer)
- `:52A:` Ordering Institution (payer's bank) — optional
- `:56A:` Intermediary Institution — optional, used when funds route through a third bank
- `:57A:` Account With Institution (beneficiary's bank)
- `:59:` Beneficiary Customer (payee) — mandatory
- `:70:` Remittance Information (free text — what the payment is for)
- `:71A:` Details of Charges — `OUR` (payer covers all fees), `SHA` (shared), `BEN` (beneficiary covers all fees)
