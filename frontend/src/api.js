async function request(method, url, body, isForm = false) {
  const opts = { method, credentials: 'same-origin' }
  if (body !== undefined) {
    if (isForm) {
      opts.body = body
    } else {
      opts.headers = { 'Content-Type': 'application/json' }
      opts.body = JSON.stringify(body)
    }
  }
  const res = await fetch(url, opts)
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(data.detail || `요청 실패 (${res.status})`)
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  me: () => request('GET', '/api/me'),
  login: (password) => request('POST', '/api/login', { password }),
  logout: () => request('POST', '/api/logout'),
  list: () => request('GET', '/api/items'),
  upload: (file, title, category) => {
    const fd = new FormData()
    fd.append('file', file)
    if (title) fd.append('title', title)
    if (category) fd.append('category', category)
    return request('POST', '/api/items', fd, true)
  },
  patch: (slug, body) => request('PATCH', `/api/items/${encodeURIComponent(slug)}`, body),
  remove: (slug) => request('DELETE', `/api/items/${encodeURIComponent(slug)}`),
  reorder: (slugs) => request('PUT', '/api/items/order', { slugs }),
}
