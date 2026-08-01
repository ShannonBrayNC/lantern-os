import { useEffect, useState } from 'react'
import { api, type EngineeringPortfolio, type Principal, type Recommendation, type Task } from './api'
import './styles.css'

type State = {
  principal: Principal | null
  tasks: Task[]
  recommendations: Recommendation[]
  engineering: EngineeringPortfolio | null
  error: string | null
}

const initialState: State = { principal: null, tasks: [], recommendations: [], engineering: null, error: null }

export default function App() {
  const [state, setState] = useState<State>(initialState)

  useEffect(() => {
    Promise.all([api.principal(), api.tasks(), api.recommendations(), api.engineering()])
      .then(([principal, tasks, recommendations, engineering]) => setState({ principal, tasks, recommendations, engineering, error: null }))
      .catch((error: unknown) => setState((current) => ({ ...current, error: error instanceof Error ? error.message : 'Unable to load Lantern OS' })))
  }, [])

  const openTasks = state.tasks.filter((task) => !task.completed)

  return (
    <div className="shell">
      <aside aria-label="Primary navigation">
        <h1>◇ Lantern OS</h1>
        <p>Command Center</p>
        <nav>
          <a aria-current="page" href="#mission">Mission Control</a>
          <a href="#today">Today's Plan</a>
          <a href="#engineering">Engineering</a>
          <a href="/docs">API</a>
          <a href="/legacy">Legacy Dashboard</a>
        </nav>
      </aside>
      <main id="mission">
        <header>
          <div><small>LANTERN PROTOCOL</small><h2>Mission Control</h2></div>
          <div className="identity"><b>{state.principal?.name ?? 'Loading…'}</b><small>{state.principal?.role ?? ''}</small></div>
        </header>
        {state.error && <div role="alert" className="error">{state.error}</div>}
        <section className="hero">
          <div><small>OPERATING MANDATE</small><h3>Build the category. Ship the platform. Close the revenue.</h3></div>
          <strong>{openTasks.length}<small> open tasks</small></strong>
        </section>
        <section aria-labelledby="recommendations-title">
          <h3 id="recommendations-title">Today's recommended moves</h3>
          <div className="cards">{state.recommendations.map((item) => <article key={`${item.level}-${item.title}`}><span>{item.level}</span><h4>{item.title}</h4><p>{item.detail}</p></article>)}</div>
        </section>
        <section id="today" aria-labelledby="tasks-title">
          <h3 id="tasks-title">Daily execution</h3>
          <div className="cards">{openTasks.map((task) => <article key={task.id}><span>{task.priority} · {task.workstream}</span><h4>{task.title}</h4><p>Due {task.due_date ?? 'now'} · {task.revenue_impact} impact</p></article>)}</div>
        </section>
        <section id="engineering" aria-labelledby="engineering-title">
          <h3 id="engineering-title">Engineering portfolio</h3>
          <div className="portfolio-summary"><b>{state.engineering?.score ?? 0}%</b><span>{state.engineering?.health ?? 'unavailable'} · {state.engineering?.available_count ?? 0}/{state.engineering?.repository_count ?? 0} available</span></div>
          <div className="cards">{state.engineering?.repositories.map((repo) => <article key={repo.repository}><span>{repo.health} · {repo.score}%</span><h4>{repo.repository}</h4><p>{repo.default_branch ?? 'No branch'} · {repo.open_pull_requests ?? '—'} PRs · {repo.latest_workflow}</p></article>)}</div>
        </section>
      </main>
    </div>
  )
}
