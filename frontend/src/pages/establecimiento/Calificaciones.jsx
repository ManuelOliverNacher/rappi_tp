import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import { getCalificacionesEst, responderCalificacion } from '../../api/establecimiento.js'

function Stars({ n }) {
  const value = Math.round(n || 0)
  return (
    <span className="text-yellow-400 text-sm">
      {'★'.repeat(value)}{'☆'.repeat(Math.max(0, 5 - value))}
      <span className="text-gray-400 ml-1">({n ?? '-'})</span>
    </span>
  )
}

export default function Calificaciones() {
  const [calificaciones, setCalificaciones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [respuestas, setRespuestas] = useState({})
  const [sending, setSending] = useState({})
  const [editando, setEditando] = useState({})

  useEffect(() => {
    getCalificacionesEst()
      .then(setCalificaciones)
      .catch(() => setError('Error cargando calificaciones'))
      .finally(() => setLoading(false))
  }, [])

  const handleResponder = async (id) => {
    if (!respuestas[id]?.trim()) return
    setSending(p => ({ ...p, [id]: true }))
    try {
      await responderCalificacion(id, respuestas[id].trim())
      setCalificaciones(prev =>
        prev.map(c => c.id === id ? { ...c, respuesta: respuestas[id].trim() } : c)
      )
      setSuccess('Respuesta enviada')
      setEditando(p => ({ ...p, [id]: false }))
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al enviar respuesta')
      setTimeout(() => setError(''), 4000)
    } finally {
      setSending(p => ({ ...p, [id]: false }))
    }
  }

  const promedio = calificaciones.length
    ? (calificaciones.reduce((s, c) => s + (c.puntaje || 0), 0) / calificaciones.length).toFixed(1)
    : null

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Calificaciones Recibidas</h1>
        {promedio && (
          <div className="bg-sidebar border border-gray-700 rounded-xl px-5 py-3 text-center">
            <div className="text-3xl font-black text-yellow-400">{promedio}</div>
            <div className="text-gray-400 text-xs mt-0.5">{calificaciones.length} resena{calificaciones.length !== 1 ? 's' : ''}</div>
          </div>
        )}
      </div>

      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {success && <div className="bg-green-900/50 border border-green-700 text-green-300 px-4 py-3 rounded-lg mb-4 text-sm">{success}</div>}

      {loading ? (
        <div className="text-gray-400">Cargando calificaciones...</div>
      ) : calificaciones.length === 0 ? (
        <div className="text-gray-400 text-center py-16">Todavia no recibiste calificaciones.</div>
      ) : (
        <div className="space-y-4">
          {calificaciones.map(c => (
            <div key={c.id} className="bg-sidebar border border-gray-700 rounded-xl p-5">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <Stars n={c.puntaje} />
                  <div className="text-gray-500 text-xs mt-1">
                    {c.nombre_cliente} &nbsp;·&nbsp;
                    {c.fecha ? new Date(c.fecha).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                  </div>
                </div>
              </div>

              {c.comentario && (
                <p className="text-gray-300 text-sm mb-3 italic">"{c.comentario}"</p>
              )}

              {c.respuesta && !editando[c.id] ? (
                <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 mt-2">
                  <div className="text-xs text-gray-500 mb-1">Tu respuesta:</div>
                  <p className="text-gray-300 text-sm">{c.respuesta}</p>
                  <button
                    onClick={() => {
                      setRespuestas(p => ({ ...p, [c.id]: c.respuesta }))
                      setEditando(p => ({ ...p, [c.id]: true }))
                    }}
                    className="text-xs text-rappi hover:underline mt-2"
                  >
                    Editar respuesta
                  </button>
                </div>
              ) : (
                <div className="mt-2 flex gap-2">
                  <input
                    placeholder="Responder a esta resena..."
                    value={respuestas[c.id] || ''}
                    onChange={e => setRespuestas(prev => ({ ...prev, [c.id]: e.target.value }))}
                    className="flex-1 bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi"
                  />
                  <button
                    onClick={() => handleResponder(c.id)}
                    disabled={sending[c.id] || !respuestas[c.id]?.trim()}
                    className="bg-rappi hover:bg-rappi-dark text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-60"
                  >
                    {sending[c.id] ? '...' : 'Responder'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}
