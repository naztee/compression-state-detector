"""Causal, versioned research rules. All percentages are expressed as percent."""
import numpy as np
import pandas as pd
VERSION = 'provisional-1.0'
STATES = {'S0':'Capitulation','S1':'Stabilization','S2':'Early Compression','S3':'Mature Compression','S4':'Expansion','S5':'Distribution'}

def prepare(frame):
    f = frame.copy()
    f['date'] = pd.to_datetime(f['date'], utc=True).dt.normalize()
    if f.date.duplicated().any():
        raise ValueError('Duplicate daily dates; resolve source records explicitly.')
    f = f.sort_values('date').set_index('date')
    if f.empty: return f
    f = f.reindex(pd.date_range(f.index.min(), f.index.max(), freq='D'))
    f.index.name = 'date'
    for c in ['price','market_cap','volume']:
        if c not in f: f[c] = np.nan
        f[c] = pd.to_numeric(f[c], errors='coerce').where(lambda s:s>0)
    return f

def state_checks(m):
    """Single source of truth for classification and visible explanations."""
    specs = [
        ('S0','r7','<=',-20), ('S0','vol_ratio','>=',1.5),
        ('S4','r7','>=',15), ('S4','price','>',m.get('prior_high30')),
        ('S4','vol_ratio','>=',1.3),
        ('S5','r21','>=',30), ('S5','off_high21','<=',-10), ('S5','vol_ratio','>=',1.3),
        ('S3','score','>=',75), ('S3','range30','<=',25), ('S3','q4_return','>=',-12),
        ('S2','score','>=',30), ('S2','q4','>=',5), ('S2','q4','<=',20),
        ('S2','range30','<=',35), ('S2','q4_return','>=',-12),
        ('S1','range30','<=',50), ('S1','r7','>',-20)]
    ops = {'<=':lambda a,b:a<=b, '>=':lambda a,b:a>=b, '>':lambda a,b:a>b}
    rows=[]
    for state,metric,op,threshold in specs:
        value=m.get(metric)
        available = value is not None and threshold is not None and pd.notna(value) and pd.notna(threshold)
        rows.append(dict(state=state,metric=metric,value=value,requirement=f'{op} {threshold}' if threshold is not None else 'Unavailable',
                         result=('PASS' if ops[op](value,threshold) else 'FAIL') if available else 'MISSING'))
    return rows

def classify(m):
    """Independent predicates, resolved by explicit S0,S4,S5,S3,S2,S1 precedence."""
    checks=state_checks(m)
    for state in ('S0','S4','S5','S3','S2','S1'):
        if all(c['result']=='PASS' for c in checks if c['state']==state): return state
    return 'UNCLASSIFIED'

