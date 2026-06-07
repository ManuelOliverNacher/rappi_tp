import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const session = localStorage.getItem('session')
  if (session) {
    try {
      const { token } = JSON.parse(session)
      if (token) config.headers['X-Session-Token'] = token
    } catch {}
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('session')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
