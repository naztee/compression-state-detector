import os
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from data import search, history, DataError
from engine import analyze, outcomes, baseline_report, STATES, VERSION, state_checks
from store import Store, runtime_db_path
from recovered import analyze_recovered
st.set_page_config(page_title='Compression Observatory',page_icon='◈',layout='wide')
st.markdown('''<style>.block-container{padding-top:2rem;max-width:1450px}div[data-testid="stMetric"]{background:#152033;padding:16px;border-radius:12px}h1{letter-spacing:-.04em}</style>''',unsafe_allow_html=True)
st.title('Compression Observatory')
st.caption('MARKET LIFECYCLE • DAILY UTC • RESEARCH EDITION')
st.warning('Two separate models: recovered research score requires genuine 114-day OHLC history; experimental S0–S5 remains unvalidated. Score categories are not lifecycle states. Neither model is an automatic entry or sizing signal.')
if not os.getenv('COINGECKO_DEMO_API_KEY'):
    try:
        if st.secrets.get('COINGECKO_DEMO_API_KEY'): os.environ['COINGECKO_DEMO_API_KEY']=st.secrets['COINGECKO_DEMO_API_KEY']
    except FileNotFoundError: pass
active_db=runtime_db_path()
store=Store(active_db)
page=st.sidebar.radio('Workspace',['Individual Coin Analysis','Market Scanner','State Transition Monitor','Historical State Charts','Data Quality Indicators','Rules & Validation'])
st.sidebar.caption(f'Rule version: {VERSION} · $0 public data stack')
@st.cache_data(ttl=3600,show_spinner=False)
def lookup(q): return search(q)
@st.cache_data(ttl=21600,show_spinner=False)
def fetch(cid): return history(cid)
def table(df): st.dataframe(df,width='stretch',hide_index=True)
def display_history(cid,h,raw):
    research=analyze_recovered(raw)
    st.subheader('Recovered research score · separate from S0–S5')
    rr=research.iloc[-1] if not research.empty else None
    if rr is None or rr.research_quality != 'OK':
        st.warning('Recovered score unavailable: genuine aligned daily OHLC plus historical market cap and volume are required for 114 completed UTC days. CoinGecko reference-price history alone is insufficient.')
        if rr is not None: st.caption(rr.research_quality)
    else:
        cols=st.columns(3)
        cols[0].metric('Recovered score',f'{rr.research_score:.2f}')
        cols[1].metric('Research score category',rr.research_category)
        cols[2].metric('V20 five-gate candidate','PASS' if rr.research_v20 else 'FAIL')
        st.caption('Recovered V21 scoring functions + frozen V20 guide gates. Source-dependent research result; not a verified reproduction of the original backtest. COOLING 30–59 is not S2. No extra Q4-return entry gate is added.')
        if rr.research_failed_gates: st.write('Failed candidate gates: '+rr.research_failed_gates)
        table(research.tail(1))
    with st.expander('Recovered research history and CSV export'):
        table(research)
        st.download_button('Download recovered research',research.to_csv(index=False),file_name=f'{cid}_recovered.csv')
    latest=h.iloc[-1]; state=latest.state
    st.subheader(f'{cid} · {state} — {STATES.get(state,state.title())}')
    st.caption(f'As of {latest.date} UTC · historical sample date, not live price')
    if (pd.Timestamp.now(tz='UTC').normalize()-pd.Timestamp(latest.date,tz='UTC')).days>2: st.error('STALE DATA: latest sample is more than 2 days old.')
    cols=st.columns(4)
    vals=[('Experimental score · not V20',latest.get('score')),('Momentum · 7 days',latest.get('momentum7')),('Observed duration',f'{latest.duration_days} days'),('Previous state',latest.previous_state or 'Unknown')]
    for col,(label,value) in zip(cols,vals): col.metric(label,'N/A' if value is None or (isinstance(value,float) and pd.isna(value)) else f'{value:.2f}' if isinstance(value,float) else value)
    cols=st.columns(4)
    for col,label,key in zip(cols,['Distance above 84D sample low','30D sample range','Directional bias','Historical market cap'],['location84','range30','bias','market_cap']):
        v=latest.get(key); col.metric(label,'N/A' if v is None or pd.isna(v) else f'${v:,.0f}' if key=='market_cap' else f'{v:.2f}%' if key in ('location84','range30') else v)
    st.caption('Duration begins at first valid observed classification; earlier state may predate available history. Daily samples miss intraday extremes.')
    if latest.quality!='OK': st.error(latest.quality)
    else:
        st.info('Experimental model eligibility: not original V20. See recovered research results above; missing OHLC prevents recovered eligibility.')
        st.caption(f'Experimental five-gate proxy: {bool(latest.get("v20_provisional_proxy",False))}. This substitutes a different score; it does not establish V20 eligibility.')
        q=pd.DataFrame({'Period':['Q1 · oldest','Q2','Q3','Q4 · newest'],'Vol / MC %':[latest[f'q{i}'] for i in range(1,5)]})
        st.plotly_chart(px.bar(q,x='Period',y='Vol / MC %',title='Four consecutive 21-day periods'),width='stretch')
    with st.expander('Why this state? · exact conditions', expanded=True):
        if latest.quality != 'OK':
            st.write('UNKNOWN: required history is incomplete. State rules are not evaluated.')
        else:
            checks=pd.DataFrame(state_checks(latest))
            summary=checks.groupby('state',sort=False).result.apply(lambda x: 'QUALIFIES' if x.eq('PASS').all() else 'DOES NOT QUALIFY').reset_index(name='Rule result')
            table(summary)
            st.caption('Precedence: S0 → S4 → S5 → S3 → S2 → S1. First qualifying state wins. UNCLASSIFIED means none qualify; it is not S3. These are provisional rules, separate from direction and V20 eligibility.')
            table(checks)
            st.caption('Metric key: r7/r21 = 7/21-day return (%); q4 = mean daily Vol/MC (%) in newest 21-day period; q4_return = 21-day return (%); range30 = sampled 30-day range (%); off_high21 = distance below 21-day high (%); vol_ratio = last 7-day mean volume / preceding 21-day mean. S4 price threshold is the prior 30-day high.')
    st.plotly_chart(px.line(raw,x='date',y='price',title='CoinGecko USD daily reference price'),width='stretch')
    good=h[h.state.ne('UNKNOWN')]
    if not good.empty: st.plotly_chart(px.scatter(good,x='date',y='price',color='state',hover_data=['score','bias'],title='Historical classifications'),width='stretch')
    st.subheader('State transitions'); table(h[h.transition])
    with st.expander('Full daily history'): table(h)
    st.download_button('Download daily classifications',h.to_csv(index=False),file_name=f'{cid}_states.csv')
    st.subheader('Baseline comparison · 30-day horizon')
    st.caption('Descriptive, single-coin results. Entries use next daily reference sample; signals spaced ≥31 days per cohort. No fees, funding, execution costs, intraday excursions or portfolio simulation. Current-universe selection can be survivorship-biased. No predictive probabilities.')
    table(baseline_report(raw,h))
    with st.expander('Forward returns and daily-sampled MAE/MFE'):
        table(outcomes(raw,h[h.transition]))
