from streamlit.testing.v1 import AppTest

def test_dashboard_api_failure_renders(monkeypatch,tmp_path):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'test.sqlite'))
    import data
    def fail(q): raise data.DataError('simulated offline')
    monkeypatch.setattr(data,'search',fail)
    at=AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
    assert not at.exception
    assert any('Data unavailable' in e.value for e in at.error)
    for page in ['Market Scanner','State Transition Monitor','Historical State Charts','Data Quality Indicators','Rules & Validation']:
        at.sidebar.radio[0].set_value(page).run(timeout=30)
        assert not at.exception

def test_recovered_panel_with_genuine_schema_fixture(monkeypatch,tmp_path):
    # Synthetic OHLC fixture exercises rendering only, never market evidence.
    import pandas as pd
    import numpy as np
    import data
    from engine import analyze
    monkeypatch.setenv('DB_PATH',str(tmp_path/'render.sqlite'))
    monkeypatch.setattr(data,'search',lambda q:[dict(id='fixture',name='Fixture',symbol='TEST')])
    c=np.linspace(1,1.1,114)
    raw=pd.DataFrame(dict(date=pd.date_range('2024-01-01',periods=114,tz='UTC'),price=c,open=c,close=c,high=c*1.02,low=c*.98,market_cap=5e6,volume=5e5))
    at=AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1]/'app.py'))
    at.session_state['analysis']=('fixture',analyze(raw),raw)
    at.run(timeout=30)
    assert not at.exception
    assert any(m.label=='Recovered score' for m in at.metric)