def analyze(frame, asof=None):
    f = prepare(frame)
    if asof is not None: f = f.loc[:pd.Timestamp(asof, tz='UTC')]
    records=[]
    for i in range(len(f)):
        w=f.iloc[max(0,i-83):i+1]; row={'date':f.index[i].date().isoformat(),'rule_version':VERSION}
        issues=[]
        if len(w)!=84: issues.append('INCOMPLETE_84D_HISTORY')
        if w.price.isna().any(): issues.append('MISSING_PRICE')
        if w.market_cap.isna().any(): issues.append('MISSING_HISTORICAL_MC')
        if w.volume.isna().any(): issues.append('MISSING_VOLUME')
        row.update(price=f.price.iloc[i],market_cap=f.market_cap.iloc[i],volume=f.volume.iloc[i])
        if issues:
            row.update(state='UNKNOWN',quality='; '.join(issues),v20_candidate=None)
            records.append(row); continue
        p=w.price; v=w.volume; vm=v/w.market_cap*100
        qs=[float(vm.iloc[j:j+21].mean()) for j in range(0,84,21)]
        range30=(p.iloc[-30:].max()/p.iloc[-30:].min()-1)*100
        loc=(p.iloc[-1]/p.min()-1)*100
        # Explicitly provisional score: contraction, low turnover, narrow price range.
        contraction=np.clip(1-qs[3]/qs[0],0,1)
        low_turnover=np.clip(1-qs[3]/40,0,1)
        narrow=np.clip(1-range30/60,0,1)
        score=round(float(40*contraction+30*low_turnover+30*narrow),2)
        m=dict(price=p.iloc[-1],score=score,range30=float(range30),location84=float(loc),
               r3=float((p.iloc[-1]/p.iloc[-4]-1)*100),r7=float((p.iloc[-1]/p.iloc[-8]-1)*100),
               r21=float((p.iloc[-1]/p.iloc[-22]-1)*100),q4_return=float((p.iloc[-1]/p.iloc[-22]-1)*100),
               off_high21=float((p.iloc[-1]/p.iloc[-21:].max()-1)*100),
               drawdown84=float((p.iloc[-1]/p.max()-1)*100),
               prior_high30=float(p.iloc[-31:-1].max()),
               vol_ratio=float(v.iloc[-7:].mean()/v.iloc[-28:-7].mean()),q4=qs[3])
        row.update(m)
        row.update({f'q{j+1}':qs[j] for j in range(4)})
        row.update(state=classify(m),quality='OK',bias='UP' if m['r7']>5 else 'DOWN' if m['r7'] < -5 else 'NEUTRAL',
                   v20_candidate=None,
                   v20_provisional_proxy=bool(1e6<=row['market_cap']<=20e6 and 30<=score<60 and 5<=qs[3]<=20 and 12<=loc<=18 and m['r3']>0))
        records.append(row)
    out=pd.DataFrame(records)
    if out.empty: return out
    # Unknown days break runs; no invented duration through missing observations.
    run=0; previous=None; last=None; start=None; transitions=[]; durations=[]; prevs=[]; momenta=[]
    for i,r in out.iterrows():
        valid=r.state not in ('UNKNOWN','UNCLASSIFIED')
        if valid:
            if last!=r.state:
                previous=last if last not in (None,'UNKNOWN','UNCLASSIFIED') else None
                start=r.date; run=1
                if previous is not None: transitions.append(i)
            else: run+=1
        else: run=0; start=None; previous=None
        durations.append(run); prevs.append(previous)
        momenta.append(float(r.get('score',np.nan)-out.iloc[i-7].get('score',np.nan)) if i>=7 else np.nan)
        last=r.state
    out['duration_days']=durations; out['previous_state']=prevs; out['momentum7']=momenta
    out['transition']=out.index.isin(transitions)
    out['transitions30']=out['transition'].rolling(30,min_periods=1).sum().astype(int)
    return out

def outcomes(frame, signals, horizons=(7,30,60)):
    """Entry at first NEXT daily price; excursions are daily sample bounds, not intraday."""
    f=prepare(frame); results=[]
    for _,s in signals.iterrows():
        t=pd.Timestamp(s.date,tz='UTC'); entry_day=t+pd.Timedelta(days=1)
        for h in horizons:
            path=f.reindex(pd.date_range(entry_day,periods=h+1,freq='D')).price
            complete=bool(path.notna().all())
            r=dict(signal_date=s.date,state=s.state,horizon=h,complete=complete,entry_date=entry_day.date().isoformat())
            r.update(forward_return=float((path.iloc[-1]/path.iloc[0]-1)*100) if complete else None,
                     mae=float((path.min()/path.iloc[0]-1)*100) if complete else None,
                     mfe=float((path.max()/path.iloc[0]-1)*100) if complete else None)
            results.append(r)
    return pd.DataFrame(results)

def baseline_report(frame, history):
    valid=history[history.quality.eq('OK')].copy()
    if valid.empty: return pd.DataFrame()
    # Non-overlap within each cohort limits repeated daily signal inflation.
    cohorts={'Compression S2/S3':valid.state.isin(['S2','S3']),
             'MC $1M–$20M':valid.market_cap.between(1e6,20e6),
             'Drawdown ≥80%':valid.drawdown84.le(-80)}
    rows=[]
    for name,mask in cohorts.items():
        picks=[]; last=None
        for _,r in valid[mask].iterrows():
            day=pd.Timestamp(r.date)
            if last is None or (day-last).days>=31: picks.append(r); last=day
        if not picks: rows.append(dict(cohort=name,n=0)); continue
        o=outcomes(frame,pd.DataFrame(picks),horizons=(30,)); o=o[o.complete]
        rows.append(dict(cohort=name,n=len(o),median_return=o.forward_return.median(),median_mae=o.mae.median(),median_mfe=o.mfe.median()))
    return pd.DataFrame(rows)
