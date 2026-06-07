import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import { getPedidosCalificar, calificarPedido } from '../../api/cliente.js'

function StarRating({ value, onChange }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map(star => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          className={`text-2xl transition-transform hover:scale-110 ${star <= value ? 'text-yellow-400' : 'text-gray-600'}`}
        >
          ★
        </button>
      ))}
    </div>
  )
}

export default function Calificar() {
  const [pedidos, setPedidos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [califs, setCalifs] = useState({})

  useEffect(() => {
    getPedidosCalificar()
      .then(data => {
        setPedidos(data)
        const init = {}
        data.forEach(p => {
          init[p.id_pedido] = {
            puntaje_est: 5, comentario_est: '',
            puntaje_rep: p.id_repartidor ? 5 : null, comentario_rep: '',
          }
        })
        setCalifs(init)
      })
      .catch(() => setError('Error cargando pedidos'))
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (pedido) => {
    const c = califs[pedido.id_pedido]
    try {
      await calificarPedido({
        id_pedido: pedido.id_pedido,
        puntaje_establecimiento: c.puntaje_est,
        comentario_est: c.comentario_est || null,
        puntaje_repartidor: pedido.id_repartidor ? c.puntaje_rep : null,
        comentario_rep: pedido.id_repartidor ? c.comentario_rep : null,
      })
      setSuccess(`Calificacion guardada para pedido #${pedido.id_pedido}`)
      setPedidos(prev => prev.filter(p => p.id_pedido !== pedido.id_pedido))
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al calificar')
      setTimeout(() => setError(''), 4000)
    }
  }

  const updateCalif = (id_pedido, field, value) => {
    setCalifs(prev => ({ ...prev, [id_pedido]: { ...prev[id_pedido], [field]: value } }))
  }

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-white mb-6">Calificar Pedidos</h1>
      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {success && <div className="bg-green-900/50 border border-green-700 text-green-300 px-4 py-3 rounded-lg mb-4 text-sm">{success}</div>}

      {loading ? (
        <div className="text-gray-400">Cargando...</div>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-5xl mb-4">🎉</div>
          <div className="text-white font-bold text-lg mb-2">Ya calificaste todos tus pedidos</div>
          <div className="text-gray-400 text-sm">No hay pedidos entregados pendientes de calificacion.</div>
        </div>
      ) : (
        <div className="space-y-4">
          {pedidos.map(pedido => {
            const c = califs[pedido.id_pedido] || {}
            return (
              <div key={pedido.id_pedido} className="bg-sidebar border border-gray-700 rounded-xl p-6 space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-white font-bold">Pedido #{pedido.id_pedido}</div>
                    <div className="text-gray-400 text-sm">{new Date(pedido.fecha_hora).toLocaleDateString('es-AR')}</div>
                  </div>
                </div>

                {/* Establecimiento rating */}
                <div className="border-t border-gray-700 pt-4">
                  <div className="text-white font-semibold mb-1">🍽️ {pedido.establecimiento}</div>
                  <StarRating value={c.puntaje_est || 5} onChange={v => updateCalif(pedido.id_pedido, 'puntaje_est', v)} />
                  <textarea
                    placeholder="Comentario opcional..."
                    value={c.comentario_est || ''}
                    onChange={e => updateCalif(pedido.id_pedido, 'comentario_est', e.target.value)}
                    className="mt-2 w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi resize-none h-16"
                  />
                </div>

                {/* Repartidor rating */}
                {pedido.id_repartidor && (
                  <div className="border-t border-gray-700 pt-4">
                    <div className="text-white font-semibold mb-1">🛵 {pedido.repartidor}</div>
                    <StarRating value={c.puntaje_rep || 5} onChange={v => updateCalif(pedido.id_pedido, 'puntaje_rep', v)} />
                    <textarea
                      placeholder="Comentario opcional..."
                      value={c.comentario_rep || ''}
                      onChange={e => updateCalif(pedido.id_pedido, 'comentario_rep', e.target.value)}
                      className="mt-2 w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi resize-none h-16"
                    />
                  </div>
                )}

                <button
                  onClick={() => handleSubmit(pedido)}
                  className="bg-rappi hover:bg-rappi-dark text-white px-6 py-2.5 rounded-lg text-sm font-bold transition-colors"
                >
                  Guardar calificacion
                </button>
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}
