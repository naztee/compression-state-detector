import json
import sqlite3
from pathlib import Path
import os
import hashlib
import tempfile
import pandas as pd
def runtime_db_path(source='data/scanner.sqlite', cloud=None):
    """Keep cloud writes away from the Git-tracked daily snapshot."""
    if os.getenv('DB_PATH'): return os.environ['DB_PATH']
    if cloud is None: cloud='/mount/src/' in str(Path(__file__).resolve())
    if not cloud: return source
    src=Path(source); raw=src.read_bytes() if src.exists() else b''
    digest=hashlib.sha256(raw).hexdigest()
    folder=Path(tempfile.gettempdir())/'compression-observatory-runtime'; folder.mkdir(exist_ok=True)
    target=folder/(digest+'.sqlite')
    if raw and not target.exists():
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as temp:
            temp.write(raw); name=temp.name
        os.replace(name,target)
    return str(target)

class Store:
    def __init__(self,path='data/scanner.sqlite'):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(path,timeout=30)
        self.conn.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS states(coin_id TEXT,date TEXT,version TEXT,state TEXT,payload TEXT,PRIMARY KEY(coin_id,date,version));
        CREATE TABLE IF NOT EXISTS observations(coin_id TEXT,date TEXT,payload TEXT,observed_at TEXT,PRIMARY KEY(coin_id,date));
        CREATE TABLE IF NOT EXISTS universe(date TEXT,exchange TEXT,symbol TEXT,payload TEXT,PRIMARY KEY(date,exchange,symbol));
        CREATE TABLE IF NOT EXISTS research_states(coin_id TEXT,date TEXT,version TEXT,payload TEXT,PRIMARY KEY(coin_id,date,version));
        CREATE TABLE IF NOT EXISTS runs(time TEXT PRIMARY KEY,payload TEXT);
        ''')
    def save(self,coin_id,history,raw):
        now=pd.Timestamp.now(tz='UTC').isoformat()
        with self.conn:
            for r in raw.to_dict('records'):
                date=pd.Timestamp(r['date']).date().isoformat(); r['date']=date
                # Freeze first observation to avoid silently rewriting historical revisions.
                self.conn.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?)',(coin_id,date,json.dumps(r,default=str),now))
            for r in history.to_dict('records'):
                self.conn.execute('INSERT OR IGNORE INTO states VALUES(?,?,?,?,?)',(coin_id,r['date'],r['rule_version'],r['state'],json.dumps(r,default=str)))
    def frozen(self,coin_id):
        rows=self.conn.execute('SELECT payload FROM observations WHERE coin_id=? ORDER BY date',(coin_id,)).fetchall()
        return pd.DataFrame([json.loads(r[0]) for r in rows])
    def universe(self,frame):
        date=pd.Timestamp.now(tz='UTC').date().isoformat()
        with self.conn:
            for r in frame.to_dict('records'):
                self.conn.execute('INSERT OR REPLACE INTO universe VALUES(?,?,?,?)',(date,r['exchange'],r['symbol'],json.dumps(r)))
    def log(self,payload):
        with self.conn: self.conn.execute('INSERT INTO runs VALUES(?,?)',(pd.Timestamp.now(tz='UTC').isoformat(),json.dumps(payload)))
    def latest(self):
        rows=self.conn.execute('''SELECT coin_id,payload FROM states s WHERE date=(SELECT MAX(date) FROM states b WHERE b.coin_id=s.coin_id AND b.version=s.version)''').fetchall()
        return pd.DataFrame([dict(coin_id=c,**json.loads(p)) for c,p in rows])
    def all_states(self):
        rows=self.conn.execute('SELECT coin_id,payload FROM states ORDER BY date').fetchall()
        return pd.DataFrame([dict(coin_id=c,**json.loads(p)) for c,p in rows])
    def latest_research(self):
        rows=self.conn.execute('SELECT coin_id,payload FROM research_states s WHERE date=(SELECT MAX(date) FROM research_states b WHERE b.coin_id=s.coin_id AND b.version=s.version)').fetchall()
        return pd.DataFrame([dict(coin_id=c,**json.loads(p)) for c,p in rows])
