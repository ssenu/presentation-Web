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

// 진행률이 필요한 업로드는 XMLHttpRequest 를 쓴다 (fetch 는 업로드 진행 이벤트가 없음).
export function uploadWithProgress(file, onProgress) {
  return new Promise((resolve, reject) => {
    const fd = new FormData()
    fd.append('file', file)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/items')
    xhr.withCredentials = true
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      let data = {}
      try {
        data = JSON.parse(xhr.responseText || '{}')
      } catch {}
      if (xhr.status >= 200 && xhr.status < 300) resolve(data)
      else {
        const err = new Error(data.detail || `요청 실패 (${xhr.status})`)
        err.status = xhr.status
        reject(err)
      }
    }
    xhr.onerror = () => reject(new Error('네트워크 오류로 올리지 못했습니다'))
    xhr.send(fd)
  })
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
  categories: () => request('GET', '/api/categories'),
  addCategory: (name) => request('POST', '/api/categories', { name }),
  removeCategory: (name) => request('DELETE', `/api/categories/${encodeURIComponent(name)}`),
  renameCategory: (name, newName) => request('PATCH', `/api/categories/${encodeURIComponent(name)}`, { name: newName }),
}
