from __future__ import annotations

import html
import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    Principal,
    auth_mode,
    build_oauth,
    current_principal,
    principal_from_claims,
    require_roles,
    session_secret,
)
from app.database import engine, get_session
from app.github_portfolio import portfolio_service
from app.models import (
    Base,
    KPI,
    Milestone,
    Opportunity,
    ResearchProgram,
    SchemaMeta,
    Setting,
    Task,
)

VERSION = "0.8.0"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    workstream: str = "Operations"
    priority: str = "P1"
    revenue_impact: str = "Medium"
    due_date: str | None = None


class TaskOut(TaskCreate):
    id: int
    completed: bool


class SettingUpdate(BaseModel):
    value: str = Field(min_length=1, max_length=500)


class KPIUpdate(BaseModel):
    actual: float = Field(ge=0)


def seed_database(session: Session) -> None:
    meta = session.get(SchemaMeta, "version")
    if meta is None:
        session.add(SchemaMeta(key="version", value=VERSION))
    else:
        meta.value = VERSION
    defaults = {
        "organization_name": "Lantern Protocol",
        "north_star_arr": "9500000",
        "north_star_date": "2028-02-01",
        "daily_focus": "Build the category. Ship the platform. Close the revenue.",
        "github_org": "ShannonBrayNC",
    }
    for key, value in defaults.items():
        if session.get(Setting, key) is None:
            session.add(Setting(key=key, value=value))
    if session.scalar(select(Task.id).limit(1)) is None:
        session.add_all(
            [
                Task(
                    title="Publish ETS category thesis",
                    workstream="Marketing",
                    priority="P0",
                    revenue_impact="High",
                    due_date="2026-08-03",
                ),
                Task(
                    title="Complete evidence-object API slice",
                    workstream="Engineering",
                    priority="P0",
                    revenue_impact="High",
                    due_date="2026-08-05",
                ),
                Task(
                    title="Contact ten design-partner prospects",
                    workstream="Sales",
                    priority="P0",
                    revenue_impact="High",
                    due_date="2026-08-04",
                ),
                Task(
                    title="Advance Evidence Graph working paper",
                    workstream="Research",
                    priority="P1",
                    revenue_impact="Medium",
                    due_date="2026-08-07",
                ),
            ]
        )
    if session.scalar(select(Opportunity.id).limit(1)) is None:
        session.add_all(
            [
                Opportunity(
                    account="Healthcare design partner",
                    stage="Discovery",
                    value=75000,
                    probability=0.25,
                    next_action="Schedule architecture workshop",
                    next_date="2026-08-05",
                ),
                Opportunity(
                    account="State-government pilot",
                    stage="Prospecting",
                    value=150000,
                    probability=0.10,
                    next_action="Identify executive sponsor",
                    next_date="2026-08-06",
                ),
                Opportunity(
                    account="Enterprise evidence assessment",
                    stage="Proposal",
                    value=50000,
                    probability=0.50,
                    next_action="Send scoped proposal",
                    next_date="2026-08-03",
                ),
            ]
        )
    if session.scalar(select(ResearchProgram.id).limit(1)) is None:
        session.add_all(
            [
                ResearchProgram(
                    title="Evidence Object Model",
                    progress=70,
                    commercial_output="Specification, sales brief, SDK schema",
                    next_action="Complete validation rules",
                ),
                ResearchProgram(
                    title="Evidence Graph Model",
                    progress=45,
                    commercial_output="Reference architecture and graph model",
                    next_action="Define contradiction edges",
                ),
                ResearchProgram(
                    title="Policy-Bound Trust Evaluation",
                    progress=30,
                    commercial_output="Trust-policy engine requirements",
                    next_action="Formalize threshold semantics",
                ),
            ]
        )
    if session.scalar(select(Milestone.id).limit(1)) is None:
        session.add_all(
            [
                Milestone(
                    title="First design partner",
                    target_date="2026-10-15",
                    progress=20,
                    owner="Founder",
                ),
                Milestone(
                    title="ETS alpha demonstration",
                    target_date="2026-12-15",
                    progress=15,
                    owner="Founder",
                ),
                Milestone(
                    title="$500K ARR run rate",
                    target_date="2027-02-01",
                    progress=5,
                    owner="Founder",
                ),
                Milestone(
                    title="Commercial general availability",
                    target_date="2027-07-15",
                    progress=2,
                    owner="Founder",
                ),
            ]
        )
    for key, label, target, unit in [
        ("outreach", "Weekly outreach", 50, "count"),
        ("discovery", "Discovery calls", 10, "count"),
        ("proposals", "Proposals sent", 3, "count"),
        ("mrr", "Monthly recurring revenue", 50000, "currency"),
    ]:
        if session.get(KPI, key) is None:
            session.add(KPI(key=key, label=label, target=target, actual=0, unit=unit))
    session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_database(session)
    yield


