import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Catalog from './pages/cliente/Catalog.jsx'
import Cart from './pages/cliente/Cart.jsx'
import Checkout from './pages/cliente/Checkout.jsx'
import MisPedidos from './pages/cliente/MisPedidos.jsx'
import Calificar from './pages/cliente/Calificar.jsx'
import MiCatalogo from './pages/establecimiento/MiCatalogo.jsx'
import PedidosEst from './pages/establecimiento/Pedidos.jsx'
import PedidosPendientes from './pages/establecimiento/PedidosPendientes.jsx'
import Calificaciones from './pages/establecimiento/Calificaciones.jsx'
import Promociones from './pages/establecimiento/Promociones.jsx'
import Dashboard from './pages/repartidor/Dashboard.jsx'
import CalificacionesRep from './pages/repartidor/Calificaciones.jsx'
import System from './pages/admin/System.jsx'
import Analytics from './pages/admin/Analytics.jsx'

const ROL_HOME = {
  cliente: '/catalog',
  establecimiento: '/establishment/catalog',
  repartidor: '/delivery/dashboard',
  admin: '/admin/system',
}

function ProtectedRoute({ children, rol }) {
  let session = null
  try { session = JSON.parse(localStorage.getItem('session') || 'null') } catch {}
  if (!session) return <Navigate to="/login" replace />
  if (rol && session.user?.rol !== rol) {
    const home = ROL_HOME[session.user?.rol] || '/login'
    return <Navigate to={home} replace />
  }
  return children
}

export default function Router() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/catalog" element={<ProtectedRoute rol="cliente"><Catalog /></ProtectedRoute>} />
      <Route path="/carrito" element={<ProtectedRoute rol="cliente"><Cart /></ProtectedRoute>} />
      <Route path="/checkout" element={<ProtectedRoute rol="cliente"><Checkout /></ProtectedRoute>} />
      <Route path="/mis-pedidos" element={<ProtectedRoute rol="cliente"><MisPedidos /></ProtectedRoute>} />
      <Route path="/calificar" element={<ProtectedRoute rol="cliente"><Calificar /></ProtectedRoute>} />
      <Route path="/establishment/catalog" element={<ProtectedRoute rol="establecimiento"><MiCatalogo /></ProtectedRoute>} />
      <Route path="/establishment/pedidos" element={<ProtectedRoute rol="establecimiento"><PedidosEst /></ProtectedRoute>} />
      <Route path="/establishment/pendientes" element={<ProtectedRoute rol="establecimiento"><PedidosPendientes /></ProtectedRoute>} />
      <Route path="/establishment/calificaciones" element={<ProtectedRoute rol="establecimiento"><Calificaciones /></ProtectedRoute>} />
      <Route path="/establishment/promociones" element={<ProtectedRoute rol="establecimiento"><Promociones /></ProtectedRoute>} />
      <Route path="/delivery/dashboard" element={<ProtectedRoute rol="repartidor"><Dashboard /></ProtectedRoute>} />
      <Route path="/delivery/calificaciones" element={<ProtectedRoute rol="repartidor"><CalificacionesRep /></ProtectedRoute>} />
      <Route path="/admin/system" element={<ProtectedRoute rol="admin"><System /></ProtectedRoute>} />
      <Route path="/admin/analytics" element={<ProtectedRoute rol="admin"><Analytics /></ProtectedRoute>} />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
