const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const token = getToken()
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({ detail: 'Unexpected server error' }))
  if (!res.ok) throw new Error(data.detail || 'Request failed')
  return data
}

export const api = {
  get:    (path)        => request(path),
  post:   (path, body)  => request(path, { method: 'POST', body: JSON.stringify(body) }),
  delete: (path)        => request(path, { method: 'DELETE' }),

  // For OAuth2PasswordRequestForm (login)
  postForm: (path, fields) =>
    fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(fields).toString(),
    }).then(async (res) => {
      const data = await res.json().catch(() => ({ detail: 'Unexpected server error' }))
      if (!res.ok) throw new Error(data.detail || 'Request failed')
      return data
    }),
}
