# Project: AI-Powered SWIFT MT103 Parser (Portfolio Project)

## Context
Suman Khera, a Data Analyst (SQL/Python/Power BI/Tableau background) building this as a
GitHub portfolio piece for data analyst/BA interviews, including an upcoming Scotiabank
Market Risk BA Specialist interview. Broader goal: move from a data-analytics role into a
data-analytics + AI role, and increase reach in the job market.

Goal for this project: show the ability to go from raw problem -> rule-based baseline ->
AI-enhanced solution -> clear comparison, with a working demo.

## Build order (tracked in Linear — team "AI Projects", project "AI-Powered SWIFT Payment Message Parser")
1. Baseline rule-based parser — regex extraction of fixed-tag fields (ground truth)
2. AI layer — Claude API for field extraction (structured JSON), remittance classification, anomaly flagging
3. Comparison — rule-based vs AI: accuracy, speed, edge cases (this is the project's value prop / README centerpiece)
4. Streamlit interface — paste message -> parsed JSON + flags side by side
5. Stretch: batch processing + CSV export
6. Stretch: anomaly dashboard (Tableau/matplotlib)

## Tech stack
Python, regex, Claude API, Streamlit, pandas.

## How to help
- Default to concise, direct answers — code and explanations, not padding.
- When writing code, prioritize readability and comments that can be explained confidently
  in an interview — understand every line, not just paste it.
- Flag anything that would be a good interview talking point (STAR-format material) as we go.
- When stuck on scope, default to shipping v1 (steps 1-4) over stretch goals.
- SWIFT MT103 field knowledge may need occasional refreshers — briefly explain new terms
  (e.g., tag 59, 70, 71A) the first time they come up.