app = FastAPI(title="Lantern OS", version=VERSION, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret(),
    https_only=os.getenv("LANTERN_COOKIE_HTTPS_ONLY", "false").lower() == "true",
    same_site="lax",
)
oauth = build_oauth()


def task_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "workstream": task.workstream,
        "priority": task.priority,
        "revenue_impact": task.revenue_impact,
        "due_date": task.due_date,
        "completed": bool(task.completed),
    }


def money(value: float) -> str:
    return f"${value:,.0f}"


def esc(value: object) -> str:
    return html.escape(str(value))


def recommendations(session: Session) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    proposal = session.scalars(
        select(Opportunity)
        .where(Opportunity.stage == "Proposal")
        .order_by(Opportunity.value.desc())
        .limit(1)
    ).first()
    if proposal:
        items.append(
            {
                "level": "Revenue",
                "title": f"Advance {proposal.account}",
                "detail": proposal.next_action or "Define the next close action.",
            }
        )
    p0 = session.scalars(
        select(Task)
        .where(Task.completed.is_(False), Task.priority == "P0")
        .order_by(Task.due_date)
        .limit(1)
    ).first()
    if p0:
        items.append(
            {
                "level": "Execution",
                "title": p0.title,
                "detail": f"Due {p0.due_date or 'now'} · {p0.workstream}",
            }
        )
    paper = session.scalars(
        select(ResearchProgram).order_by(ResearchProgram.progress.desc()).limit(1)
    ).first()
    if paper:
        items.append(
            {
                "level": "Research",
                "title": f"Convert {paper.title} into market proof",
                "detail": paper.next_action or paper.commercial_output,
            }
        )
    return items[:3]


@app.get("/auth/login")
async def login(request: Request):
    if auth_mode() == "local":
        return RedirectResponse("/")
    redirect_uri = os.getenv(
        "LANTERN_ENTRA_REDIRECT_URI", str(request.url_for("auth_callback"))
    )
    return await oauth.entra.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    token = await oauth.entra.authorize_access_token(request)
    claims = token.get("userinfo") or await oauth.entra.parse_id_token(request, token)
    request.session["principal"] = principal_from_claims(dict(claims)).to_dict()
    return RedirectResponse("/")


@app.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/api/health")
def health(session: Session = Depends(get_session)) -> dict:
    schema = session.get(SchemaMeta, "version")
    return {
        "status": "ok",
        "service": "lantern-os",
        "version": VERSION,
        "schema": schema.value if schema else "unknown",
        "auth_mode": auth_mode(),
        "database": engine.dialect.name,
    }


@app.get("/api/me")
def me(principal: Principal = Depends(current_principal)) -> dict[str, str]:
    return principal.to_dict()


@app.get("/api/engineering")
def engineering(
    _: Principal = Depends(require_roles("Viewer")), refresh: bool = False
) -> dict:
    return portfolio_service.portfolio(force=refresh)


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(
    _: Principal = Depends(require_roles("Viewer")),
    session: Session = Depends(get_session),
) -> list[dict]:
    query = select(Task).order_by(Task.completed, Task.priority, Task.due_date)
    return [task_dict(item) for item in session.scalars(query).all()]


@app.post("/api/tasks", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    _: Principal = Depends(require_roles("Operator")),
    session: Session = Depends(get_session),
) -> dict:
    task = Task(**payload.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task_dict(task)


@app.patch("/api/tasks/{task_id}/toggle", response_model=TaskOut)
def toggle_task(
    task_id: int,
    _: Principal = Depends(require_roles("Operator")),
    session: Session = Depends(get_session),
) -> dict:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.completed = not task.completed
    session.commit()
    session.refresh(task)
    return task_dict(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    _: Principal = Depends(require_roles("Owner")),
    session: Session = Depends(get_session),
) -> None:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()


@app.get("/api/settings")
def list_settings(
    _: Principal = Depends(require_roles("Viewer")),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return {item.key: item.value for item in session.scalars(select(Setting)).all()}


@app.put("/api/settings/{key}")
def update_setting(
    key: str,
    payload: SettingUpdate,
    _: Principal = Depends(require_roles("Executive")),
    session: Session = Depends(get_session),
) -> dict:
    item = session.get(Setting, key)
    if item is None:
        item = Setting(key=key, value=payload.value)
        session.add(item)
    else:
        item.value = payload.value
    session.commit()
    return {"key": key, "value": payload.value}


@app.get("/api/kpis")
def list_kpis(
    _: Principal = Depends(require_roles("Viewer")),
    session: Session = Depends(get_session),
) -> list[dict]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "target": item.target,
            "actual": item.actual,
            "unit": item.unit,
        }
        for item in session.scalars(select(KPI).order_by(KPI.key)).all()
    ]


