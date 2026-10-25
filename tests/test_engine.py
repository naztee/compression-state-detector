import numpy as np
import pandas as pd
import pytest
from engine import analyze, outcomes, classify, baseline_report
from store import Store

def fixture(n=200):
    return pd.DataFrame(dict(date=pd.date_range('2024-01-01',periods=n,tz='UTC'),price=np.linspace(1,1.1,n),market_cap=np.full(n,5e6),volume=np.linspace(2e6,3e5,n)))

def test_causal_append_invariance():
    f=fixture(); a=analyze(f.iloc[:130]); b=analyze(f).iloc[:130]
    pd.testing.assert_frame_equal(a,b)

def test_exact_quarters():
    f=fixture(84); f['volume']=np.repeat([2e6,1e6,5e5,2.5e5],21)
    r=analyze(f).iloc[-1]
    assert [r[f'q{i}'] for i in range(1,5)]==[40,20,10,5]

def test_missing_historical_mc_never_current_substitution():
    f=fixture(84); f.loc[2,'market_cap']=np.nan
    r=analyze(f).iloc[-1]
    assert r.state=='UNKNOWN' and 'MISSING_HISTORICAL_MC' in r.quality

def test_gap_invalidates_window():
    f=fixture(100).drop(index=70); assert analyze(f).iloc[-1].state=='UNKNOWN'

def test_duplicate_rejected():
    with pytest.raises(ValueError): analyze(pd.concat([fixture(84),fixture(84).iloc[:1]]))

def test_warmup_and_v20_unverified():
    h=analyze(fixture()); assert (h.iloc[:83].state=='UNKNOWN').all()
    assert h.v20_candidate.isna().all(); assert h.score.dropna().between(0,100).all()

def test_forward_next_sample_and_censoring():
    f=fixture(100); f['price']=np.arange(1,101)
    sig=pd.DataFrame([dict(date='2024-03-24',state='S2')])
    o=outcomes(f,sig,(7,30)); assert o.iloc[0].complete and not o.iloc[1].complete
    assert o.iloc[0].forward_return==pytest.approx((92/85-1)*100)
    assert o.iloc[0].mae==0

def test_conflict_precedence_and_no_fixed_sequence():
    m=dict(r7=-25,vol_ratio=2,price=1,prior_high30=2,r21=40,off_high21=-15,score=90,range30=15,q4_return=0,q4=10)
    assert classify(m)=='S0'
    m.update(r7=20,price=3); assert classify(m)=='S4'
    m.update(r7=0,price=1); assert classify(m)=='S5'

def test_frozen_store(tmp_path):
    f=fixture(100); h=analyze(f); s=Store(str(tmp_path/'test.sqlite')); s.save('x',h,f)
    f['market_cap']=9e6; s.save('x',analyze(f),f)
    assert s.frozen('x').market_cap.iloc[0]==5e6
    assert len(s.latest())==1

def test_historical_mc_controls_baseline():
    f=fixture(200); f.loc[:120,'market_cap']=1e8
    h=analyze(f); report=baseline_report(f,h)
    assert report.set_index('cohort').loc['MC $1M–$20M','n']<=2

def test_stability_tiny_perturbation_flat_market():
    f=fixture(120); h=analyze(f); f.price*=1.00001
    assert analyze(f).state.tolist()==h.state.tolist()
