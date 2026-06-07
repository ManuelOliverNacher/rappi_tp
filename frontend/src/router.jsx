import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Catalog from './pages/cliente/Catalog.jsx'
import Cart from './pages/cliente/Cart.jsx'
import Checkout from './pages/cliente/Checkout.jsx'
import MisPedidos from './pages/cliente/MisPedidos.jsx'
import Calificar from './pages/cliente/Calificar.jsx'
import MiCatalogo from './pages/establecimiento/MiCatalogo.jsx'
import PedidosEst from './pages/establecimiento/Pedidos.jsx'
import Dashboard from './pages/repartidor/Dashboard.jsx'
import System from './pages/admin/System.jsx'
import Analytics from './pages/admin/Analytics.jsx'

function ProtectedRoute({ children }) {
  const session = localStorage.getItem('session')
  if (!session) return <Navigate to="/login" replace />
  return children
}

export default function Router() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/catalog" element={<ProtectedRoute><Catalog /></ProtectedRoute>} />
      <Route path="/carrito" element={<ProtectedRoute><Cart /></ProtectedRoute>} />
      <Route path="/checkout" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
      <Route path="/mis-pedidos" element={<ProtectedRoute><MisPedidos /></ProtectedRoute>} />
      <Route path="/calificar" element={<ProtectedRoute><Calificar /></ProtectedRoute>} />
      <Route path="/establishment/catalog" element={<ProtectedRoute><MiCatalogo /></ProtectedRoute>} />
      <Route path="/establishment/pedidos" element={<ProtectedRoute><PedidosEst /></ProtectedRoute>} />
      <Route path="/delivery/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/admin/system" element={<ProtectedRoute><System /></ProtectedRoute>} />
      <Route path="/admin/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