if page=='Individual Coin Analysis':
    q=st.text_input('Search a cryptocurrency','bitcoin')
    uploaded=st.file_uploader('Import genuine daily CSV: date, market_cap, volume and price; add open, high, low, close for recovered research',type='csv')
    if uploaded:
        try:
            raw=pd.read_csv(uploaded); raw['price']=raw['price'] if 'price' in raw else raw['close']; h=analyze(raw); display_history('uploaded-data',h,raw)
        except Exception as e: st.error(f'Cannot analyze CSV: {e}')
    elif q:
        try:
            options=lookup(q)
            if not options: st.info('No supported CoinGecko IDs found.')
            else:
                c=st.selectbox('Confirm asset identity',options,format_func=lambda c:f'{c["name"]} ({c["symbol"]}) · {c["id"]}')
                if st.button('Analyze coin',type='primary'):
                    with st.spinner('Loading real completed daily observations…'):
                        cid=c['id']; raw=fetch(cid); frozen=store.frozen(cid)
                        if not frozen.empty:
                            raw=pd.concat([frozen,raw]).assign(date=lambda x:pd.to_datetime(x.date,utc=True)).drop_duplicates('date',keep='first').sort_values('date')
                        h=analyze(raw); store.save(cid,h,raw); st.session_state['analysis']=(cid,h,raw)
                if 'analysis' in st.session_state: display_history(*st.session_state['analysis'])
        except Exception as e:
            st.error(f'Data unavailable: {e}'); st.info('No fabricated fallback. Retry later, configure an optional FREE CoinGecko Demo key, or import genuine daily CSV data.')
