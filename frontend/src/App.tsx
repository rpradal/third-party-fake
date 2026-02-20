import { useEffect, useState } from 'react'

const PAYMENT_TERMS = ['Net 30', 'Net 60'] as const
type PaymentTerm = (typeof PAYMENT_TERMS)[number]

type Customer = {
  id: string
  archived: boolean
  payment_term: PaymentTerm | null
}

type WebhookAttempt = {
  at: string
  customer_id: string
  webhook_url: string | null
  success: boolean
  status_code: number | null
  error: string | null
}

type InboundAttempt = {
  at: string
  method: string
  path: string
  payload: unknown
  success: boolean
  status_code: number
  error: string | null
}

type ApiState = {
  webhook_url: string | null
  customers: Customer[]
  webhook_attempts: WebhookAttempt[]
  inbound_attempts: InboundAttempt[]
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(body || `HTTP ${res.status}`)
  }

  return (await res.json()) as T
}

function formatDate(input: string): string {
  const date = new Date(input)
  if (Number.isNaN(date.getTime())) return input
  return date.toLocaleString()
}

export default function App() {
  const [state, setState] = useState<ApiState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [webhookInput, setWebhookInput] = useState('')
  const [savingById, setSavingById] = useState<Record<string, boolean>>({})

  const customers = state?.customers ?? []
  const webhookAttempts = state?.webhook_attempts ?? []
  const inboundAttempts = state?.inbound_attempts ?? []

  async function refreshState() {
    setLoading(true)
    setError(null)
    try {
      const next = await fetchJson<ApiState>('/state')
      setState(next)
      setWebhookInput((current) => current || next.webhook_url || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshState()
    const timer = window.setInterval(() => {
      void refreshState()
    }, 5000)

    return () => window.clearInterval(timer)
  }, [])

  async function saveWebhookUrl() {
    setError(null)
    try {
      await fetchJson('/webhook/config', {
        method: 'POST',
        body: JSON.stringify({ webhook_url: webhookInput }),
      })
      await refreshState()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  async function patchCustomer(
    customerId: string,
    patch: Partial<Pick<Customer, 'archived' | 'payment_term'>>,
  ) {
    setError(null)
    setSavingById((prev) => ({ ...prev, [customerId]: true }))
    setState((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        customers: prev.customers.map((customer) =>
          customer.id === customerId ? { ...customer, ...patch } : customer,
        ),
      }
    })
    try {
      await fetchJson(`/customers/${encodeURIComponent(customerId)}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      })
      await refreshState()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      await refreshState()
    } finally {
      setSavingById((prev) => ({ ...prev, [customerId]: false }))
    }
  }

  return (
    <main className="page">
      <header className="hero">
        <h1>Fake Third Party Console</h1>
        <p>Demo ERP sync: query, local edit, et appel webhook implicite au Save.</p>
      </header>

      {error ? <p className="error">{error}</p> : null}

      <section className="card">
        <h2>Webhook ERP</h2>
        <div className="row">
          <input
            type="url"
            placeholder="https://erp.example.com/webhook"
            value={webhookInput}
            onChange={(e) => setWebhookInput(e.target.value)}
          />
          <button onClick={saveWebhookUrl}>Save webhook URL</button>
        </div>
      </section>

      <section className="card">
        <h2>Customers ({customers.length})</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Archived</th>
                <th>Payment Term</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr key={customer.id}>
                  <td className="mono">{customer.id}</td>
                  <td>
                    <input
                      type="checkbox"
                      checked={customer.archived}
                      onChange={(e) => void patchCustomer(customer.id, { archived: e.target.checked })}
                      disabled={savingById[customer.id] ?? false}
                    />
                  </td>
                  <td>
                    <select
                      value={customer.payment_term ?? ''}
                      onChange={(e) =>
                        void patchCustomer(customer.id, {
                          payment_term: e.target.value === '' ? null : (e.target.value as PaymentTerm),
                        })
                      }
                      disabled={savingById[customer.id] ?? false}
                    >
                      <option value="">None</option>
                      {PAYMENT_TERMS.map((term) => (
                        <option key={term} value={term}>
                          {term}
                        </option>
                      ))}
                    </select>
                    {savingById[customer.id] ? <span className="saving-inline">Saving...</span> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="attempts-grid">
        <section className="card attempts-card">
          <h2>Webhook Outbound Attempts</h2>
          <div className="attempts">
            {webhookAttempts.length === 0 ? <p>No attempts yet.</p> : null}
            {webhookAttempts.map((attempt, index) => (
              <article key={`${attempt.at}-${attempt.customer_id}-${index}`} className="attempt">
                <p>
                  <strong>{attempt.success ? 'SUCCESS' : 'FAILED'}</strong> - {formatDate(attempt.at)}
                </p>
                <p>
                  customer=<span className="mono">{attempt.customer_id}</span> status=
                  {attempt.status_code ?? 'n/a'}
                </p>
                {attempt.webhook_url ? <p>url={attempt.webhook_url}</p> : null}
                {attempt.error ? <p className="error-inline">error={attempt.error}</p> : null}
              </article>
            ))}
          </div>
        </section>

        <section className="card attempts-card">
          <h2>Inbound ERP Attempts</h2>
          <div className="attempts">
            {inboundAttempts.length === 0 ? <p>No inbound attempts yet.</p> : null}
            {inboundAttempts.map((attempt, index) => (
              <article key={`${attempt.at}-${attempt.method}-${attempt.path}-${index}`} className="attempt">
                <p>
                  <strong>{attempt.success ? 'SUCCESS' : 'FAILED'}</strong> - {formatDate(attempt.at)}
                </p>
                <p>
                  method=<span className="mono">{attempt.method}</span> path=
                  <span className="mono">{attempt.path}</span> status={attempt.status_code}
                </p>
                <pre className="payload-view">{JSON.stringify(attempt.payload, null, 2)}</pre>
                {attempt.error ? <p className="error-inline">error={attempt.error}</p> : null}
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
