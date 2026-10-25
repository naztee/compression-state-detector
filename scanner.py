import argparse
import json
import time
from pathlib import Path
import pandas as pd
from data import perpetuals,coin_list,resolve,markets,history,contract_identities,provider_perpetuals
from engine import analyze
from store import Store

def _scan(exchange='bybit',limit=25,db='data/scanner.sqlite',delay=12):
    store=Store(db); report={'exchange':exchange,'errors':[],'scanned':0,'coverage':'FORWARD_ONLY_UNIVERSE'}
    overrides=json.loads(Path('mappings.json').read_text())
    provider_warning=None
    try: identities=contract_identities(exchange)
    except Exception as e: identities={}; provider_warning=str(e)
    try:
        inventory=perpetuals(exchange); report['inventory_source']='CCXT_VENUE'
    except Exception as e:
        report['venue_inventory_warning']=str(e)
        inventory=provider_perpetuals(exchange)
        report['inventory_source']='COINGECKO_DERIVATIVES_VENUE_STATUS_UNCONFIRMED'
    contracts=resolve(inventory,coin_list(),overrides,identities)
    report['identity_source_warning']=provider_warning
    store.universe(contracts)
    contracts.to_csv('data/universe_latest.csv',index=False)
    eligible_status=contracts.active.eq(True)
    if 'inventory_source' in contracts: eligible_status=eligible_status | contracts.inventory_source.eq('COINGECKO_DERIVATIVES')
    eligible=contracts[contracts.coin_id.notna() & eligible_status].drop_duplicates('coin_id')
    ids=eligible.coin_id.tolist(); snapshots=[]
    for i in range(0,len(ids),100):
        snapshots.extend(markets(ids[i:i+100])); time.sleep(delay)
    last=store.latest(); seen=dict(zip(last.coin_id,last.date)) if not last.empty else {}
    snapshots=sorted(snapshots,key=lambda r:(not (1e6<=(r.get('market_cap') or 0)<=20e6),seen.get(r['id'],''),r.get('market_cap') or 1e30))
    report['batch_limit_note']='Bounded daily batch; prioritizes $1M–$20M, then least-recently scanned within each priority tier. Not complete daily coverage.'
    report.update(time=pd.Timestamp.now(tz='UTC').isoformat(),contracts=len(contracts),unverified=int(contracts.coin_id.isna().sum()),verified=len(ids),selected=min(limit,len(snapshots)))
    for c in snapshots[:limit]:
        try:
            raw=history(c['id']); frozen=store.frozen(c['id'])
            if not frozen.empty:
                raw=pd.concat([frozen,raw]).assign(date=lambda x:pd.to_datetime(x.date,utc=True)).drop_duplicates('date',keep='first').sort_values('date')
            h=analyze(raw); store.save(c['id'],h,raw); report['scanned']+=1
        except Exception as e: report['errors'].append({'coin_id':c['id'],'error':str(e)})
        time.sleep(delay)
    previous=store.conn.execute('SELECT symbol FROM universe WHERE exchange=? AND date < (SELECT MAX(date) FROM universe WHERE exchange=?)',(exchange,exchange)).fetchall()
    report['missing_previously_observed_contracts']=sorted({r[0] for r in previous}-set(contracts.symbol))
    report['missing_contract_note']='Missing is not proof of delisting; manually verify exchange notices.'
    store.log(report); Path('data/last_run.json').write_text(json.dumps(report,indent=2))
    return report
def scan(exchange='bybit',limit=25,db='data/scanner.sqlite',delay=12):
    if not 1 <= limit <= 100: raise ValueError('Limit must be 1–100')
    try: return _scan(exchange,limit,db,delay)
    except Exception as e:
        report={'exchange':exchange,'fatal_error':str(e),'scanned':0,'status':'FAILED','time':pd.Timestamp.now(tz='UTC').isoformat()}
        store=Store(db); store.log(report)
        Path('data').mkdir(exist_ok=True)
        Path('data/last_run.json').write_text(json.dumps(report,indent=2))
        return report

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--exchange',default='bybit'); p.add_argument('--limit',type=int,default=25); a=p.parse_args()
    report=scan(a.exchange,a.limit); print(json.dumps(report,indent=2))
    if report.get('fatal_error'): raise SystemExit(1)
