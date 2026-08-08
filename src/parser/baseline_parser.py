"""
Baseline rule-based MT103 parser.

This is the "ground truth" control for the project: pure regex, zero AI,
zero external dependencies. Its job is to show exactly where a purely
rule-based approach breaks down (missing fields, messy free text, unusual
punctuation) -- that gap is what the AI layer (see AI-7) is meant to close.
"""

import re
from datetime import datetime
from pathlib import Path

# Matches a field tag line, e.g. ":20:REF20260315001" -> tag="20", value="REF20260315001"
# Tag format is 2 digits + an optional single letter (K, A, B ...).
TAG_PATTERN = re.compile(r'^:(\d{2}[A-Z]?):(.*)$')

# These tags are allowed to spill onto multiple lines in real MT103 messages.
# Everything else (:20:, :23B:, :52A:, :57A:, :71A: ...) is always one line.
MULTILINE_TAGS = {'50K', '59', '70'}

# Fields a valid MT103 must have. Used to flag incomplete messages instead
# of silently parsing them as if nothing were wrong.
MANDATORY_TAGS = {'20', '23B', '32A', '50K', '59', '71A'}


def split_into_fields(raw_text: str) -> dict:
    """
    Break the message body into {tag: raw_value} pairs.

    Continuation lines (no leading ':tag:') get appended to whichever tag
    was most recently seen, with a newline in between -- this is what lets
    a 4-line :70: remittance field come back out as one multi-line string.
    """
    fields = {}
    current_tag = None

    # The real content lives between "{4:" and the closing "-}"; everything
    # before that ({1:...}{2:...}) is routing/header info we don't need here.
    body = raw_text.split('{4:', 1)[-1]
    body = body.rsplit('-}', 1)[0]

    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue

        match = TAG_PATTERN.match(line)
        if match:
            current_tag, value = match.groups()
            fields[current_tag] = value
        elif current_tag:
            fields[current_tag] += '\n' + line

    return fields


def parse_amount_field(raw_32a: str) -> dict:
    """
    :32A: packs value date + currency + amount into one string with no
    separators, e.g. '260315USD15000,00'. Two SWIFT quirks to handle:
      - dates are YYMMDD
      - the decimal separator is a COMMA, not a period (European convention)
      - currencies with no minor unit (e.g. JPY) leave a trailing comma
        with nothing after it, e.g. '2500000,'
    """
    if not raw_32a:
        return {'value_date': None, 'currency': None, 'amount': None,
                'amount_parse_error': 'missing :32A: field'}

    match = re.match(r'^(\d{6})([A-Z]{3})([\d,]+)$', raw_32a)
    if not match:
        return {'value_date': None, 'currency': None, 'amount': None,
                'amount_parse_error': f'unrecognized format: {raw_32a!r}'}

    date_str, currency, amount_str = match.groups()
    value_date = datetime.strptime(date_str, '%y%m%d').strftime('%Y-%m-%d')
    amount = float(amount_str.replace(',', '.'))

    return {'value_date': value_date, 'currency': currency, 'amount': amount,
            'amount_parse_error': None}


def parse_party_field(raw_value: str) -> dict:
    """
    :50K: (ordering customer) and :59: (beneficiary) share the same shape:
    an optional '/account' line, then up to 4 lines of name/address, e.g.

        /98765432
        ACME TRADING LLC
        500 5TH AVENUE
        NEW YORK NY US

    We keep line 2 as the raw name and join the rest as the address. This
    is deliberately naive -- it does NOT clean stray punctuation (see
    mt103_011's "ACME TRADING LLC ,. +sos"). That gap is intentional: it's
    exactly the kind of cleanup the AI layer should do better than regex.
    """
    if not raw_value:
        return {'account': None, 'name_raw': None, 'address': None}

    lines = raw_value.split('\n')
    account = None
    if lines and lines[0].startswith('/'):
        account = lines[0][1:]
        lines = lines[1:]

    name_raw = lines[0] if lines else None
    address = ' '.join(lines[1:]) if len(lines) > 1 else None

    return {'account': account, 'name_raw': name_raw, 'address': address}


def parse_mt103_file(path: Path) -> dict:
    """Parse one MT103 .txt file into a flat dict of extracted fields."""
    raw_text = path.read_text(encoding='utf-8')
    fields = split_into_fields(raw_text)

    missing = MANDATORY_TAGS - fields.keys()
    amount_info = parse_amount_field(fields.get('32A'))
    ordering = parse_party_field(fields.get('50K'))
    beneficiary = parse_party_field(fields.get('59'))

    return {
        'file': path.name,
        'reference': fields.get('20'),
        'op_code': fields.get('23B'),
        'value_date': amount_info['value_date'],
        'currency': amount_info['currency'],
        'amount': amount_info['amount'],
        'ordering_account': ordering['account'],
        'ordering_customer_raw': ordering['name_raw'],
        'beneficiary_account': beneficiary['account'],
        'beneficiary_raw': beneficiary['name_raw'],
        'remittance_info_raw': (fields.get('70') or '').replace('\n', ' '),
        'charges_code': fields.get('71A'),
        'intermediary_bic': fields.get('56A'),
        'missing_mandatory_fields': ','.join(sorted(missing)) if missing else None,
        'amount_parse_error': amount_info['amount_parse_error'],
    }
