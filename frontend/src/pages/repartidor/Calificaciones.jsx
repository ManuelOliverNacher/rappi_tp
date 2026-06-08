import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import { getCalificacionesRep } from '../../api/repartidor.js'

function Stars({ n }) {
  const value = Math.round(n || 0)
  return (
    <span className="text-yellow-400 text-sm">
      {'★'.repeat(value)}{'☆'.repeat(Math.max(0, 5 - value))}
      <span className="text-gray-400 ml-1">({n ?? '-'})</span>
    </span>
  )
}

export default function CalificacionesRep() {
  const [calificaciones, setCalificaciones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getCalificacionesRep()
      .then(setCalificaciones)
      .catch(() => setError('Error cargando calificaciones'))
      .finally(() => setLoading(false))
  }, [])

  const promedio = calificaciones.length
    ? (calificaciones.reduce((s, c) => s + (c.puntaje || 0), 0) / calificaciones.length).toFixed(1)
    : null

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Mis Calificaciones</h1>
        {promedio && (
          <div className="bg-sidebar border border-gray-700 rounded-xl px-5 py-3 text-center">
            <div className="text-3xl font-black text-yellow-400">{promedio}</div>
            <div className="text-gray-400 text-xs mt-0.5">{calificaciones.length} resena{calificaciones.length !== 1 ? 's' : ''}</div>
          </div>
        )}
      </div>

      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {loading ? (
        <div className="text-gray-400">Cargando calificaciones...</div>
      ) : calificaciones.length === 0 ? (
        <div className="text-gray-400 text-center py-16">Todavia no recibiste calificaciones.</div>
      ) : (
        <div className="space-y-4">
          {calificaciones.map(c => (
            <div key={c.id} className="bg-sidebar border border-gray-700 rounded-xl p-5">
              <div className="mb-2">
                <Stars n={c.puntaje} />
                <div className="text-gray-500 text-xs mt-1">
                  {c.nombre_cliente} &nbsp;·&nbsp;
                  {c.fecha ? new Date(c.fecha).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                </div>
              </div>
              {c.comentario && (
                <p className="text-gray-300 text-sm italic">"{c.comentario}"</p>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}
