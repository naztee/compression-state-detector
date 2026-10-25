import numpy as np
import pandas as pd
import pytest
from recovered import RecoveredScore, analyze_recovered

def fixture(n=160):
    c=np.linspace(1,1.15,n)
    return pd.DataFrame(dict(date=pd.date_range('2024-01-01',periods=n,tz='UTC'),open=c,high=c*1.02,low=c*.98,close=c,market_cap=5e6,volume=5e5))

def test_manual_component_values_and_penalty():
    s=RecoveredScore()
    assert s.score_turnover(1,.6,.3,.08)==100
    assert s.score_downside(-.4,-.2,-.1,0)==100
    assert s.score_range(1,.7,.5,.3)==100
    assert s.score_new_lows(10,5,1,0)==100
    assert s.abandonment_penalty(.02,-.2)==40
    assert s.abandonment_penalty(.1,-.12)==15
    assert s.classify_state(59.99)=='COOLING'
    assert s.classify_state(60)=='EARLY'

def test_missing_ohlc_is_not_sampled_price():
    f=fixture().drop(columns=['open','high','low','close']); f['price']=1
    r=analyze_recovered(f).iloc[-1]
    assert r.research_score is None and 'CLOSE' in r.research_quality
    assert r.research_v20 is None

def test_medians_and_114_day_warmup():
    f=fixture(114); f.loc[113,'market_cap']=1e9; f.loc[113,'volume']=1e9
    h=analyze_recovered(f); r=h.iloc[-1]
    assert h.iloc[:113].research_quality.ne('OK').all()
    assert r.research_quality=='OK'
    assert r.research_mc7==5e6
    assert r.research_q4_vm==10
    assert r.research_location==pytest.approx((f.close.iloc[-1]/f.low.iloc[-84:].min()-1)*100)

def test_causality_and_missing_calendar():
    f=fixture(); a=analyze_recovered(f.iloc[:130]); b=analyze_recovered(f).iloc[:130]
    pd.testing.assert_frame_equal(a,b)
    assert analyze_recovered(f.drop(index=110)).iloc[-1].research_quality!='OK'

def test_q2_q3_affect_recovered_score():
    s=RecoveredScore()
    assert s.score_turnover(1,.6,.3,.1)>s.score_turnover(1,.02,.8,.1)

def test_invalid_ohlc_and_zero_volume():
    f=fixture(); f.loc[140,'high']=.1
    assert 'INVALID_OHLC_ORDER' in analyze_recovered(f).iloc[-1].research_quality
    f=fixture(); f.volume=0
    assert analyze_recovered(f).iloc[-1].research_quality=='OK'

