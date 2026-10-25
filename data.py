"""Free public endpoints only. Cached requests; finite retries; no synthetic fallback."""
import json
import os
import time
from pathlib import Path
import requests
import pandas as pd
import ccxt
CACHE=Path(os.getenv('CACHE_DIR','cache')); CACHE.mkdir(exist_ok=True)
class DataError(RuntimeError): pass

def get(path,params=None,ttl=3600):
    import hashlib
    key=hashlib.sha256(json.dumps([path,params],sort_keys=True).encode()).hexdigest()
    file=CACHE/(key+'.json')
    if file.exists() and time.time()-file.stat().st_mtime<ttl:
        return json.loads(file.read_text())
    headers={'Accept':'application/json'}
    if os.getenv('COINGECKO_DEMO_API_KEY'): headers['x-cg-demo-api-key']=os.environ['COINGECKO_DEMO_API_KEY']
    for attempt in range(3):
        try:
            response=requests.get('https://api.coingecko.com/api/v3/'+path,params=params,headers=headers,timeout=25)
            if response.status_code in (429,500,502,503,504) and attempt<2:
                time.sleep(min(15,3*(attempt+1))); continue
            response.raise_for_status(); result=response.json()
            file.write_text(json.dumps(result)); return result
        except requests.RequestException as e:
            status=getattr(getattr(e,'response',None),'status_code',None)
            raise DataError(f'CoinGecko request failed ({type(e).__name__}, HTTP {status or "unavailable"}). No replacement data used.') from e
    raise DataError('API retries exhausted')

def search(query): return get('search',{'query':query},ttl=86400).get('coins',[])
def coin_list(): return get('coins/list',ttl=86400)
def markets(ids):
    return get('coins/markets',{'vs_currency':'usd','ids':','.join(ids),'per_page':250,'page':1},ttl=3600)

def history(coin_id,days=365):
    raw=get(f'coins/{coin_id}/market_chart',{'vs_currency':'usd','days':days,'interval':'daily'},ttl=21600)
    series=[]
    for name,key in [('price','prices'),('market_cap','market_caps'),('volume','total_volumes')]:
        vals=raw.get(key,[])
        if not vals: series.append(pd.Series(dtype=float,name=name)); continue
        z=pd.DataFrame(vals,columns=['ts',name]); z['date']=pd.to_datetime(z.ts,unit='ms',utc=True)
        # Retain only exact 00:00 UTC historical samples. Drop partial/live last point.
        z=z[z.date.eq(z.date.dt.normalize()) & z.date.lt(pd.Timestamp.now(tz='UTC').normalize())]
        if z.date.duplicated().any(): raise DataError('Duplicate historical timestamps')
        series.append(z.set_index('date')[name])
    f=pd.concat(series,axis=1).sort_index(); f.index.name='date'
    if f.empty: raise DataError('No completed daily history available')
    return f.reset_index()

def perpetuals(exchange='bybit'):
    if exchange not in ('bybit','binanceusdm','okx'): raise DataError('Unsupported exchange')
    try:
        client=getattr(ccxt,exchange)({'enableRateLimit':True,'timeout':25000})
        ms=client.load_markets()
        return [dict(exchange=exchange,symbol=m['symbol'],contract_id=m['id'],base=m['base'],active=m.get('active'),
                     contract_status='ACTIVE' if m.get('active') is True else 'INACTIVE' if m.get('active') is False else 'STATUS_UNKNOWN')
                for m in ms.values() if m.get('swap') and m.get('linear') and m.get('settle')=='USDT']
    except Exception as e: raise DataError(f'{exchange} markets unavailable: {type(e).__name__}') from e

def contract_identities(exchange):
    # CoinGecko explicitly links venue contract IDs to underlying IDs.
    # Other venues still support reviewed mappings; no guessed venue IDs.
    if exchange != 'bybit': return {}
    raw=get('derivatives/exchanges/bybit',{'include_tickers':'all'},ttl=86400)
    matches={}
    for t in raw.get('tickers',[]):
        if t.get('contract_type')=='perpetual' and t.get('target')=='USDT' and t.get('coin_id') and not t.get('expired_at'):
            matches.setdefault(t['symbol'],set()).add(t['coin_id'])
    return {symbol:next(iter(ids)) for symbol,ids in matches.items() if len(ids)==1}

def provider_perpetuals(exchange):
    """Explicit secondary inventory; venue trading status remains unconfirmed."""
    if exchange != 'bybit': raise DataError('No secondary inventory configured for this venue')
    raw=get('derivatives/exchanges/bybit',{'include_tickers':'all'},ttl=86400)
    rows=[]
    for t in raw.get('tickers',[]):
        if t.get('contract_type')=='perpetual' and t.get('target')=='USDT' and t.get('coin_id') and not t.get('expired_at'):
            rows.append(dict(exchange=exchange,symbol=t['symbol'],contract_id=t['symbol'],base=t['base'],
                             active=None,contract_status='VENUE_STATUS_UNCONFIRMED',inventory_source='COINGECKO_DERIVATIVES',
                             provider_last_traded=t.get('last_traded')))
    if not rows: raise DataError('Secondary inventory returned no supported contracts')
    return rows

def resolve(contracts,coins,overrides=None,identities=None):
    overrides=overrides or {}; identities=identities or {}; bysymbol={}; ids={c['id'] for c in coins}
    for c in coins: bysymbol.setdefault(c['symbol'].upper(),[]).append(c['id'])
    rows=[]
    for m in contracts:
        r=dict(m); override=overrides.get(m['base']); candidates=bysymbol.get(m['base'].upper(),[])
        # Symbol uniqueness is insufficient identity proof. Explicit user-reviewed mapping required.
        linked=identities.get(m.get('contract_id'))
        resolved=override if override in ids else linked if linked in ids else None
        r.update(coin_id=resolved,
                 identity_status='VERIFIED_OVERRIDE' if override in ids else 'PROVIDER_CONTRACT_ID' if linked in ids else 'UNVERIFIED_IDENTITY',
                 suggested_ids=';'.join(candidates))
        rows.append(r)
    return pd.DataFrame(rows)
