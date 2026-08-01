from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "lantern.db"


def connect() -> sqlite3.Connection:
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                workstream TEXT NOT NULL DEFAULT 'Operations',
                priority TEXT NOT NULL DEFAULT 'P1',
                revenue_impact TEXT NOT NULL DEFAULT 'Medium',
                due_date TEXT,
                completed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL,
                stage TEXT NOT NULL,
                value REAL NOT NULL,
                probability REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                commercial_output TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                target_date TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        if db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO tasks(title, workstream, priority, revenue_impact, due_date) VALUES(?,?,?,?,?)",
                [
                    ("Publish ETS category thesis", "Marketing", "P0", "High", "2026-08-03"),
                    ("Complete evidence-object API slice", "Engineering", "P0", "High", "2026-08-05"),
                    ("Contact ten design-partner prospects", "Sales", "P0", "High", "2026-08-04"),
                    ("Advance Evidence Graph working paper", "Research", "P1", "Medium", "2026-08-07"),
                ],
            )
            db.executemany(
                "INSERT INTO opportunities(account, stage, value, probability) VALUES(?,?,?,?)",
                [
                    ("Healthcare design partner", "Discovery", 75000, 0.25),
                    ("State-government pilot", "Prospecting", 150000, 0.10),
                    ("Enterprise evidence assessment", "Proposal", 50000, 0.50),
                ],
            )
            db.executemany(
                "INSERT INTO research(title, progress, commercial_output) VALUES(?,?,?)",
                [
                    ("Evidence Object Model", 70, "Specification, sales brief, and SDK schema"),
                    ("Evidence Graph Model", 45, "Reference architecture and product graph model"),
                    ("Policy-Bound Trust Evaluation", 30, "Trust-policy engine requirements"),
                ],
            )
            db.executemany(
                "INSERT INTO milestones(title, target_date, progress) VALUES(?,?,?)",
                [
                    ("First design partner", "2026-10-15", 20),
                    ("ETS alpha demonstration", "2026-12-15", 15),
                    ("$500K ARR run rate", "2027-02-01", 5),
                    ("Commercial general availability", "2027-07-15", 2),
                ],
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Lantern OS", version="0.3.0", lifespan=lifespan)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    workstream: str = "Operations"
    priority: str = "P1"
    revenue_impact: str = "Medium"
    due_date: str | None = None


class TaskOut(TaskCreate):
    id: int
    completed: bool


def row_to_task(row: sqlite3.Row) -> dict:
    return {**dict(row), "completed": bool(row["completed"])}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "lantern-os", "version": "0.3.0"}


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(db: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    rows = db.execute("SELECT * FROM tasks ORDER BY completed, priority, due_date").fetchall()
    return [row_to_task(row) for row in rows]


@app.post("/api/tasks", response_model=TaskOut)
def create_task(payload: TaskCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    cursor = db.execute(
        "INSERT INTO tasks(title, workstream, priority, revenue_impact, due_date) VALUES(?,?,?,?,?)",
        (payload.title, payload.workstream, payload.priority, payload.revenue_impact, payload.due_date),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id=?", (cursor.lastrowid,)).fetchone()
    return row_to_task(row)


@app.patch("/api/tasks/{task_id}/toggle", response_model=TaskOut)
def toggle_task(task_id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.execute("UPDATE tasks SET completed=? WHERE id=?", (0 if row["completed"] else 1, task_id))
    db.commit()
    return row_to_task(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: sqlite3.Connection = Depends(get_db)) -> None:
    cursor = db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")


def money(value: float) -> str:
    return f"${value:,.0f}"


def render_dashboard(db: sqlite3.Connection) -> str:
    tasks = db.execute("SELECT * FROM tasks ORDER BY completed, priority, due_date").fetchall()
    opportunities = db.execute("SELECT * FROM opportunities ORDER BY value DESC").fetchall()
    research = db.execute("SELECT * FROM research ORDER BY progress DESC").fetchall()
    milestones = db.execute("SELECT * FROM milestones ORDER BY target_date").fetchall()
    pipeline = sum(row["value"] for row in opportunities)
    weighted = sum(row["value"] * row["probability"] for row in opportunities)
    completed = sum(row["completed"] for row in tasks)
    progress = round((completed / len(tasks) * 100) if tasks else 0)
    task_rows = "".join(
        f'<tr class="{"done" if row["completed"] else ""}"><td><input type="checkbox" {"checked" if row["completed"] else ""} onchange="toggleTask({row["id"]})"></td><td><b>{row["title"]}</b><small>{row["workstream"]}</small></td><td>{row["priority"]}</td><td>{row["due_date"] or "—"}</td><td>{row["revenue_impact"]}</td></tr>'
        for row in tasks
    )
    deal_cards = "".join(
        f'<article><span>{row["stage"]}</span><h3>{row["account"]}</h3><b>{money(row["value"])}</b><small>Weighted {money(row["value"] * row["probability"])}</small></article>'
        for row in opportunities
    )
    research_cards = "".join(
        f'<article><span>{row["progress"]}%</span><h3>{row["title"]}</h3><div class="bar"><i style="width:{row["progress"]}%"></i></div><small>{row["commercial_output"]}</small></article>'
        for row in research
    )
    milestone_rows = "".join(
        f'<li><b>{row["title"]}</b><span>{row["target_date"]} · {row["progress"]}%</span></li>'
        for row in milestones
    )
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Lantern OS</title><style>{CSS}</style></head><body><aside><h1>◇ Lantern OS</h1><p>Command Center</p><nav><a href='/'>Mission Control</a><a href='/docs'>API</a></nav><footer><small>NORTH STAR</small><b>$9.5M ARR</b><span>February 2028</span></footer></aside><main><header><div><small>LANTERN PROTOCOL</small><h2>Mission Control</h2></div><time>{date.today()}</time></header><section class='hero'><div><small>OPERATING MANDATE</small><h3>Build the category. Ship the platform. Close the revenue.</h3><p>Daily command center for ETS commercialization.</p></div><strong>{progress}%<small> execution complete</small></strong></section><section class='stats'><article><small>Total pipeline</small><b>{money(pipeline)}</b></article><article><small>Weighted pipeline</small><b>{money(weighted)}</b></article><article><small>Open tasks</small><b>{len(tasks)-completed}</b></article><article><small>Research programs</small><b>{len(research)}</b></article></section><section class='panel'><h3>Daily execution</h3><table><thead><tr><th>Done</th><th>Task</th><th>Priority</th><th>Due</th><th>Impact</th></tr></thead><tbody>{task_rows}</tbody></table></section><section class='grid'><div class='panel'><h3>Revenue engine</h3><div class='cards'>{deal_cards}</div></div><div class='panel'><h3>Research-to-revenue</h3><div class='cards'>{research_cards}</div></div></section><section class='panel'><h3>18-month milestones</h3><ul>{milestone_rows}</ul></section><script>async function toggleTask(id){{await fetch(`/api/tasks/${{id}}/toggle`,{{method:'PATCH'}});location.reload();}}</script></main></body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard(db: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    return HTMLResponse(render_dashboard(db))


CSS = """
:root{--bg:#090d11;--panel:#111820;--line:#26313d;--text:#edf2f7;--muted:#92a0ad;--gold:#e6b94f;--green:#4fd1a5}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Segoe UI,sans-serif;display:flex;min-height:100vh}aside{position:fixed;width:230px;height:100vh;border-right:1px solid var(--line);padding:28px;background:#0c1117}aside h1{margin:0;color:var(--gold)}aside p,small,span{color:var(--muted)}nav{display:grid;gap:8px;margin-top:36px}nav a{color:var(--text);text-decoration:none;padding:12px;border-radius:8px}nav a:hover{background:var(--panel)}footer{position:absolute;bottom:28px;display:grid;gap:5px}footer b{font-size:24px;color:var(--gold)}main{margin-left:230px;padding:32px;width:calc(100% - 230px)}header{display:flex;justify-content:space-between;align-items:center}header h2{font-size:34px;margin:4px 0 24px}.hero{border:1px solid var(--line);background:linear-gradient(130deg,#131d27,#10161d);padding:28px;border-radius:16px;display:flex;justify-content:space-between;align-items:center}.hero h3{font-size:30px;margin:6px 0}.hero strong{font-size:42px;color:var(--gold)}.hero strong small{display:block;font-size:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}.stats article,.panel,.cards article{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}.stats b{display:block;font-size:28px;margin-top:8px}.panel{margin-bottom:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.cards{display:grid;gap:10px}.cards article{display:grid;gap:7px}.cards article b{font-size:22px;color:var(--gold)}.bar{height:7px;background:#26313d;border-radius:8px;overflow:hidden}.bar i{display:block;height:100%;background:var(--green)}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line)}td small{display:block;margin-top:4px}.done{opacity:.45;text-decoration:line-through}ul{list-style:none;padding:0}li{display:flex;justify-content:space-between;padding:13px 0;border-bottom:1px solid var(--line)}@media(max-width:900px){aside{position:static;width:100%;height:auto}aside footer{display:none}body{display:block}main{margin:0;width:100%}.stats,.grid{grid-template-columns:1fr 1fr}}@media(max-width:620px){.stats,.grid{grid-template-columns:1fr}.hero strong{display:none}table{display:block;overflow:auto}}
"""
