from __future__ import annotations

import html
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "lantern.db"
VERSION = "0.5.0"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_db() -> Iterator[sqlite3.Connection]:
    db = connect()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,workstream TEXT NOT NULL DEFAULT 'Operations',priority TEXT NOT NULL DEFAULT 'P1',revenue_impact TEXT NOT NULL DEFAULT 'Medium',due_date TEXT,completed INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY AUTOINCREMENT,account TEXT NOT NULL,stage TEXT NOT NULL,value REAL NOT NULL,probability REAL NOT NULL,next_action TEXT NOT NULL DEFAULT '',next_date TEXT);
            CREATE TABLE IF NOT EXISTS research (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,progress INTEGER NOT NULL DEFAULT 0,commercial_output TEXT NOT NULL,next_action TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS milestones (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,target_date TEXT NOT NULL,progress INTEGER NOT NULL DEFAULT 0,owner TEXT NOT NULL DEFAULT 'Founder');
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS kpis (key TEXT PRIMARY KEY,label TEXT NOT NULL,target REAL NOT NULL DEFAULT 0,actual REAL NOT NULL DEFAULT 0,unit TEXT NOT NULL DEFAULT 'count');
            """
        )
        db.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('version',?)", (VERSION,))
        defaults={"organization_name":"Lantern Protocol","north_star_arr":"9500000","north_star_date":"2028-02-01","daily_focus":"Build the category. Ship the platform. Close the revenue.","github_org":"ShannonBrayNC"}
        for key,value in defaults.items(): db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(key,value))
        if db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]==0:
            db.executemany("INSERT INTO tasks(title,workstream,priority,revenue_impact,due_date) VALUES(?,?,?,?,?)",[("Publish ETS category thesis","Marketing","P0","High","2026-08-03"),("Complete evidence-object API slice","Engineering","P0","High","2026-08-05"),("Contact ten design-partner prospects","Sales","P0","High","2026-08-04"),("Advance Evidence Graph working paper","Research","P1","Medium","2026-08-07")])
        if db.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]==0:
            db.executemany("INSERT INTO opportunities(account,stage,value,probability,next_action,next_date) VALUES(?,?,?,?,?,?)",[("Healthcare design partner","Discovery",75000,.25,"Schedule architecture workshop","2026-08-05"),("State-government pilot","Prospecting",150000,.10,"Identify executive sponsor","2026-08-06"),("Enterprise evidence assessment","Proposal",50000,.50,"Send scoped proposal","2026-08-03")])
        if db.execute("SELECT COUNT(*) FROM research").fetchone()[0]==0:
            db.executemany("INSERT INTO research(title,progress,commercial_output,next_action) VALUES(?,?,?,?)",[("Evidence Object Model",70,"Specification, sales brief, SDK schema","Complete validation rules"),("Evidence Graph Model",45,"Reference architecture and graph model","Define contradiction edges"),("Policy-Bound Trust Evaluation",30,"Trust-policy engine requirements","Formalize threshold semantics")])
        if db.execute("SELECT COUNT(*) FROM milestones").fetchone()[0]==0:
            db.executemany("INSERT INTO milestones(title,target_date,progress,owner) VALUES(?,?,?,?)",[("First design partner","2026-10-15",20,"Founder"),("ETS alpha demonstration","2026-12-15",15,"Founder"),("$500K ARR run rate","2027-02-01",5,"Founder"),("Commercial general availability","2027-07-15",2,"Founder")])
        db.executemany("INSERT OR IGNORE INTO kpis(key,label,target,actual,unit) VALUES(?,?,?,?,?)",[("outreach","Weekly outreach",50,0,"count"),("discovery","Discovery calls",10,0,"count"),("proposals","Proposals sent",3,0,"count"),("mrr","Monthly recurring revenue",50000,0,"currency")])
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database(); yield

app=FastAPI(title="Lantern OS",version=VERSION,lifespan=lifespan)

class TaskCreate(BaseModel):
    title:str=Field(min_length=1,max_length=240); workstream:str="Operations"; priority:str="P1"; revenue_impact:str="Medium"; due_date:str|None=None
class TaskOut(TaskCreate):
    id:int; completed:bool
class SettingUpdate(BaseModel):
    value:str=Field(min_length=1,max_length=500)
class KPIUpdate(BaseModel):
    actual:float=Field(ge=0)

def row_to_task(row:sqlite3.Row)->dict: return {**dict(row),"completed":bool(row["completed"])}
def money(value:float)->str: return f"${value:,.0f}"
def esc(value:object)->str: return html.escape(str(value))

def recommendations(db:sqlite3.Connection)->list[dict[str,str]]:
    items=[]
    proposal=db.execute("SELECT * FROM opportunities WHERE stage='Proposal' ORDER BY value DESC LIMIT 1").fetchone()
    if proposal: items.append({"level":"Revenue","title":f"Advance {proposal['account']}","detail":proposal["next_action"] or "Define the next close action."})
    p0=db.execute("SELECT * FROM tasks WHERE completed=0 AND priority='P0' ORDER BY due_date LIMIT 1").fetchone()
    if p0: items.append({"level":"Execution","title":p0["title"],"detail":f"Due {p0['due_date'] or 'now'} · {p0['workstream']}"})
    paper=db.execute("SELECT * FROM research ORDER BY progress DESC LIMIT 1").fetchone()
    if paper: items.append({"level":"Research","title":f"Convert {paper['title']} into market proof","detail":paper["next_action"] or paper["commercial_output"]})
    return items[:3]

@app.get("/api/health")
def health(db:sqlite3.Connection=Depends(get_db))->dict:
    schema=db.execute("SELECT value FROM schema_meta WHERE key='version'").fetchone(); return {"status":"ok","service":"lantern-os","version":VERSION,"schema":schema[0] if schema else "unknown"}
@app.get("/api/tasks",response_model=list[TaskOut])
def list_tasks(db:sqlite3.Connection=Depends(get_db))->list[dict]: return [row_to_task(r) for r in db.execute("SELECT * FROM tasks ORDER BY completed,priority,due_date").fetchall()]
@app.post("/api/tasks",response_model=TaskOut)
def create_task(payload:TaskCreate,db:sqlite3.Connection=Depends(get_db))->dict:
    c=db.execute("INSERT INTO tasks(title,workstream,priority,revenue_impact,due_date) VALUES(?,?,?,?,?)",(payload.title,payload.workstream,payload.priority,payload.revenue_impact,payload.due_date)); db.commit(); return row_to_task(db.execute("SELECT * FROM tasks WHERE id=?",(c.lastrowid,)).fetchone())
@app.patch("/api/tasks/{task_id}/toggle",response_model=TaskOut)
def toggle_task(task_id:int,db:sqlite3.Connection=Depends(get_db))->dict:
    r=db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone()
    if r is None: raise HTTPException(status_code=404,detail="Task not found")
    db.execute("UPDATE tasks SET completed=? WHERE id=?",(0 if r["completed"] else 1,task_id)); db.commit(); return row_to_task(db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone())
@app.delete("/api/tasks/{task_id}",status_code=204)
def delete_task(task_id:int,db:sqlite3.Connection=Depends(get_db))->None:
    c=db.execute("DELETE FROM tasks WHERE id=?",(task_id,)); db.commit()
    if c.rowcount==0: raise HTTPException(status_code=404,detail="Task not found")
@app.get("/api/settings")
def list_settings(db:sqlite3.Connection=Depends(get_db))->dict[str,str]: return {r["key"]:r["value"] for r in db.execute("SELECT * FROM settings").fetchall()}
@app.put("/api/settings/{key}")
def update_setting(key:str,payload:SettingUpdate,db:sqlite3.Connection=Depends(get_db))->dict:
    db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,payload.value)); db.commit(); return {"key":key,"value":payload.value}
@app.get("/api/kpis")
def list_kpis(db:sqlite3.Connection=Depends(get_db))->list[dict]: return [dict(r) for r in db.execute("SELECT * FROM kpis ORDER BY key").fetchall()]
@app.patch("/api/kpis/{key}")
def update_kpi(key:str,payload:KPIUpdate,db:sqlite3.Connection=Depends(get_db))->dict:
    c=db.execute("UPDATE kpis SET actual=? WHERE key=?",(payload.actual,key)); db.commit()
    if c.rowcount==0: raise HTTPException(status_code=404,detail="KPI not found")
    return dict(db.execute("SELECT * FROM kpis WHERE key=?",(key,)).fetchone())
@app.get("/api/recommendations")
def get_recommendations(db:sqlite3.Connection=Depends(get_db))->list[dict[str,str]]: return recommendations(db)

def render_dashboard(db:sqlite3.Connection)->str:
    settings={r["key"]:r["value"] for r in db.execute("SELECT * FROM settings").fetchall()}; tasks=db.execute("SELECT * FROM tasks ORDER BY completed,priority,due_date").fetchall(); opportunities=db.execute("SELECT * FROM opportunities ORDER BY value DESC").fetchall(); research=db.execute("SELECT * FROM research ORDER BY progress DESC").fetchall(); milestones=db.execute("SELECT * FROM milestones ORDER BY target_date").fetchall(); kpis=db.execute("SELECT * FROM kpis ORDER BY key").fetchall(); recs=recommendations(db)
    pipeline=sum(r["value"] for r in opportunities); weighted=sum(r["value"]*r["probability"] for r in opportunities); completed=sum(r["completed"] for r in tasks); progress=round((completed/len(tasks)*100) if tasks else 0); overdue=sum(1 for r in tasks if not r["completed"] and r["due_date"] and r["due_date"]<date.today().isoformat())
    task_rows="".join(f'<tr class="{"done" if r["completed"] else ""}"><td><input type="checkbox" {"checked" if r["completed"] else ""} onchange="toggleTask({r["id"]})"></td><td><b>{esc(r["title"])}</b><small>{esc(r["workstream"])}</small></td><td><span class="pill">{esc(r["priority"])}</span></td><td>{esc(r["due_date"] or "—")}</td><td>{esc(r["revenue_impact"])}</td></tr>' for r in tasks)
    deal_cards="".join(f'<article><span>{esc(r["stage"])}</span><h3>{esc(r["account"])}</h3><b>{money(r["value"])}</b><small>{esc(r["next_action"] or "No next action")}</small></article>' for r in opportunities); research_cards="".join(f'<article><span>{r["progress"]}%</span><h3>{esc(r["title"])}</h3><div class="bar"><i style="width:{r["progress"]}%"></i></div><small>{esc(r["next_action"] or r["commercial_output"])}</small></article>' for r in research); milestone_rows="".join(f'<li><div><b>{esc(r["title"])}</b><small>{esc(r["owner"])}</small></div><span>{esc(r["target_date"])} · {r["progress"]}%</span></li>' for r in milestones); rec_cards="".join(f'<article class="recommend"><span>{esc(i["level"])}</span><h3>{esc(i["title"])}</h3><p>{esc(i["detail"])}</p></article>' for i in recs); kpi_cards="".join(f'<article><small>{esc(r["label"])}</small><b>{money(r["actual"]) if r["unit"]=="currency" else int(r["actual"])}</b><span>Target {money(r["target"]) if r["unit"]=="currency" else int(r["target"])}</span></article>' for r in kpis)
    org=esc(settings.get("organization_name","Lantern Protocol")); focus=esc(settings.get("daily_focus","Build the category. Ship the platform. Close the revenue.")); north_star=float(settings.get("north_star_arr","9500000"))
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Lantern OS {VERSION}</title><style>{CSS}</style></head><body><aside><h1>◇ Lantern OS</h1><p>Command Center</p><nav><a class='active' href='/'>Mission Control</a><a href='#today'>Today's Plan</a><a href='#revenue'>Sales CRM</a><a href='#research'>Research</a><a href='#roadmap'>Roadmap</a><a href='/docs'>API</a></nav><footer><small>NORTH STAR</small><b>{money(north_star)} ARR</b><span>{esc(settings.get('north_star_date','2028-02-01'))}</span><em>v{VERSION}</em></footer></aside><main><header><div><small>{org.upper()}</small><h2>Mission Control</h2></div><time>{date.today()}</time></header><section class='hero'><div><small>OPERATING MANDATE</small><h3>{focus}</h3><p>Daily command center for ETS commercialization.</p></div><strong>{progress}%<small> execution complete</small></strong></section><section class='stats'><article><small>Total pipeline</small><b>{money(pipeline)}</b></article><article><small>Weighted pipeline</small><b>{money(weighted)}</b></article><article><small>Open tasks</small><b>{len(tasks)-completed}</b><span>{overdue} overdue</span></article><article><small>Research programs</small><b>{len(research)}</b></article></section><section class='panel'><div class='section-head'><div><small>DECISION SUPPORT</small><h3>Today's recommended moves</h3></div><span>{datetime.now().strftime('%H:%M')}</span></div><div class='recommendations'>{rec_cards}</div></section><section class='panel' id='today'><div class='section-head'><h3>Daily execution</h3><span>{completed}/{len(tasks)} complete</span></div><table><thead><tr><th>Done</th><th>Task</th><th>Priority</th><th>Due</th><th>Impact</th></tr></thead><tbody>{task_rows}</tbody></table></section><section class='panel'><div class='section-head'><h3>Operating KPIs</h3><span>Current period</span></div><div class='stats kpis'>{kpi_cards}</div></section><section class='grid'><div class='panel' id='revenue'><h3>Revenue engine</h3><div class='cards'>{deal_cards}</div></div><div class='panel' id='research'><h3>Research-to-revenue</h3><div class='cards'>{research_cards}</div></div></section><section class='panel' id='roadmap'><h3>18-month milestones</h3><ul>{milestone_rows}</ul></section><script>async function toggleTask(id){{await fetch(`/api/tasks/${{id}}/toggle`,{{method:'PATCH'}});location.reload();}}</script></main></body></html>"""
@app.get("/",response_class=HTMLResponse)
def dashboard(db:sqlite3.Connection=Depends(get_db))->HTMLResponse: return HTMLResponse(render_dashboard(db))

CSS=":root{--bg:#080d12;--panel:#101821;--panel2:#131e29;--line:#263444;--text:#f1f5f9;--muted:#92a6ba;--gold:#f0bd45;--green:#45d2a8}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Segoe UI,sans-serif;display:flex;min-height:100vh}aside{position:fixed;width:250px;height:100vh;border-right:1px solid var(--line);padding:30px;background:#0a1118}aside h1{margin:0;color:var(--gold);font-size:34px}aside p,small,span{color:var(--muted)}nav{display:grid;gap:7px;margin-top:34px}nav a{color:var(--text);text-decoration:none;padding:12px 14px;border-radius:9px}nav a:hover,nav a.active{background:var(--panel2);color:var(--gold)}footer{position:absolute;bottom:26px;display:grid;gap:5px}footer b{font-size:22px;color:var(--gold)}footer em{font-size:12px;color:var(--muted);margin-top:8px}main{margin-left:250px;padding:34px;width:calc(100% - 250px);max-width:1500px}header{display:flex;justify-content:space-between;align-items:center}header h2{font-size:38px;margin:5px 0 24px}.hero{border:1px solid var(--line);background:linear-gradient(130deg,#14202b,#0e161e);padding:30px;border-radius:18px;display:flex;justify-content:space-between;align-items:center}.hero h3{font-size:31px;margin:7px 0;max-width:900px}.hero strong{font-size:46px;color:var(--gold)}.hero strong small{display:block;font-size:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}.stats article,.panel,.cards article,.recommend{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}.stats b{display:block;font-size:28px;margin:8px 0 3px}.panel{margin-bottom:18px}.section-head{display:flex;justify-content:space-between;align-items:center}.section-head h3{margin:5px 0 16px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.cards{display:grid;gap:10px}.cards article{display:grid;gap:7px;background:var(--panel2)}.cards article b{font-size:22px;color:var(--gold)}.bar{height:7px;background:#26313d;border-radius:8px;overflow:hidden}.bar i{display:block;height:100%;background:var(--green)}.recommendations{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.recommend{background:var(--panel2)}.recommend span,.pill{display:inline-block;color:var(--gold);font-size:12px;font-weight:700}.recommend h3{margin:8px 0}.recommend p{color:var(--muted);margin:0;line-height:1.5}.kpis{margin-bottom:0}.kpis article span{display:block;font-size:12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line)}td small{display:block;margin-top:4px}.done{opacity:.45;text-decoration:line-through}ul{list-style:none;padding:0}li{display:flex;justify-content:space-between;padding:14px 0;border-bottom:1px solid var(--line)}li div{display:grid;gap:4px}@media(max-width:1000px){aside{position:static;width:100%;height:auto}aside footer{display:none}body{display:block}main{margin:0;width:100%}.stats,.grid,.recommendations{grid-template-columns:1fr 1fr}}@media(max-width:650px){.stats,.grid,.recommendations{grid-template-columns:1fr}.hero strong{display:none}table{display:block;overflow:auto}}"