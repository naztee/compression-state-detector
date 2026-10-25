import requests
import pytest
import data

def test_api_failure_has_no_fake_fallback(monkeypatch,tmp_path):
    monkeypatch.setattr(data,'CACHE',tmp_path)
    def fail(*a,**kw): raise requests.ConnectionError('offline')
    monkeypatch.setattr(data.requests,'get',fail)
    with pytest.raises(data.DataError): data.get('test')

def test_http_failure(monkeypatch,tmp_path):
    monkeypatch.setattr(data,'CACHE',tmp_path)
    class Response:
        status_code=403
        def raise_for_status(self): raise requests.HTTPError('forbidden')
    monkeypatch.setattr(data.requests,'get',lambda *a,**kw:Response())
    with pytest.raises(data.DataError): data.get('forbidden')

def test_symbol_ambiguity_and_missing_override():
    contracts=[dict(base='ABC',symbol='ABC/USDT:USDT',exchange='bybit',active=True)]
    coins=[dict(symbol='abc',id='one'),dict(symbol='abc',id='two')]
    assert data.resolve(contracts,coins).coin_id.isna().all()
    assert data.resolve(contracts,coins,{'ABC':'one'}).coin_id.iloc[0]=='one'

def test_partial_day_exclusion(monkeypatch):
    import pandas as pd
    t=int(pd.Timestamp('2024-01-01',tz='UTC').timestamp()*1000)
    raw={k:[[t,10],[t+3600000,20]] for k in ['prices','market_caps','total_volumes']}
    monkeypatch.setattr(data,'get',lambda *a,**kw:raw)
    assert len(data.history('test'))==1

def test_429_bounded_retry(monkeypatch,tmp_path):
    monkeypatch.setattr(data,'CACHE',tmp_path); calls=[]
    class Response:
        status_code=429
        def raise_for_status(self): raise requests.HTTPError('rate limit')
    monkeypatch.setattr(data.requests,'get',lambda *a,**kw:(calls.append(1) or Response()))
    monkeypatch.setattr(data.time,'sleep',lambda x:None)
    with pytest.raises(data.DataError): data.get('rate-limit')
    assert len(calls)==3

def test_provider_mapping_uses_exact_contract_id():
    contracts=[dict(base='ABC',contract_id='1000ABCUSDT',symbol='1000ABC/USDT:USDT',exchange='bybit',active=True)]
    coins=[dict(symbol='abc',id='one'),dict(symbol='abc',id='two')]
    r=data.resolve(contracts,coins,identities={'1000ABCUSDT':'two'})
    assert r.coin_id.iloc[0]=='two' and r.identity_status.iloc[0]=='PROVIDER_CONTRACT_ID'
    assert data.resolve(contracts,coins,identities={'ABCUSDT':'two'}).coin_id.isna().all()
