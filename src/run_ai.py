"""
Runs the AI (Claude API) parser over every sample message in data/raw/
and writes the results to data/ai_output.csv.

Requires ANTHROPIC_API_KEY to be set in a .env file in the project root.

Usage:
    python src/run_ai.py
"""

import csv
from pathlib import Path

from parser.ai_parser import build_client, parse_mt103_file_with_ai

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / 'data' / 'raw'
OUTPUT_CSV = PROJECT_ROOT / 'data' / 'ai_output.csv'

FIELDNAMES = [
    'file', 'reference', 'op_code', 'value_date', 'currency', 'amount',
    'ordering_customer', 'beneficiary', 'remittance_info',
    'remittance_classification', 'charges_code',
    'anomaly_flag', 'anomaly_reason', 'parse_error',
]


def main():
    client = build_client()
    files = sorted(RAW_DATA_DIR.glob('mt103_*.txt'))

    rows = []
    for f in files:
        try:
            rows.append(parse_mt103_file_with_ai(f, client))
        except Exception as exc:
            # Don't let one bad response kill the whole batch -- record the
            # failure and keep going, same spirit as the baseline parser's
            # missing_mandatory_fields flag.
            print(f'  ! failed on {f.name}: {exc}')
            rows.append({name: None for name in FIELDNAMES} | {'file': f.name, 'parse_error': str(exc)})

    with OUTPUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f'Parsed {len(rows)} messages -> {OUTPUT_CSV.relative_to(PROJECT_ROOT)}')

    flagged = [r for r in rows if r.get('anomaly_flag') or r.get('parse_error')]
    if flagged:
        print(f'\n{len(flagged)} message(s) flagged:')
        for r in flagged:
            reason = r.get('anomaly_reason') or r.get('parse_error')
            print(f"  - {r['file']}: {reason}")


if __name__ == '__main__':
    main()
