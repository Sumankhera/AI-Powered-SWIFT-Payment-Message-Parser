"""
Streamlit demo: paste a raw MT103 message and see the baseline regex parser
and the AI parser (DeepSeek via OpenRouter) run side by side. Also supports
batch mode: upload multiple messages, parse them all, and export as CSV.

This is the interactive counterpart to src/compare.py -- that script proves
the accuracy/speed numbers in bulk over the sample set, this app lets you
see the same behaviour live (one message at a time, or a batch).

Usage:
    streamlit run src/app.py
"""

import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from parser.baseline_parser import parse_mt103_text
from parser.ai_parser import build_client, parse_mt103_text_with_ai

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / 'data' / 'raw'
AI_OUTPUT_CSV = PROJECT_ROOT / 'data' / 'ai_output.csv'

st.set_page_config(page_title='SWIFT MT103 Parser', layout='wide')
st.title('SWIFT MT103 Parser: Baseline (regex) vs AI (DeepSeek)')
st.caption(
    'Paste a raw MT103 message, or load one of the sample edge cases, then '
    'compare the rule-based baseline parser against the AI-powered parser.'
)

sample_files = sorted(RAW_DATA_DIR.glob('mt103_*.txt'))

single_tab, batch_tab, dashboard_tab = st.tabs(['Single message', 'Batch', 'Anomaly Dashboard'])

with single_tab:
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

with batch_tab:
    st.caption(
        'Upload one or more raw MT103 .txt files (or leave empty to run over the '
        'bundled sample set), parse them all with both parsers, and export the '
        'combined results as CSV.'
    )

    uploaded_files = st.file_uploader(
        'Upload MT103 message files', type='txt', accept_multiple_files=True,
    )
    run_ai_in_batch = st.checkbox('Also run the AI parser (slower -- one API call per message)', value=False)

    batch_clicked = st.button('Run batch', type='primary')

    if batch_clicked:
        if uploaded_files:
            batch_inputs = [(f.name, f.read().decode('utf-8')) for f in uploaded_files]
        else:
            batch_inputs = [(f.name, f.read_text(encoding='utf-8')) for f in sample_files]

        client = None
        if run_ai_in_batch:
            try:
                client = build_client()
            except RuntimeError as exc:
                st.error(str(exc))
                run_ai_in_batch = False

        rows = []
        progress = st.progress(0.0, text='Parsing...')
        for i, (name, text) in enumerate(batch_inputs, start=1):
            row = {'file': name}

            start = time.perf_counter()
            baseline_result = parse_mt103_text(text, file=name)
            row['baseline_ms'] = round((time.perf_counter() - start) * 1000, 3)
            row['baseline_flag'] = (
                baseline_result.get('missing_mandatory_fields') or baseline_result.get('amount_parse_error')
            )
            for key in ('reference', 'op_code', 'value_date', 'currency', 'amount'):
                row[f'baseline_{key}'] = baseline_result.get(key)

            if run_ai_in_batch and client is not None:
                start = time.perf_counter()
                try:
                    ai_result = parse_mt103_text_with_ai(text, client, file=name)
                except Exception as exc:
                    ai_result = {'parse_error': str(exc)}
                row['ai_ms'] = round((time.perf_counter() - start) * 1000, 3)
                row['ai_flag'] = ai_result.get('anomaly_reason') or ai_result.get('parse_error')
                for key in ('reference', 'op_code', 'value_date', 'currency', 'amount', 'remittance_classification'):
                    row[f'ai_{key}'] = ai_result.get(key)

            rows.append(row)
            progress.progress(i / len(batch_inputs), text=f'Parsed {i}/{len(batch_inputs)}')

        progress.empty()

        results_df = pd.DataFrame(rows)
        st.session_state['batch_results'] = results_df

    if 'batch_results' in st.session_state:
        results_df = st.session_state['batch_results']
        st.dataframe(results_df, use_container_width=True)
        st.download_button(
            'Download results as CSV',
            data=results_df.to_csv(index=False),
            file_name='mt103_batch_results.csv',
            mime='text/csv',
        )

with dashboard_tab:
    st.caption(
        'Anomaly and classification breakdown from the AI parser run over the '
        'full sample set (data/ai_output.csv -- generated by src/run_ai.py).'
    )

    if not AI_OUTPUT_CSV.exists():
        st.warning(f'{AI_OUTPUT_CSV.relative_to(PROJECT_ROOT)} not found. Run `python src/run_ai.py` first.')
    else:
        ai_df = pd.read_csv(AI_OUTPUT_CSV)
        # 'False'/'True' round-trip through CSV as strings, not bools.
        ai_df['anomaly_flag'] = ai_df['anomaly_flag'].astype(str).str.lower() == 'true'

        flagged_count = int(ai_df['anomaly_flag'].sum())
        clean_count = len(ai_df) - flagged_count

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric('Messages parsed', len(ai_df))
        metric_col2.metric('Flagged as anomalous', flagged_count)
        metric_col3.metric('Anomaly rate', f'{flagged_count / len(ai_df) * 100:.0f}%')

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader('Flagged vs. clean')
            fig, ax = plt.subplots(figsize=(4, 4))
            ax.pie(
                [clean_count, flagged_count],
                labels=['Clean', 'Flagged'],
                colors=['#4C72B0', '#C44E52'],
                autopct='%1.0f%%',
                startangle=90,
            )
            st.pyplot(fig)

        with chart_col2:
            st.subheader('Remittance classification')
            fig, ax = plt.subplots(figsize=(4, 4))
            class_counts = ai_df['remittance_classification'].value_counts()
            ax.bar(class_counts.index, class_counts.values, color='#4C72B0')
            ax.set_ylabel('Count')
            plt.xticks(rotation=45, ha='right')
            fig.tight_layout()
            st.pyplot(fig)

        st.subheader('Amount by message, anomalies highlighted')
        fig, ax = plt.subplots(figsize=(10, 4))
        colors = ai_df['anomaly_flag'].map({True: '#C44E52', False: '#4C72B0'})
        ax.bar(ai_df['file'], ai_df['amount'], color=colors)
        ax.set_ylabel('Amount (message currency)')
        ax.set_yscale('log')
        plt.xticks(rotation=45, ha='right')
        fig.tight_layout()
        st.pyplot(fig)

        flagged_df = ai_df[ai_df['anomaly_flag']][['file', 'currency', 'amount', 'anomaly_reason']]
        if not flagged_df.empty:
            st.subheader('Flagged messages')
            st.dataframe(flagged_df, use_container_width=True)