elif page=='Market Scanner':
    st.subheader('Latest scanner observations')
    if Path('data/seed_provenance.json').exists(): st.caption('Initial history imported from the verified Mac scan. Automated refresh status is shown below; import provenance is retained in data/seed_provenance.json.')
    st.caption('Run python scanner.py daily, or enable the supplied free GitHub Actions workflow. The dashboard reads the persisted snapshot; it does not start paid jobs.')
    with st.expander('Review and add a contract identity mapping'):
        st.caption('Match the exact exchange base and CoinGecko ID. Confirm the underlying asset, contract address and any multipliers/redenominations. Cloud edits are ephemeral; update mappings.json in GitHub for scheduled scans.')
        base=st.text_input('Exact exchange base, for example GTC')
        identity=st.text_input('Exact verified CoinGecko ID')
        reviewed=st.checkbox('I verified this contract refers to that underlying asset')
        if st.button('Save reviewed mapping',disabled=not (base and identity and reviewed)):
            try:
                from data import coin_list
                ids={c['id'] for c in coin_list()}
                if identity not in ids: st.error('CoinGecko ID does not exist in current supported list.')
                else:
                    mapping=json.loads(Path('mappings.json').read_text()); mapping[base]=identity
                    Path('mappings.json').write_text(json.dumps(mapping,indent=2)); st.success('Saved. Run a fresh scan to include this mapping.')
            except Exception as e: st.error(f'Mapping could not be saved: {e}')

    with st.expander('Run a bounded scan now'):
        exchange=st.selectbox('Exchange',['bybit','binanceusdm','okx'])
        limit=st.number_input('Maximum coins per run',min_value=1,max_value=25,value=5)
        if st.button('Run free public API scan'):
            try:
                from scanner import scan
                with st.spinner('Scanning verified mappings; exchange access and free quotas may limit coverage…'):
                    st.json(scan(exchange,int(limit),active_db))
            except Exception as e: st.error(f'Scan failed: {e}')
    f=store.latest()
    if f.empty: st.info('No scans recorded yet. See setup instructions and mappings.json.')
    else:
        states=st.multiselect('Lifecycle states',sorted(f.state.unique()))
        a,b,c=st.columns(3)
        lo=a.number_input('Min market cap',value=1_000_000,min_value=0); hi=b.number_input('Max market cap',value=20_000_000,min_value=0)
        score=c.slider('Experimental score · not V20',(0),(100),(0,100))
        minvol=st.number_input('Minimum daily reported volume USD',value=0,min_value=0)
        recent=st.checkbox('Only transitions in past 7 calendar days')
        filt=f[f.market_cap.between(lo,hi) & f.score.between(*score) & f.volume.ge(minvol)] if 'score' in f else f.iloc[0:0]
        if states: filt=filt[filt.state.isin(states)]
        if recent:
            allh=store.all_states(); cutoff=(pd.Timestamp.now(tz='UTC')-pd.Timedelta(days=7)).date().isoformat()
            ids=allh.loc[allh.transition.eq(True)&allh.date.ge(cutoff),'coin_id']; filt=filt[filt.coin_id.isin(ids)]
        table(filt); st.download_button('Export scanner CSV',filt.to_csv(index=False),'scanner.csv')
    st.subheader('Recovered research scanner coverage')
    recovered_latest=store.latest_research()
    if recovered_latest.empty: st.info('No recovered research records yet. The next scan records availability; reference-price histories alone cannot supply recovered scores.')
    else: table(recovered_latest)
    run=Path('data/last_run.json')
    if run.exists(): st.json(json.loads(run.read_text()))
elif page in ('State Transition Monitor','Historical State Charts'):
    f=store.all_states()
    if f.empty: st.info('Analyze a coin or run a scan to begin tracking.')
    elif page=='State Transition Monitor':
        table(f[f.transition.eq(True)].sort_values('date',ascending=False))
    else:
        cid=st.selectbox('Coin',sorted(f.coin_id.unique())); z=f[f.coin_id.eq(cid)]
        st.plotly_chart(px.scatter(z,x='date',y='state',color='state',title='Lifecycle history'),width='stretch')
        if 'score' in z: st.plotly_chart(px.line(z,x='date',y=['score','momentum7']),width='stretch')
elif page=='Data Quality Indicators':
    f=store.latest()
    if not f.empty: table(f[[c for c in ['coin_id','date','quality','state','rule_version'] if c in f]])
    uni=Path('data/universe_latest.csv')
    if uni.exists(): st.subheader('Contract identity & status'); table(pd.read_csv(uni))
    st.info('Historical market cap is never replaced by current market cap. Missing daily records invalidate the affected window. Contract universe snapshots start at installation; older delistings are not reconstructed. Missing contracts are flagged for verification, not assumed delisted.')
else:
    st.markdown(Path('RULES.md').read_text())
