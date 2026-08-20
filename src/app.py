"""
Streamlit demo: paste a raw MT103 message and see the baseline regex parser
and the AI parser (DeepSeek via OpenRouter) run side by side.

This is the interactive counterpart to src/compare.py -- that script proves
the accuracy/speed numbers in bulk over the sample set, this app lets you
see the same behaviour on a single message, live.

Usage:
    streamlit run src/app.py
"""

import time
from pathlib import Path

import streamlit as st

from parser.baseline_parser import parse_mt103_text
from parser.ai_parser import build_client, parse_mt103_text_with_ai

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / 'data' / 'raw'

st.set_page_config(page_title='SWIFT MT103 Parser', layout='wide')
st.title('SWIFT MT103 Parser: Baseline (regex) vs AI (DeepSeek)')
st.caption(
    'Paste a raw MT103 message, or load one of the sample edge cases, then '
    'compare the rule-based baseline parser against the AI-powered parser.'
)

sample_files = sorted(RAW_DATA_DIR.glob('mt103_*.txt'))
sample_names = ['-- paste your own --'] + [f.name for f in sample_files]

chosen = st.selectbox('Load a sample message', sample_names)

if chosen != sample_names[0]:
    default_text = (RAW_DATA_DIR / chosen).read_text(encoding='utf-8')
else:
    default_text = ''

raw_text = st.text_area('Raw MT103 message', value=default_text, height=280)

parse_clicked = st.button('Parse', type='primary', disabled=not raw_text.strip())

if parse_clicked:
    baseline_col, ai_col = st.columns(2)

    with baseline_col:
        st.subheader('Baseline (regex)')
        start = time.perf_counter()
        baseline_result = parse_mt103_text(raw_text)
        baseline_ms = (time.perf_counter() - start) * 1000

        warning = baseline_result.get('missing_mandatory_fields') or baseline_result.get('amount_parse_error')
        if warning:
            st.warning(f'Flagged: {warning}')

        st.json(baseline_result)
        st.caption(f'Parse time: {baseline_ms:.3f} ms')

    with ai_col:
        st.subheader('AI (DeepSeek via OpenRouter)')
        try:
            client = build_client()
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            with st.spinner('Calling the model...'):
                start = time.perf_counter()
                try:
                    ai_result = parse_mt103_text_with_ai(raw_text, client)
                except Exception as exc:
                    ai_result = None
                    st.error(f'AI parse failed: {exc}')
                ai_ms = (time.perf_counter() - start) * 1000

            if ai_result is not None:
                if ai_result.get('anomaly_flag'):
                    st.warning(f"Anomaly flagged: {ai_result.get('anomaly_reason')}")
                if ai_result.get('remittance_classification'):
                    st.info(f"Remittance category: {ai_result['remittance_classification']}")

                st.json(ai_result)
                st.caption(f'Parse time: {ai_ms:.1f} ms')
else:
    st.info('Paste a message (or load a sample above) and click Parse.')
