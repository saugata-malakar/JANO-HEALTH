/**
 * API client for the HireSense backend.
 *
 * Uses Clerk's getToken() to attach a JWT to every request. In bypass mode
 * (VITE_BYPASS_AUTH=true) we send the request without a token and let the
 * backend's DEV_BYPASS_AUTH flag accept it.
 */

const BASE = import.meta.env.VITE_API_BASE_URL || ''
const BYPASS = import.meta.env.VITE_BYPASS_AUTH === 'true'

class ApiError extends Error {
  constructor(status, message, payload) {
    super(message)
    this.status = status
    this.payload = payload
  }
}

async function request(path, { method = 'GET', body, headers = {}, getToken } = {}) {
  const finalHeaders = { ...headers }
  let finalBody = body

  if (body && !(body instanceof FormData)) {
    finalHeaders['Content-Type'] = 'application/json'
    finalBody = JSON.stringify(body)
  }

  if (!BYPASS && getToken) {
    try {
      const token = await getToken()
      if (token) finalHeaders['Authorization'] = `Bearer ${token}`
    } catch (e) {
      // No active session — let the backend respond with 401
    }
  }

  const resp = await fetch(`${BASE}${path}`, { method, headers: finalHeaders, body: finalBody })

  if (!resp.ok) {
    let detail = `Request failed with status ${resp.status}`
    let payload
    try {
      payload = await resp.json()
      if (payload?.detail) detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail)
    } catch (_) {
      // not JSON
    }
    throw new ApiError(resp.status, detail, payload)
  }
  return resp.json()
}

export const api = {
  health: () => request('/health'),
  config: () => request('/config'),
  sampleJD: () => request('/api/demo/sample-jd'),
  sampleEvaluation: () => request('/api/demo/sample-evaluation'),

  parse: (file, { getToken } = {}) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/api/parse', { method: 'POST', body: fd, getToken })
  },

  evaluateFile: ({ file, jd, verify = true, generate_questions = true }, { getToken } = {}) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('jd', JSON.stringify(jd))
    fd.append('verify', String(verify))
    fd.append('generate_questions', String(generate_questions))
    return request('/api/evaluate/file', { method: 'POST', body: fd, getToken })
  },

  evaluateBatch: ({ files, jd, verify = true, generate_questions = false }, { getToken } = {}) => {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    fd.append('jd', JSON.stringify(jd))
    fd.append('verify', String(verify))
    fd.append('generate_questions', String(generate_questions))
    return request('/api/evaluate/batch', { method: 'POST', body: fd, getToken })
  },

  evaluateText: (body, { getToken } = {}) =>
    request('/api/evaluate/text', { method: 'POST', body, getToken }),

  generateInterview: (body, { getToken } = {}) =>
    request('/api/interview', { method: 'POST', body, getToken }),
}

export { ApiError }
