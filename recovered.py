"""Recovered scoring methods from main_v21_combined_project_test.py, 12 Sep 2026.
Source Library ID libfile_2c7e3c8b6a3881918446409221aebe25.
Pure Python port; no QuantConnect dependency. Not a validated S0–S5 model.
"""
import pandas as pd
import numpy as np
VERSION = 'recovered-v21-score-1.0'

class RecoveredScore:
    def score_turnover(self, q1, q2, q3, q4):
            score = 0
            if q1 > q2:
                score += 20
            if q2 > q3:
                score += 20
            if q3 > q4:
                score += 20
            if q4 < 0.1:
                score += 25
            elif q4 < 0.15:
                score += 18
            elif q4 < 0.2:
                score += 10
            if q1 > 0:
                contraction = 1.0 - q4 / q1
                if contraction >= 0.8:
                    score += 15
                elif contraction >= 0.6:
                    score += 10
                elif contraction >= 0.4:
                    score += 5
            return min(score, 100)
    
    def score_downside(self, q1, q2, q3, q4):
            score = 0
            if q2 > q1:
                score += 20
            if q3 > q2:
                score += 20
            if q4 > q3:
                score += 20
            if q4 >= -0.03:
                score += 25
            elif q4 >= -0.05:
                score += 20
            elif q4 >= -0.08:
                score += 12
            elif q4 >= -0.12:
                score += 5
            worst_previous = min(q1, q2, q3)
            improvement = q4 - worst_previous
            if improvement >= 0.3:
                score += 15
            elif improvement >= 0.2:
                score += 10
            elif improvement >= 0.1:
                score += 5
            return min(score, 100)
    
    def score_range(self, q1, q2, q3, q4):
            score = 0
            if q2 < q1:
                score += 20
            if q3 < q2:
                score += 20
            if q4 < q3:
                score += 20
            if q1 > 0:
                contraction = 1.0 - q4 / q1
                if contraction >= 0.6:
                    score += 40
                elif contraction >= 0.4:
                    score += 30
                elif contraction >= 0.25:
                    score += 20
                elif contraction >= 0.1:
                    score += 10
            return min(score, 100)
    
    def score_new_lows(self, q1, q2, q3, q4):
            score = 0
            if q2 <= q1:
                score += 15
            if q3 <= q2:
                score += 15
            if q4 <= q3:
                score += 20
            if q4 == 0:
                score += 50
            elif q4 <= 1:
                score += 40
            elif q4 <= 2:
                score += 25
            elif q4 <= 4:
                score += 10
            return min(score, 100)
    
    def abandonment_penalty(self, q4_turnover, q4_return):
            penalty = 0
            if q4_turnover < 0.1 and q4_return <= -0.15:
                penalty += 30
            elif q4_turnover < 0.1 and q4_return <= -0.1:
                penalty += 20
            elif q4_turnover < 0.15 and q4_return <= -0.12:
                penalty += 15
            if q4_turnover < 0.03 and q4_return < -0.05:
                penalty += 10
            return min(penalty, 40)
    
    def classify_state(self, score):
            if score < 40:
                return 'REPRICING'
            if score < 60:
                return 'COOLING'
            if score < 75:
                return 'EARLY'
            if score < 90:
                return 'MATURE'
            return 'EXTREME'

def analyze_recovered(frame):
    """Strict calendar alignment; 30 prior bars + 84 trajectory bars.

    Historical MC/volume and OHLC must refer to the same completed UTC day.
    No sampled-price substitution. Frozen five-gate eligibility excludes the
    extra Q4-return gate found in the V21 execution path, as the V20 guide directs.
    """
    if frame.empty: return pd.DataFrame()
    f=frame.copy()
    f['date']=pd.to_datetime(f.date,utc=True).dt.normalize()
    if f.date.duplicated().any(): raise ValueError('Duplicate daily dates')
    f=f.sort_values('date').set_index('date')
    f=f.reindex(pd.date_range(f.index.min(),f.index.max(),freq='D'))
    required=['open','high','low','close','market_cap','volume']
    for c in required:
        if c not in f: f[c]=np.nan
        f[c]=pd.to_numeric(f[c],errors='coerce')
    scorer=RecoveredScore(); records=[]
    for i in range(len(f)):
        w=f.iloc[max(0,i-113):i+1]
        row=dict(date=f.index[i].date().isoformat(),research_version=VERSION,research_quality='OK',research_score=None,research_category='UNAVAILABLE',research_v20=None)
        issues=[]
        if len(w)<114: issues.append('INCOMPLETE_114D_HISTORY')
        for c in required:
            invalid=w[c].isna() | ~np.isfinite(w[c]) | (w[c]<0 if c=='volume' else w[c]<=0)
            if invalid.any(): issues.append('MISSING_OR_INVALID_'+c.upper())
        bad=(w.high<w[['open','close','low']].max(axis=1)) | (w.low>w[['open','close','high']].min(axis=1))
        if bad.any(): issues.append('INVALID_OHLC_ORDER')
        if f.index[i]>=pd.Timestamp.now(tz='UTC').normalize(): issues.append('INCOMPLETE_UTC_DAY')
        if issues:
            row['research_quality']='; '.join(issues); records.append(row); continue
        tr=w.iloc[30:]; qs=[]
        for q in range(4):
            seg=tr.iloc[q*21:(q+1)*21]
            nl=sum(w.low.iloc[j]<w.low.iloc[j-30:j].min() for j in range(30+q*21,30+(q+1)*21))
            qs.append(dict(turnover=float((seg.volume/seg.market_cap).median()),ret=float(seg.close.iloc[-1]/seg.close.iloc[0]-1),
                           range=float((seg.high.max()-seg.low.min())/seg.close.median()),new_lows=int(nl)))
        t=scorer.score_turnover(*(q['turnover'] for q in qs)); d=scorer.score_downside(*(q['ret'] for q in qs))
        r=scorer.score_range(*(q['range'] for q in qs)); l=scorer.score_new_lows(*(q['new_lows'] for q in qs))
        penalty=scorer.abandonment_penalty(qs[-1]['turnover'],qs[-1]['ret'])
        score=max(0,min(100,.3*t+.3*d+.2*r+.2*l-penalty))
        mc=float(tr.market_cap.iloc[-7:].median()); location=float(tr.close.iloc[-1]/tr.low.min()-1)
        r3=float(tr.close.iloc[-1]/tr.close.iloc[-4]-1)
        gates=dict(market_cap=1e6<=mc<=20e6,score=30<=score<60,q4=0.05<=qs[-1]['turnover']<.20,location=.12<=location<.18,r3=r3>0)
        row.update(research_score=score,research_category=scorer.classify_state(score),research_v20=bool(all(gates.values())),
                   research_mc7=mc,research_location=location*100,research_r3=r3*100,
                   turnover_score=t,downside_score=d,range_score=r,new_low_score=l,abandonment_penalty=penalty,
                   research_q4_return=qs[-1]['ret']*100,research_v21_extra_return_gate=qs[-1]['ret']>=-.12,
                   research_failed_gates=', '.join(k for k,v in gates.items() if not v))
        for n,q in enumerate(qs,1):
            row.update({f'research_q{n}_vm':q['turnover']*100,f'research_q{n}_return':q['ret']*100,
                        f'research_q{n}_range':q['range']*100,f'research_q{n}_new_lows':q['new_lows']})
        records.append(row)
    return pd.DataFrame(records)
