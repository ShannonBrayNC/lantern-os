export type Principal = {
  subject: string
  name: string
  email: string
  role: string
  source: string
}

export type Task = {
  id: number
  title: string
  workstream: string
  priority: string
  revenue_impact: string
  due_date: string | null
  completed: boolean
}

export type Recommendation = {
  level: string
  title: string
  detail: string
}

export type RepositoryHealth = {
  repository: string
  default_branch: string | null
  open_issues: number | null
  open_pull_requests: number | null
  latest_workflow: string
  latest_release: string | null
  health: string
  score: number
  refreshed_at: string
  stale: boolean
  error: string | null
}

export type EngineeringPortfolio = {
  score: number
  health: string
  repository_count: number
  available_count: number
  repositories: RepositoryHealth[]
  refreshed_at: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `${response.status} ${response.statusText}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  principal: () => request<Principal>('/api/me'),
  tasks: () => request<Task[]>('/api/tasks'),
  toggleTask: (taskId: number) => request<Task>(`/api/tasks/${taskId}/toggle`, { method: 'PATCH' }),
  recommendations: () => request<Recommendation[]>('/api/recommendations'),
  engineering: () => request<EngineeringPortfolio>('/api/engineering')
}
