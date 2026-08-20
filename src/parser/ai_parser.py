"""
AI-powered MT103 parser using DeepSeek V4 Pro via OpenRouter.

Where baseline_parser.py uses regex to extract fixed-position fields, this
module hands the raw message to the model and asks it to do three things
regex structurally cannot:
  1. Extract the same core fields, but tolerate messy/unstructured text
     (see mt103_011's "ACME TRADING LLC ,. +sos").
  2. Classify the free-text :70: remittance line into a purpose category.
  3. Flag anomalies (missing fields, suspiciously high amounts, malformed
     structure) with a short human-readable reason.

Uses tool calling (function-calling) rather than free-text prompting so the
response is a schema-validated dict, not prose we'd have to parse -- see
AI-7 discussion for why that matters for a reliable batch pipeline.

OpenRouter is an API gateway that speaks the OpenAI-compatible chat
completions format, so we use the `openai` SDK pointed at OpenRouter's
base URL rather than a provider-specific SDK.
"""

import os
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = 'deepseek/deepseek-v4-pro'
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

# This "tool" is never actually executed -- we force the model to call it
# purely to get a schema-validated JSON object back instead of free-form text.
EXTRACTION_TOOL = {
    'type': 'function',
    'function': {
        'name': 'record_mt103_fields',
        'description': 'Record the extracted fields from an MT103 SWIFT payment message.',
        'parameters': {
            'type': 'object',
            'properties': {
                'reference': {'type': 'string', 'description': 'Sender reference from field :20:'},
                'op_code': {'type': 'string', 'description': 'Bank operation code from field :23B:, e.g. CRED'},
                'value_date': {'type': 'string', 'description': 'Value date from :32A: as YYYY-MM-DD'},
                'currency': {'type': 'string', 'description': '3-letter currency code from :32A:'},
                'amount': {'type': 'number', 'description': 'Payment amount from :32A: as a plain number'},
                'ordering_customer': {'type': 'string', 'description': 'Cleaned name of the ordering customer from :50K:'},
                'beneficiary': {'type': 'string', 'description': 'Cleaned name of the beneficiary from :59:, with stray punctuation/junk removed'},
                'remittance_info': {'type': 'string', 'description': 'Cleaned free-text remittance purpose from :70:'},
                'remittance_classification': {
                    'type': 'string',
                    'description': 'One-word category for the payment purpose, e.g. invoice, consulting, trade_settlement, payroll, other',
                },
                'charges_code': {'type': 'string', 'description': 'Charges code from :71A:, e.g. OUR, SHA, BEN'},
                'anomaly_flag': {'type': 'boolean', 'description': 'True if anything about this message looks unusual or incomplete'},
                'anomaly_reason': {
                    'type': ['string', 'null'],
                    'description': 'Short reason for the anomaly flag, or null if not flagged',
                },
            },
            'required': [
                'reference', 'op_code', 'value_date', 'currency', 'amount',
                'ordering_customer', 'beneficiary', 'remittance_info',
                'remittance_classification', 'charges_code',
                'anomaly_flag', 'anomaly_reason',
            ],
        },
    },
}

PROMPT_TEMPLATE = """You are parsing a raw SWIFT MT103 payment message. Extract the fields \
using the record_mt103_fields tool. If a field is missing from the message, use an empty \
string for text fields (not "N/A" or similar). Judge amount, structure, and content for \
anything that looks unusual (e.g. missing mandatory fields, unusually high amount, garbled \
beneficiary text) and set anomaly_flag/anomaly_reason accordingly.

Date rule: the value date inside field :32A: is ALWAYS six digits in strict YYMMDD order \
(year, then month, then day) -- e.g. "270114" means 2027-01-14, never 2014-01-27 and never \
2027-14-01. Do not treat it as ambiguous or reformat it any other way.

Message:
{raw_text}"""


MAX_ATTEMPTS = 3


def parse_mt103_text_with_ai(raw_text: str, client: OpenAI, file: str = None) -> dict:
    """Send raw MT103 message text to the model and return the extracted fields as a dict.

    Split out from parse_mt103_file_with_ai() so the Streamlit app (src/app.py)
    can parse pasted text directly, without needing a file on disk.

    Retries on malformed tool-call JSON (the model occasionally emits broken
    JSON on genuinely ambiguous input) before giving up and returning an error row.
    """
    import json

    messages = [{'role': 'user', 'content': PROMPT_TEMPLATE.format(raw_text=raw_text)}]

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.chat.completions.create(
            model=MODEL,
            tools=[EXTRACTION_TOOL],
            tool_choice={'type': 'function', 'function': {'name': 'record_mt103_fields'}},
            messages=messages,
        )
        tool_call = response.choices[0].message.tool_calls[0]
        try:
            data = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

        data['file'] = file
        data['parse_error'] = None
        return data

    raise RuntimeError(f'malformed JSON after {MAX_ATTEMPTS} attempts: {last_error}')


def parse_mt103_file_with_ai(path: Path, client: OpenAI) -> dict:
    """Send one MT103 message file to the model and return the extracted fields as a dict."""
    raw_text = path.read_text(encoding='utf-8')
    return parse_mt103_text_with_ai(raw_text, client, file=path.name)


def build_client() -> OpenAI:
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise RuntimeError(
            'OPENROUTER_API_KEY not set. Add it to a .env file in the project root, e.g.\n'
            'OPENROUTER_API_KEY=sk-or-...'
        )
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