@app.patch("/api/kpis/{key}")
def update_kpi(
    key: str,
    payload: KPIUpdate,
    _: Principal = Depends(require_roles("Operator")),
    session: Session = Depends(get_session),
) -> dict:
    item = session.get(KPI, key)
    if item is None:
        raise HTTPException(status_code=404, detail="KPI not found")
    item.actual = payload.actual
    session.commit()
    return {
        "key": item.key,
        "label": item.label,
        "target": item.target,
        "actual": item.actual,
        "unit": item.unit,
    }


@app.get("/api/recommendations")
def get_recommendations(
    _: Principal = Depends(require_roles("Viewer")),
    session: Session = Depends(get_session),
) -> list[dict[str, str]]:
    return recommendations(session)


def render_dashboard(session: Session, principal: Principal) -> str:
    settings = {item.key: item.value for item in session.scalars(select(Setting)).all()}
    tasks = session.scalars(
        select(Task).order_by(Task.completed, Task.priority, Task.due_date)
    ).all()
    opportunities = session.scalars(
        select(Opportunity).order_by(Opportunity.value.desc())
    ).all()
    research = session.scalars(
        select(ResearchProgram).order_by(ResearchProgram.progress.desc())
    ).all()
    milestones = session.scalars(
        select(Milestone).order_by(Milestone.target_date)
    ).all()
    kpis = session.scalars(select(KPI).order_by(KPI.key)).all()
    portfolio = portfolio_service.portfolio()
    recs = recommendations(session)
    pipeline = sum(item.value for item in opportunities)
    weighted = sum(item.value * item.probability for item in opportunities)
    completed = sum(1 for item in tasks if item.completed)
    progress = round((completed / len(tasks) * 100) if tasks else 0)
    overdue = sum(
        1
        for item in tasks
        if not item.completed
        and item.due_date
        and item.due_date < date.today().isoformat()
    )
    task_rows = "".join(
        f'<tr class="{"done" if item.completed else ""}"><td><input type="checkbox" '
        f'{"checked" if item.completed else ""} onchange="toggleTask({item.id})"></td>'
        f'<td><b>{esc(item.title)}</b><small>{esc(item.workstream)}</small></td>'
        f'<td>{esc(item.priority)}</td><td>{esc(item.due_date or "—")}</td>'
        f'<td>{esc(item.revenue_impact)}</td></tr>'
        for item in tasks
    )
    rec_cards = "".join(
        f'<article><span>{esc(item["level"])}</span><h3>{esc(item["title"])}</h3>'
        f'<p>{esc(item["detail"])}</p></article>'
        for item in recs
    )
    deal_cards = "".join(
        f'<article><span>{esc(item.stage)}</span><h3>{esc(item.account)}</h3>'
        f'<b>{money(item.value)}</b><small>{esc(item.next_action)}</small></article>'
        for item in opportunities
    )
    research_cards = "".join(
        f'<article><span>{item.progress}%</span><h3>{esc(item.title)}</h3>'
        f'<small>{esc(item.next_action or item.commercial_output)}</small></article>'
        for item in research
    )
    milestone_rows = "".join(
        f'<li><b>{esc(item.title)}</b><span>{esc(item.target_date)} · '
        f'{item.progress}%</span></li>'
        for item in milestones
    )
    kpi_cards = "".join(
        f'<article><small>{esc(item.label)}</small>'
        f'<b>{money(item.actual) if item.unit == "currency" else int(item.actual)}</b>'
        f'<span>Target '
        f'{money(item.target) if item.unit == "currency" else int(item.target)}</span>'
        f'</article>'
        for item in kpis
    )
    repo_rows = "".join(
        f'<tr><td><b>{esc(item["repository"])}</b>'
        f'<small>{"STALE · " if item["stale"] else ""}'
        f'{esc(item["default_branch"] or "unavailable")}</small></td>'
        f'<td><span class="status {esc(item["health"])}">'
        f'{esc(item["health"])}</span></td><td>{item["score"]}</td>'
        f'<td>{esc(item["open_pull_requests"] if item["open_pull_requests"] is not None else "—")}</td>'
        f'<td>{esc(item["latest_workflow"])}</td>'
        f'<td>{esc(item["latest_release"] or "—")}</td></tr>'
        for item in portfolio["repositories"]
    )
    org = esc(settings.get("organization_name", "Lantern Protocol"))
    focus = esc(
        settings.get(
            "daily_focus",
            "Build the category. Ship the platform. Close the revenue.",
        )
    )
    north_star = float(settings.get("north_star_arr", "9500000"))
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Lantern OS {VERSION}</title><style>{CSS}</style></head><body><aside><h1>◇ Lantern OS</h1><p>Command Center</p><nav><a href='/'>Mission Control</a><a href='#today'>Today's Plan</a><a href='#engineering'>Engineering</a><a href='#revenue'>Sales CRM</a><a href='#research'>Research</a><a href='#roadmap'>Roadmap</a><a href='/docs'>API</a></nav><footer><small>NORTH STAR</small><b>{money(north_star)} ARR</b><span>{esc(settings.get('north_star_date','2028-02-01'))}</span><em>v{VERSION}</em></footer></aside><main><header><div><small>{org.upper()}</small><h2>Mission Control</h2></div><div><b>{esc(principal.name)}</b><small>{esc(principal.role)} · {engine.dialect.name}</small></div></header><section class='hero'><div><small>OPERATING MANDATE</small><h3>{focus}</h3><p>Daily command center for ETS commercialization.</p></div><strong>{progress}%<small> execution complete</small></strong></section><section class='stats'><article><small>Total pipeline</small><b>{money(pipeline)}</b></article><article><small>Weighted pipeline</small><b>{money(weighted)}</b></article><article><small>Engineering health</small><b>{portfolio['score']}%</b><span>{portfolio['available_count']}/{portfolio['repository_count']} available</span></article><article><small>Open tasks</small><b>{len(tasks)-completed}</b><span>{overdue} overdue</span></article></section><section class='panel'><h3>Today's recommended moves</h3><div class='cards'>{rec_cards}</div></section><section class='panel' id='engineering'><h3>Engineering portfolio</h3><p class='muted'>Cached GitHub data · refreshed {esc(portfolio['refreshed_at'])}</p><table><thead><tr><th>Repository</th><th>Health</th><th>Score</th><th>PRs</th><th>Workflow</th><th>Release</th></tr></thead><tbody>{repo_rows}</tbody></table></section><section class='panel' id='today'><h3>Daily execution</h3><table><thead><tr><th>Done</th><th>Task</th><th>Priority</th><th>Due</th><th>Impact</th></tr></thead><tbody>{task_rows}</tbody></table></section><section class='panel'><h3>Operating KPIs</h3><div class='stats'>{kpi_cards}</div></section><section class='grid'><div class='panel' id='revenue'><h3>Revenue engine</h3><div class='cards'>{deal_cards}</div></div><div class='panel' id='research'><h3>Research-to-revenue</h3><div class='cards'>{research_cards}</div></div></section><section class='panel' id='roadmap'><h3>18-month milestones</h3><ul>{milestone_rows}</ul></section><script>async function toggleTask(id){{await fetch(`/api/tasks/${{id}}/toggle`,{{method:'PATCH'}});location.reload();}}</script></main></body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard(
    principal: Principal = Depends(current_principal),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    return HTMLResponse(render_dashboard(session, principal))


