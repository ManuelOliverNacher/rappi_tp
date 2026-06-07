import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth.js'

const ROLES = [
  { id: 'cliente', label: 'Cliente', icon: '👤' },
  { id: 'establecimiento', label: 'Establecimiento', icon: '🏪' },
  { id: 'repartidor', label: 'Repartidor', icon: '🛵' },
  { id: 'admin', label: 'Admin', icon: '⚙️' },
]

const REDIRECTS = {
  cliente: '/catalog',
  establecimiento: '/establishment/catalog',
  repartidor: '/delivery/dashboard',
  admin: '/admin/system',
}

export default function Login() {
  const navigate = useNavigate()
  const [rol, setRol] = useState('cliente')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) { setError('Completa todos los campos'); return }
    setLoading(true)
    setError('')
    try {
      const data = await login(email, password, rol)
      localStorage.setItem('session', JSON.stringify(data))
      navigate(REDIRECTS[data.user.rol] || '/login')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar sesion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{
        background: '#111827',
        backgroundImage: 'radial-gradient(circle, #374151 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }}
    >
      <div className="bg-white text-gray-800 rounded-xl shadow-2xl p-8 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-6">
          <div className="text-5xl font-black text-rappi tracking-tight">rappi</div>
          <div className="text-gray-500 text-sm font-medium">Logistics</div>
          <div className="text-gray-400 text-xs mt-1">Control Operativo Unificado</div>
        </div>

        {/* Role selector */}
        <div className="grid grid-cols-2 gap-2 mb-6">
          {ROLES.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => setRol(r.id)}
              className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border-2 text-sm font-semibold transition-all ${
                rol === r.id
                  ? 'bg-rappi text-white border-rappi'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-rappi hover:text-rappi'
              }`}
            >
              <span className="text-lg">{r.icon}</span>
              {r.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div className="relative">
            <span className="absolute left-3 top-3 text-gray-400">✉️</span>
            <input
              type="text"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder={rol === 'admin' ? 'admin' : 'correo@ejemplo.com'}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-rappi bg-white"
            />
          </div>

          {/* Password */}
          <div className="relative">
            <span className="absolute left-3 top-3 text-gray-400">🔒</span>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Contrasena"
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-rappi bg-white"
            />
          </div>

          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 text-gray-600 cursor-pointer">
              <input type="checkbox" className="rounded" />
              Mantener sesion iniciada
            </label>
            <span className="text-rappi cursor-pointer hover:underline text-xs">
              Olvide mi contrasena
            </span>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-rappi hover:bg-rappi-dark text-white font-bold py-3 rounded-lg transition-colors disabled:opacity-60"
          >
            {loading ? 'Ingresando...' : 'Entrar'}
          </button>
        </form>

        <div className="text-center mt-4 text-sm text-gray-500">
          No tienes cuenta?{' '}
          <span className="text-rappi cursor-pointer hover:underline">Solicita acceso</span>
        </div>

        {/* Test users info */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 font-semibold mb-1">Usuarios de prueba (pwd: test123)</div>
          <div className="text-xs text-gray-500">
            Cliente: manu@test.com · Establecimiento: sushi@test.com · Repartidor: juan@test.com
          </div>
          <div className="text-xs text-gray-500 mt-1">Admin: usuario <strong>admin</strong> / pwd <strong>admin1234</strong></div>
        </div>

        {/* Feature badges */}
        <div className="flex justify-center gap-3 mt-5">
          {['🔒 Seguro', '⚡ Rapido', '🌎 Global'].map(b => (
            <span key={b} className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-full font-medium">
              {b}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
