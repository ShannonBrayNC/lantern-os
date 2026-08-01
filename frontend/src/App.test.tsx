import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import App from './App'

vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
  const path = input instanceof Request ? input.url : input instanceof URL ? input.href : input
  const payload = path.endsWith('/api/me')
    ? { subject: 'local', name: 'Lantern Owner', email: 'owner@localhost', role: 'Owner', source: 'local' }
    : path.endsWith('/api/tasks')
      ? [{ id: 1, title: 'Ship frontend shell', workstream: 'Engineering', priority: 'P0', revenue_impact: 'High', due_date: '2026-08-02', completed: false }]
      : path.endsWith('/api/recommendations')
        ? [{ level: 'Execution', title: 'Ship frontend shell', detail: 'Complete Issue #5' }]
        : { score: 88, health: 'healthy', repository_count: 1, available_count: 1, refreshed_at: '2026-08-01T00:00:00Z', repositories: [{ repository: 'ShannonBrayNC/lantern-os', default_branch: 'main', open_issues: 1, open_pull_requests: 1, latest_workflow: 'success', latest_release: null, health: 'healthy', score: 88, refreshed_at: '2026-08-01T00:00:00Z', stale: false, error: null }] }
  return Promise.resolve(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }))
}))

test('renders the authenticated Mission Control shell', async () => {
  render(<App />)
  expect(await screen.findByText('Lantern Owner')).toBeInTheDocument()
  expect(screen.getByText('Ship frontend shell')).toBeInTheDocument()
  expect(screen.getByText('ShannonBrayNC/lantern-os')).toBeInTheDocument()
})
