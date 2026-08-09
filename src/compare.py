"""
Compares the baseline regex parser and the AI (DeepSeek/OpenRouter) parser
against the hand-labeled ground truth, field by field.

Produces:
  - data/comparison_output.csv: per-file, per-field match/mismatch for both parsers
  - a printed summary: field-level accuracy % for each parser, plus average speed

Usage:
    python src/compare.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
OUTPUT_CSV = DATA_DIR / 'comparison_output.csv'

# Fields present in ground truth that both parsers can be scored against.
# Maps ground-truth column -> (baseline column, ai column). The two parsers
# use different column names for the same concept (baseline keeps raw/account
# fields separate; AI outputs a single cleaned field).
FIELD_MAP = {
    'reference': ('reference', 'reference'),
    'op_code': ('op_code', 'op_code'),
    'value_date': ('value_date', 'value_date'),
    'currency': ('currency', 'currency'),
    'amount': ('amount', 'amount'),
    'ordering_customer': ('ordering_customer_raw', 'ordering_customer'),
    'beneficiary': ('beneficiary_raw', 'beneficiary'),
}

# Ground truth uses the literal string "MISSING" for fields that are
# deliberately absent from the source message (see mt103_007). A parser is
# correct on that field if it also comes back empty -- there's nothing to
# extract, so matching "MISSING" the literal string isn't the right bar.
MISSING_SENTINEL = 'MISSING'


def normalize(value) -> str:
    """Lowercase/strip a value for tolerant comparison. Treats NaN/None as empty."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    return str(value).strip().lower()


def values_match(expected, actual) -> bool:
    expected_norm = normalize(expected)
    actual_norm = normalize(actual)

    if expected_norm == MISSING_SENTINEL.lower():
        return actual_norm == ''

    if expected_norm == '':
        return actual_norm == ''

    # Amounts: compare numerically so "15000" vs "15000.00" still matches.
    try:
        return abs(float(expected_norm) - float(actual_norm)) < 0.005
    except ValueError:
        pass

    return expected_norm == actual_norm


def main():
    ground_truth = pd.read_csv(DATA_DIR / 'mt103_ground_truth.csv').set_index('file')
    baseline = pd.read_csv(DATA_DIR / 'baseline_output.csv').set_index('file')
    ai = pd.read_csv(DATA_DIR / 'ai_output.csv').set_index('file')

    rows = []
    for file, truth_row in ground_truth.iterrows():
        for gt_field, (baseline_field, ai_field) in FIELD_MAP.items():
            expected = truth_row[gt_field]
            baseline_actual = baseline.loc[file, baseline_field] if file in baseline.index else None
            ai_actual = ai.loc[file, ai_field] if file in ai.index else None

            rows.append({
                'file': file,
                'field': gt_field,
                'expected': expected,
                'baseline_value': baseline_actual,
                'baseline_correct': values_match(expected, baseline_actual),
                'ai_value': ai_actual,
                'ai_correct': values_match(expected, ai_actual),
            })

    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUTPUT_CSV, index=False)
    print(f'Wrote per-field comparison -> {OUTPUT_CSV.relative_to(PROJECT_ROOT)}\n')

    # Per-field accuracy.
    print('Field-level accuracy (baseline vs AI):')
    per_field = comparison.groupby('field')[['baseline_correct', 'ai_correct']].mean() * 100
    for field, row in per_field.iterrows():
        print(f'  {field:20s} baseline {row["baseline_correct"]:5.1f}%   ai {row["ai_correct"]:5.1f}%')

    overall_baseline = comparison['baseline_correct'].mean() * 100
    overall_ai = comparison['ai_correct'].mean() * 100
    print(f'\nOverall accuracy: baseline {overall_baseline:.1f}%   ai {overall_ai:.1f}%')

    # Speed.
    baseline_avg_ms = baseline['parse_time_ms'].mean()
    ai_avg_ms = ai['parse_time_ms'].mean()
    print(f'\nAverage parse time: baseline {baseline_avg_ms:.3f} ms   ai {ai_avg_ms:.1f} ms')
    print(f'AI is ~{ai_avg_ms / baseline_avg_ms:,.0f}x slower per message (network round trip vs local regex).')

    # Mismatches worth calling out.
    mismatches = comparison[~comparison['baseline_correct'] | ~comparison['ai_correct']]
    if not mismatches.empty:
        print(f'\n{len(mismatches)} field-level mismatch(es):')
        for _, r in mismatches.iterrows():
            who = []
            if not r['baseline_correct']:
                who.append('baseline')
            if not r['ai_correct']:
                who.append('ai')
            print(f"  - {r['file']} [{r['field']}]: expected {r['expected']!r}, "
                  f"wrong on {', '.join(who)} "
                  f"(baseline={r['baseline_value']!r}, ai={r['ai_value']!r})")


if __name__ == '__main__':
    main()
