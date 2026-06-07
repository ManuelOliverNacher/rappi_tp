import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import Badge from '../../components/Badge.jsx'
import { getMisPedidos, getEstadosPedido } from '../../api/cliente.js'

export default function MisPedidos() {
  const [pedidos, setPedidos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(null)
  const [estados, setEstados] = useState({})
  const [loadingEstados, setLoadingEstados] = useState({})

  useEffect(() => {
    getMisPedidos()
      .then(setPedidos)
      .catch(() => setError('Error cargando pedidos'))
      .finally(() => setLoading(false))
  }, [])

  const handleExpand = async (id_pedido) => {
    if (expanded === id_pedido) { setExpanded(null); return }
    setExpanded(id_pedido)
    if (estados[id_pedido]) return
    setLoadingEstados(p => ({ ...p, [id_pedido]: true }))
    try {
      const rows = await getEstadosPedido(id_pedido)
      setEstados(p => ({ ...p, [id_pedido]: rows }))
    } catch {}
    setLoadingEstados(p => ({ ...p, [id_pedido]: false }))
  }

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-white mb-6">Mis Pedidos</h1>
      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {loading ? (
        <div className="text-gray-400">Cargando pedidos...</div>
      ) : pedidos.length === 0 ? (
        <div className="text-gray-400 text-center py-20">Todavia no realizaste ningun pedido.</div>
      ) : (
        <div className="bg-sidebar border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">#</th>
                <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Establecimiento</th>
                <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Fecha</th>
                <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Total</th>
                <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Estado</th>
                <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {pedidos.map(p => (
                <React.Fragment key={p.id_pedido}>
                  <tr className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3 text-gray-300 text-sm font-mono">#{p.id_pedido}</td>
                    <td className="px-4 py-3 text-white text-sm font-medium">{p.establecimiento}</td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {new Date(p.fecha_hora).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-3 text-rappi font-bold text-sm">${parseFloat(p.total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
                    <td className="px-4 py-3"><Badge estado={p.estado} /></td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleExpand(p.id_pedido)}
                        className="text-blue-400 hover:text-blue-300 text-xs border border-blue-700 px-3 py-1 rounded-lg transition-colors"
                      >
                        {expanded === p.id_pedido ? 'Ocultar' : 'Ver estados'}
                      </button>
                    </td>
                  </tr>
                  {expanded === p.id_pedido && (
                    <tr className="bg-gray-800/50">
                      <td colSpan={6} className="px-6 py-4">
                        {loadingEstados[p.id_pedido] ? (
                          <div className="text-gray-400 text-sm">Cargando historial de Cassandra...</div>
                        ) : (estados[p.id_pedido] || []).length === 0 ? (
                          <div className="text-gray-500 text-sm">Sin historial de estados.</div>
                        ) : (
                          <div className="space-y-2">
                            <div className="text-gray-500 text-xs mb-2 uppercase tracking-wider">Historial (Cassandra)</div>
                            {(estados[p.id_pedido] || []).map((e, i) => (
                              <div key={i} className="flex items-center gap-3 text-sm">
                                <span className="text-gray-500 font-mono text-xs w-32">
                                  {e.fecha_hora ? new Date(e.fecha_hora).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                                </span>
                                <span className="text-gray-400">→</span>
                                <Badge estado={e.estado} />
                                {e.observacion && <span className="text-gray-500 text-xs">— {e.observacion}</span>}
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  )
}
