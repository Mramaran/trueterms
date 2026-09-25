/**
 * api.js — All API calls to FastAPI backend
 * ==========================================
 * Security: X-API-Key sent on every protected request.
 * NOTE: The VITE_API_SECRET_KEY is visible in the browser bundle.
 * For production, use a backend session/cookie auth instead.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_KEY  = import.meta.env.VITE_API_SECRET_KEY || ''

const MAX_QUERY_LENGTH = 4000  // Hard cap — prevent API abuse

const authHeaders = () => ({
  'Content-Type': 'application/json',
  ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
})

// ── Health Check ──────────────────────────────────────────────────────────────
export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`)
  return res.json()
}

// ── Send Chat Message ─────────────────────────────────────────────────────────
export async function sendChat(query, signal, n_results = 10, system_context = '', file_context = '', language = 'en', history = []) {
  // Hard cap on query length
  const safeQuery = String(query).slice(0, MAX_QUERY_LENGTH)

  // Combine caller's abort signal with a 90-second timeout
  const timeout = AbortSignal.timeout(180_000)
  const combined = AbortSignal.any ? AbortSignal.any([signal, timeout]) : signal

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ query: safeQuery, n_results, system_context, file_context, language, history }),
    signal: combined,
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

// ── Generate Contract ─────────────────────────────────────────────────────────
export async function generateContract(contract_type, with_risk_factor = false, additional_requirements = '') {
  const res = await fetch(`${API_BASE}/generate-contract`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ contract_type, with_risk_factor, additional_requirements }),
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

// ── Run Contract on ACTUS Server ────────────────────────────────────────────
export async function runContract(contractJson) {
  // Wrap single contract object in array if needed
  const payload = Array.isArray(contractJson) ? contractJson : [contractJson]
  const res = await fetch(`${API_BASE}/run-contract`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error: ${res.status}`)
  }
  return res.json()
}

// ── Write File to Filesystem ────────────────────────────────────────────────
export async function writeFile(path, content, mode = 'overwrite') {
  const res = await fetch(`${API_BASE}/write-file`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ path, content, mode }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error: ${res.status}`)
  }
  return res.json()
}

// ── Read File from Filesystem ────────────────────────────────────────────────
export async function readFile(path, allowedPaths = null) {
  const res = await fetch(`${API_BASE}/read-file`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ path, allowed_paths: allowedPaths }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error: ${res.status}`)
  }
  return res.json()
}

// ── Get All Contract Types ────────────────────────────────────────────────────
export async function getContractTypes() {
  const res = await fetch(`${API_BASE}/contract-types`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

// ── TrueTerms: Loan Truth Check ──────────────────────────────────────────────
async function jsonOrThrow(res) {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Server error: ${res.status}`)
  return data
}

// Read a loan offer (English / Tamil / Hindi) → { terms, missing, assumptions, parser }
export async function parseLoanOffer(text, language = 'en') {
  const res = await fetch(`${API_BASE}/loan/parse-offer`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ text: String(text).slice(0, MAX_QUERY_LENGTH), language }),
  })
  return jsonOrThrow(res)
}

// Run the offer on ACTUS → advertised rate vs true APR, EMI, schedule, contract
export async function checkLoanOffer(terms) {
  const res = await fetch(`${API_BASE}/loan/check-offer`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ terms }),
  })
  return jsonOrThrow(res)
}

// Illustrative RBI-format Key Facts Statement → { html, engine, apr_pct }
export async function getLoanKfs(terms, lenderName = null) {
  const res = await fetch(`${API_BASE}/loan/kfs`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ terms, lender_name: lenderName }),
  })
  return jsonOrThrow(res)
}

// Bundled 500-loan demo book (CSV text)
export async function getDemoLoanBook() {
  const res = await fetch(`${API_BASE}/loan/demo-book`, { headers: authHeaders() })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error: ${res.status}`)
  }
  return res.text()
}

// Check a CSV loan book (multipart upload) → { summary, loans }
export async function checkLoanBook(file) {
  // Drop Content-Type so the browser sets the multipart boundary itself
  const { 'Content-Type': _json, ...headers } = authHeaders()
  const form = new FormData()
  form.append('file', file, file.name || 'loan_book.csv')
  const res = await fetch(`${API_BASE}/loan/check-book`, { method: 'POST', headers, body: form })
  return jsonOrThrow(res)
}