CSS = ":root{--bg:#080d12;--panel:#101821;--line:#263444;--text:#f1f5f9;--muted:#92a6ba;--gold:#f0bd45}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Segoe UI,sans-serif;display:flex;min-height:100vh}aside{position:fixed;width:250px;height:100vh;border-right:1px solid var(--line);padding:30px;background:#0a1118}aside h1{color:var(--gold);font-size:34px}nav{display:grid;gap:8px;margin-top:30px}nav a{color:var(--text);text-decoration:none;padding:10px}footer{position:absolute;bottom:25px;display:grid;gap:5px}footer b{color:var(--gold)}main{margin-left:250px;padding:34px;width:calc(100% - 250px)}header,.hero{display:flex;justify-content:space-between;align-items:center}.hero,.panel,.stats article,.cards article{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.hero strong{font-size:44px;color:var(--gold)}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}.stats b{display:block;font-size:28px}.panel{margin-bottom:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.cards{display:grid;gap:10px}.cards article span{color:var(--gold)}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line)}td small,header small,.muted{display:block;color:var(--muted)}.done{opacity:.45;text-decoration:line-through}.status{padding:4px 8px;border-radius:12px}.healthy{color:#74d99f}.attention{color:#f0bd45}.critical,.unavailable{color:#ff7b7b}ul{list-style:none;padding:0}li{display:flex;justify-content:space-between;padding:12px;border-bottom:1px solid var(--line)}@media(max-width:900px){aside{position:static;width:100%;height:auto}aside footer{display:none}body{display:block}main{margin:0;width:100%}.stats,.grid{grid-template-columns:1fr 1fr}}@media(max-width:600px){.stats,.grid{grid-template-columns:1fr}.hero strong{display:none}}"
