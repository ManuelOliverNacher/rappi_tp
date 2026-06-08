import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import Badge from '../../components/Badge.jsx'
import { getEstadoRepartidor, marcarDisponible, marcarOcupado, getPedidosRepartidor, tomarPedido, actualizarEstadoEntrega } from '../../api/repartidor.js'

const ESTADOS_ENTREGA = ['repartidor_asignado', 'en_camino', 'entregado']

export default function Dashboard() {
  const [estado, setEstado] = useState(null)
  const [pedidos, setPedidos] = useState({ asignados: [], disponibles: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [estadosEntrega, setEstadosEntrega] = useState({})
  const [observaciones, setObservaciones] = useState({})
  const [updating, setUpdating] = useState({})

  const fetchData = () => {
    Promise.all([getEstadoRepartidor(), getPedidosRepartidor()])
      .then(([e, p]) => {
        setEstado(e)
        setPedidos(p)
        const init = {}
        p.asignados.forEach(ped => { init[ped.id_pedido] = ped.estado || 'en_camino' })
        setEstadosEntrega(init)
      })
      .catch(() => setError('Error cargando datos'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  const handleDisponible = async () => {
    try {
      await marcarDisponible()
      setSuccess('Ahora estas disponible')
      fetchData()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) { setError(err.response?.data?.detail || 'Error') }
  }

  const handleOcupado = async () => {
    try {
      await marcarOcupado()
      setSuccess('Marcado como no disponible')
      fetchData()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) { setError(err.response?.data?.detail || 'Error') }
  }

  const handleTomar = async (id_pedido) => {
    setUpdating(p => ({ ...p, [`tomar_${id_pedido}`]: true }))
    try {
      await tomarPedido(id_pedido)
      setSuccess(`Pedido #${id_pedido} tomado`)
      fetchData()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al tomar pedido')
      setTimeout(() => setError(''), 4000)
    } finally {
      setUpdating(p => ({ ...p, [`tomar_${id_pedido}`]: false }))
    }
  }

  const handleActualizar = async (id_pedido) => {
    const estadoSel = estadosEntrega[id_pedido] || 'en_camino'
    setUpdating(p => ({ ...p, [id_pedido]: true }))
    try {
      await actualizarEstadoEntrega(id_pedido, estadoSel, observaciones[id_pedido] || null)
      setSuccess(`Pedido #${id_pedido} → ${estadoSel}`)
      fetchData()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error actualizando estado')
    } finally {
      setUpdating(p => ({ ...p, [id_pedido]: false }))
    }
  }

  if (loading) return <Layout><div className="text-gray-400">Cargando...</div></Layout>

  const disponible = estado?.disponible

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-white mb-6">Dashboard Repartidor</h1>
      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {success && <div className="bg-green-900/50 border border-green-700 text-green-300 px-4 py-3 rounded-lg mb-4 text-sm">{success}</div>}

      {/* Status card */}
      <div className="bg-sidebar border border-gray-700 rounded-xl p-6 mb-6">
        <h2 className="text-white font-bold text-lg mb-4">Estado Operacional</h2>
        <div className="flex items-center gap-6">
          <div className={`w-4 h-4 rounded-full ${disponible ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
          <span className={`text-2xl font-black ${disponible ? 'text-green-400' : 'text-red-400'}`}>
            {disponible ? 'DISPONIBLE' : 'OCUPADO'}
          </span>
          <div className="flex gap-3 ml-auto">
            <button
              onClick={handleDisponible}
              disabled={disponible}
              className="bg-green-600 hover:bg-green-500 text-white px-5 py-2.5 rounded-lg text-sm font-bold disabled:opacity-40 transition-colors"
            >
              Marcar disponible
            </button>
            <button
              onClick={handleOcupado}
              disabled={!disponible}
              className="bg-red-700 hover:bg-red-600 text-white px-5 py-2.5 rounded-lg text-sm font-bold disabled:opacity-40 transition-colors"
            >
              Marcar ocupado
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 mt-5">
          <div className="bg-gray-700/50 rounded-lg p-3">
            <div className="text-gray-400 text-xs">Repartidores disponibles (Redis)</div>
            <div className="text-green-400 text-xl font-bold">{estado?.disponibles_redis ?? '—'}</div>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-3">
            <div className="text-gray-400 text-xs">Repartidores ocupados (Redis)</div>
            <div className="text-red-400 text-xl font-bold">{estado?.ocupados_redis ?? '—'}</div>
          </div>
        </div>
      </div>

      {/* Mis pedidos asignados */}
      <div className="mb-6">
        <h2 className="text-white font-bold text-lg mb-3">Mis pedidos asignados ({pedidos.asignados.length})</h2>
        {pedidos.asignados.length === 0 ? (
          <div className="text-gray-500 text-sm">No tienes pedidos asignados.</div>
        ) : (
          <div className="space-y-3">
            {pedidos.asignados.map(p => (
              <div key={p.id_pedido} className="bg-sidebar border border-gray-700 rounded-xl p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-white font-bold">#{p.id_pedido}</span>
                      <Badge estado={p.estado} />
                    </div>
                    <div className="text-gray-400 text-sm">{p.establecimiento} · Cliente: {p.cliente}</div>
                    {p.direccion && <div className="text-gray-500 text-xs mt-0.5">📍 {p.direccion}</div>}
                    <div className="text-rappi font-bold text-sm mt-1">${parseFloat(p.total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</div>
                    {p.estado === 'entregado' && p.observacion && (
                      <div className="text-gray-400 text-xs mt-1 italic">Obs: {p.observacion}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <select
                      value={estadosEntrega[p.id_pedido] || p.estado || 'en_camino'}
                      onChange={e => setEstadosEntrega(prev => ({ ...prev, [p.id_pedido]: e.target.value }))}
                      className="bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none"
                    >
                      {ESTADOS_ENTREGA.map(s => <option key={s} value={s}>{s.replace(/_/g, ' ').toUpperCase()}</option>)}
                    </select>
                    <input
                      placeholder="Observacion..."
                      value={observaciones[p.id_pedido] || ''}
                      onChange={e => setObservaciones(prev => ({ ...prev, [p.id_pedido]: e.target.value }))}
                      className="bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none w-32"
                    />
                    <button
                      onClick={() => handleActualizar(p.id_pedido)}
                      disabled={updating[p.id_pedido]}
                      className="bg-rappi hover:bg-rappi-dark text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-60"
                    >
                      {updating[p.id_pedido] ? '...' : 'Actualizar'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pedidos disponibles */}
      <div>
        <h2 className="text-white font-bold text-lg mb-3">Pedidos disponibles para tomar ({pedidos.disponibles.length})</h2>
        {pedidos.disponibles.length === 0 ? (
          <div className="text-gray-500 text-sm">No hay pedidos listos para retirar en este momento.</div>
        ) : (
          <div className="space-y-3">
            {pedidos.disponibles.map(p => (
              <div key={p.id_pedido} className="bg-sidebar border border-green-700/50 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-white font-bold">#{p.id_pedido}</span>
                    <Badge estado={p.estado} />
                  </div>
                  <div className="text-gray-400 text-sm">{p.establecimiento}</div>
                  <div className="text-rappi font-bold text-sm">${parseFloat(p.total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</div>
                </div>
                <button
                  onClick={() => handleTomar(p.id_pedido)}
                  disabled={updating[`tomar_${p.id_pedido}`]}
                  className="bg-green-600 hover:bg-green-500 text-white px-5 py-2.5 rounded-lg text-sm font-bold transition-colors disabled:opacity-60"
                >
                  {updating[`tomar_${p.id_pedido}`] ? 'Tomando...' : '🛵 Tomar pedido'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
