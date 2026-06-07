import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { logout } from '../api/auth.js'

const MENU_ITEMS = {
  cliente: [
    { icon: '🏪', label: 'Catalogos', path: '/catalog' },
    { icon: '🛒', label: 'Mi Carrito', path: '/carrito' },
    { icon: '📦', label: 'Mis Pedidos', path: '/mis-pedidos' },
    { icon: '⭐', label: 'Calificar', path: '/calificar' },
  ],
  establecimiento: [
    { icon: '🍽️', label: 'Mi Catalogo', path: '/establishment/catalog' },
    { icon: '📋', label: 'Pedidos', path: '/establishment/pedidos' },
  ],
  repartidor: [
    { icon: '🟢', label: 'Dashboard', path: '/delivery/dashboard' },
  ],
  admin: [
    { icon: '🔌', label: 'Sistema', path: '/admin/system' },
    { icon: '📊', label: 'Analytics', path: '/admin/analytics' },
  ],
}

export default function Layout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  let session = null
  try { session = JSON.parse(localStorage.getItem('session') || 'null') } catch {}
  const user = session?.user

  const menuItems = user ? (MENU_ITEMS[user.rol] || []) : []

  const handleLogout = async () => {
    try { await logout() } catch {}
    localStorage.removeItem('session')
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-surface overflow-hidden">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-sidebar border-r border-gray-700 flex flex-col transition-all duration-200`}>
        {/* Logo */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <span className="text-rappi text-2xl font-black">rappi</span>
            {sidebarOpen && (
              <div>
                <div className="text-gray-400 text-xs">Logistics</div>
                <div className="text-gray-500 text-[10px]">OPERATIONAL CONTROL</div>
              </div>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const active = location.pathname === item.path
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-rappi text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <span className="text-base">{item.icon}</span>
                {sidebarOpen && <span>{item.label}</span>}
              </button>
            )
          })}
        </nav>

        {/* User + Logout */}
        <div className="p-4 border-t border-gray-700">
          {sidebarOpen && user && (
            <div className="mb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-rappi rounded-full flex items-center justify-center text-white text-sm font-bold">
                  {(user.nombre || 'U')[0].toUpperCase()}
                </div>
                <div>
                  <div className="text-white text-sm font-semibold truncate max-w-[140px]">{user.nombre}</div>
                  <div className="text-gray-400 text-xs capitalize">{user.rol}</div>
                </div>
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <span>🚪</span>
            {sidebarOpen && <span>Cerrar sesion</span>}
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Navbar */}
        <header className="bg-sidebar border-b border-gray-700 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              ☰
            </button>
            <div className="relative">
              <input
                type="text"
                placeholder="Buscar..."
                className="bg-gray-700 text-gray-200 pl-9 pr-4 py-1.5 rounded-lg text-sm border border-gray-600 focus:outline-none focus:border-rappi w-64"
              />
              <span className="absolute left-3 top-2 text-gray-400 text-sm">🔍</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="text-gray-400 hover:text-white text-xl">🔔</button>
            <button className="text-gray-400 hover:text-white text-xl">❓</button>
            {user && (
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-rappi rounded-full flex items-center justify-center text-white text-sm font-bold">
                  {(user.nombre || 'U')[0].toUpperCase()}
                </div>
                <div>
                  <div className="text-white text-sm font-semibold">{user.nombre}</div>
                  <div className="text-gray-400 text-xs capitalize">{user.rol}</div>
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
