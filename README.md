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

Python, regex, Claude API, Streamlit, pandas.

## Status

Work in progress — tracked in [Linear](https://linear.app/aiprojectswift/project/ai-powered-swift-payment-message-parser-ab4f541288e4).
