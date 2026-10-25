import numpy as np
import pandas as pd
import scanner
from store import Store

def test_scanner_persists_real_pipeline_with_controlled_fixture(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path); (tmp_path/'mappings.json').write_text('{"TEST":"test-asset"}')
    monkeypatch.setattr(scanner,'perpetuals',lambda e:[dict(exchange=e,base='TEST',symbol='TEST/USDT:USDT',active=True)])
    monkeypatch.setattr(scanner,'contract_identities',lambda e:{})
    monkeypatch.setattr(scanner,'coin_list',lambda:[dict(id='test-asset',symbol='test')])
    monkeypatch.setattr(scanner,'markets',lambda ids:[dict(id='test-asset',market_cap=5e6)])
    f=pd.DataFrame(dict(date=pd.date_range('2024-01-01',periods=100,tz='UTC'),price=np.ones(100),volume=np.full(100,5e5),market_cap=np.full(100,5e6)))
    monkeypatch.setattr(scanner,'history',lambda cid:f)
    report=scanner.scan(limit=1,delay=0)
    assert report['scanned']==1
    assert Store().latest().iloc[0].quality=='OK'
    assert (tmp_path/'data/universe_latest.csv').exists()

def test_failed_universe_run_logged(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path); (tmp_path/'mappings.json').write_text('{}')
    monkeypatch.setattr(scanner,'contract_identities',lambda e:{})
    def fail(e): raise RuntimeError('offline')
    monkeypatch.setattr(scanner,'perpetuals',fail)
    report=scanner.scan(delay=0)
    assert report['status']=='FAILED'
    assert (tmp_path/'data/last_run.json').exists()

def test_secondary_inventory_is_explicit_and_status_unconfirmed(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path); (tmp_path/'mappings.json').write_text('{}')
    monkeypatch.setattr(scanner,'contract_identities',lambda e:{'XUSDT':'x'})
    def fail(e): raise RuntimeError('venue API unavailable')
    monkeypatch.setattr(scanner,'perpetuals',fail)
    monkeypatch.setattr(scanner,'provider_perpetuals',lambda e:[dict(exchange=e,symbol='XUSDT',contract_id='XUSDT',base='X',active=None,inventory_source='COINGECKO_DERIVATIVES',contract_status='VENUE_STATUS_UNCONFIRMED')])
    monkeypatch.setattr(scanner,'coin_list',lambda:[dict(id='x',symbol='x')])
    monkeypatch.setattr(scanner,'markets',lambda ids:[])
    r=scanner.scan(delay=0)
    assert r['inventory_source']=='COINGECKO_DERIVATIVES_VENUE_STATUS_UNCONFIRMED'
    assert r['venue_inventory_warning']=='venue API unavailable'
    assert r['verified']==1
    assert pd.read_csv('data/universe_latest.csv').contract_status.iloc[0]=='VENUE_STATUS_UNCONFIRMED'
