import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import Badge from '../../components/Badge.jsx'
import { getPedidosEst, cambiarEstadoPedido } from '../../api/establecimiento.js'

const ESTADOS_OPCIONES = ['creado', 'aceptado', 'preparando', 'listo_para_retirar', 'repartidor_asignado', 'en_camino', 'entregado', 'cancelado']
const ESTADOS_SOLO_LECTURA = ['repartidor_asignado', 'en_camino', 'entregado', 'cancelado']

export default function Pedidos() {
  const [pedidos, setPedidos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [nuevosEstados, setNuevosEstados] = useState({})
  const [observaciones, setObservaciones] = useState({})
  const [updating, setUpdating] = useState({})

  const loadPedidos = () =>
    getPedidosEst().then(data => {
      setPedidos(data)
      const init = {}
      data.forEach(p => { init[p.id_pedido] = p.estado || 'aceptado' })
      setNuevosEstados(init)
    })

  useEffect(() => {
    loadPedidos()
      .catch(() => setError('Error cargando pedidos'))
      .finally(() => setLoading(false))
  }, [])

  const handleCambiarEstado = async (id_pedido) => {
    setUpdating(p => ({ ...p, [id_pedido]: true }))
    try {
      await cambiarEstadoPedido(id_pedido, nuevosEstados[id_pedido], observaciones[id_pedido] || null)
      setSuccess(`Estado actualizado para pedido #${id_pedido}`)
      loadPedidos().catch(() => {})
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error actualizando estado')
      setTimeout(() => setError(''), 4000)
    } finally {
      setUpdating(p => ({ ...p, [id_pedido]: false }))
    }
  }

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-white mb-6">Pedidos Recibidos</h1>
      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {success && <div className="bg-green-900/50 border border-green-700 text-green-300 px-4 py-3 rounded-lg mb-4 text-sm">{success}</div>}

      {loading ? (
        <div className="text-gray-400">Cargando pedidos...</div>
      ) : pedidos.length === 0 ? (
        <div className="text-gray-400 text-center py-16">No hay pedidos todavia.</div>
      ) : (
        <div className="space-y-3">
          {pedidos.map(p => (
            <div key={p.id_pedido} className="bg-sidebar border border-gray-700 rounded-xl p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-white font-bold">Pedido #{p.id_pedido}</span>
                    <Badge estado={p.estado} />
                  </div>
                  <div className="text-gray-400 text-sm">
                    Cliente: <span className="text-gray-300">{p.cliente}</span> &nbsp;·&nbsp;
                    {new Date(p.fecha_hora).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </div>
                  <div className="text-rappi font-bold mt-1">${parseFloat(p.total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <select
                    value={nuevosEstados[p.id_pedido] || p.estado || 'creado'}
                    onChange={e => setNuevosEstados(prev => ({ ...prev, [p.id_pedido]: e.target.value }))}
                    disabled={ESTADOS_SOLO_LECTURA.includes(p.estado)}
                    className="bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {ESTADOS_OPCIONES.map(s => (
                      <option key={s} value={s}>{s.replace(/_/g, ' ').toUpperCase()}</option>
                    ))}
                  </select>
                  <input
                    placeholder="Observacion..."
                    value={observaciones[p.id_pedido] || ''}
                    onChange={e => setObservaciones(prev => ({ ...prev, [p.id_pedido]: e.target.value }))}
                    className="bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi w-36"
                  />
                  <button
                    onClick={() => handleCambiarEstado(p.id_pedido)}
                    disabled={updating[p.id_pedido] || ESTADOS_SOLO_LECTURA.includes(p.estado)}
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
    </Layout>
  )
}
