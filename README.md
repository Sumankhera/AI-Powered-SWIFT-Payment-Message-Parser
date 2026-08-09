# AI-Powered SWIFT MT103 Parser

Portfolio project comparing a rule-based baseline parser against an AI-enhanced parser
for SWIFT MT103 payment messages — built to demonstrate moving from a data-analytics
skillset into data-analytics + AI.

## Problem

Bank ops teams manually read SWIFT MT103/MT202 messages to extract data for
reconciliation, reporting, or investigation. This project automates extraction —
including messy free-text fields (like `:70: remittance info`) that regex struggles with.

## Build order

1. Baseline rule-based parser — regex extraction of fixed-tag fields (ground truth)
2. AI layer — Claude API for field extraction (structured JSON), remittance
   classification, anomaly flagging
3. Comparison — rule-based vs AI: accuracy, speed, edge cases
4. Streamlit interface — paste message -> parsed JSON + flags side by side
5. Stretch: batch processing + CSV export
6. Stretch: anomaly dashboard (Tableau/matplotlib)

## Tech stack

Python, regex, DeepSeek V4 Pro (via OpenRouter), Streamlit, pandas.

## Comparison: regex baseline vs AI

Both parsers run against the same 11 synthetic MT103 messages (`data/raw/`), scored
against a hand-labeled ground truth (`data/mt103_ground_truth.csv`). Reproduce with:

```
python src/run_baseline.py
python src/run_ai.py
python src/compare.py
```

| Field              | Baseline (regex) | AI (DeepSeek) |
|--------------------|:-----------------:|:-------------:|
| reference          | 100.0%            | 100.0%        |
| op_code            | 100.0%            | 100.0%        |
| value_date         | 100.0%            | 90.9%         |
| currency           | 100.0%            | 100.0%        |
| amount             | 100.0%            | 100.0%        |
| ordering_customer  | 100.0%            | 100.0%        |
| beneficiary        | 100.0%            | 90.9%         |
| **Overall**        | **100.0%**        | **97.4%**     |
| Avg. parse time    | 0.6 ms            | ~18,000 ms    |

Baseline wins on paper here for two reasons that are worth reading past the raw number:
- **Ground truth stores literal raw text.** On `mt103_011`, the beneficiary field is
  genuinely `"ACME TRADING LLC ,. +sos"` (junk punctuation and all). The AI cleaned it to
  `"ACME TRADING LLC"` — more useful for a real ops workflow, but it fails an exact-string
  match against ground truth. Regex "wins" that field only because it didn't try to clean
  anything.
- **Date formatting is occasionally inconsistent.** The AI got the correct date *value*
  once an explicit YYMMDD rule was added to the prompt, but on one run it returned the
  raw digits (`270114`) instead of the requested `YYYY-MM-DD` format — a reminder that
  LLM output shape needs validation even when using structured tool calls.

### Pros and cons

| | Regex baseline | AI (LLM) parser |
|---|---|---|
| **Pros** | Deterministic — same input always gives same output. Effectively instant (sub-millisecond). Free, no external dependency or network call. Fails loudly and predictably on malformed/missing fields. | Handles messy, unstructured free text (junk punctuation, inconsistent spacing) without new regex rules. Classifies remittance purpose from natural language. Flags semantic anomalies (suspicious beneficiary names, unusually high amounts) that have no fixed pattern to match against. |
| **Cons** | Can't interpret or clean free text — a beneficiary field with typos or junk characters comes back exactly as messy as it went in. No semantic understanding: can't classify intent or judge whether an amount is "unusual." Every new message quirk needs a new regex rule. | ~30,000x slower per message (network round trip vs. local computation). Costs money per call. Occasionally inconsistent formatting (e.g. date format) even with a schema-enforced response. Requires retry logic for malformed responses. Non-deterministic — same input can occasionally produce different output across runs. |

**Takeaway:** regex is the right tool for strict, fixed-format fields where speed and
determinism matter (reference numbers, amounts, currency codes). AI earns its cost on the
fields regex structurally cannot handle — free text cleanup, classification, and anomaly
judgment. A production pipeline would likely use both: regex for the fast, mandatory
fields, AI for classification/anomaly flags and as a fallback when regex fields are
missing or malformed.

## Status

Work in progress — tracked in [Linear](https://linear.app/aiprojectswift/project/ai-powered-swift-payment-message-parser-ab4f541288e4).
