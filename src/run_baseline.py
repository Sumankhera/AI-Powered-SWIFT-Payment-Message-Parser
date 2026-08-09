"""
Runs the baseline regex parser over every sample message in data/raw/
and writes the results to data/baseline_output.csv.

Usage:
    python src/run_baseline.py
"""

import csv
import time
from pathlib import Path

from parser.baseline_parser import parse_mt103_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / 'data' / 'raw'
OUTPUT_CSV = PROJECT_ROOT / 'data' / 'baseline_output.csv'


def main():
    files = sorted(RAW_DATA_DIR.glob('mt103_*.txt'))

    rows = []
    for f in files:
        start = time.perf_counter()
        row = parse_mt103_file(f)
        row['parse_time_ms'] = round((time.perf_counter() - start) * 1000, 3)
        rows.append(row)

    with OUTPUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f'Parsed {len(rows)} messages -> {OUTPUT_CSV.relative_to(PROJECT_ROOT)}')

    flagged = [r for r in rows if r['missing_mandatory_fields'] or r['amount_parse_error']]
    if flagged:
        print(f'\n{len(flagged)} message(s) flagged:')
        for r in flagged:
            reason = r['missing_mandatory_fields'] or r['amount_parse_error']
            print(f"  - {r['file']}: {reason}")


if __name__ == '__main__':
    main()
