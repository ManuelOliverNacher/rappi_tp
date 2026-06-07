import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout.jsx'
import { getEstablecimientos, getCatalogo, agregarAlCarrito } from '../../api/cliente.js'

export default function Catalog() {
  const navigate = useNavigate()
  const [establecimientos, setEstablecimientos] = useState([])
  const [selectedEst, setSelectedEst] = useState(null)
  const [catalogo, setCatalogo] = useState(null)
  const [cantidades, setCantidades] = useState({})
  const [loading, setLoading] = useState(false)
  const [loadingCat, setLoadingCat] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    setLoading(true)
    getEstablecimientos()
      .then(setEstablecimientos)
      .catch(() => setError('Error cargando establecimientos'))
      .finally(() => setLoading(false))
  }, [])

  const handleSelectEst = useCallback((est) => {
    setSelectedEst(est)
    setCatalogo(null)
    setCantidades({})
    setLoadingCat(true)
    getCatalogo(est.id)
      .then(doc => {
        setCatalogo(doc)
        const init = {}
        ;(doc.catalogo || []).forEach(p => { init[p.id_producto] = 1 })
        setCantidades(init)
      })
      .catch(() => setError('Error cargando catalogo'))
      .finally(() => setLoadingCat(false))
  }, [])

  const handleAgregar = async (prod) => {
    if (!selectedEst) return
    try {
      await agregarAlCarrito({
        id_establecimiento: selectedEst.id,
        nombre_establecimiento: selectedEst.nombre,
        id_producto: prod.id_producto,
        nombre: prod.nombre,
        precio: prod.precio,
        cantidad: cantidades[prod.id_producto] || 1,
      })
      setSuccess(`${prod.nombre} agregado al carrito`)
      setTimeout(() => setSuccess(''), 2500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al agregar')
      setTimeout(() => setError(''), 3000)
    }
  }

  const disponibles = (catalogo?.catalogo || []).filter(p => p.disponible !== false)

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Catalogo de Productos</h1>
          <p className="text-gray-400 text-sm mt-1">Selecciona un establecimiento para ver sus productos</p>
        </div>
        <button
          onClick={() => navigate('/carrito')}
          className="bg-rappi hover:bg-rappi-dark text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
        >
          Ver Carrito
        </button>
      </div>

      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {success && <div className="bg-green-900/50 border border-green-700 text-green-300 px-4 py-3 rounded-lg mb-4 text-sm">{success}</div>}

      {/* Establecimiento selector */}
      <div className="mb-6">
        <label className="block text-gray-400 text-sm mb-2">Establecimiento</label>
        {loading ? (
          <div className="text-gray-400 text-sm">Cargando establecimientos...</div>
        ) : (
          <select
            className="bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-rappi w-full max-w-lg"
            value={selectedEst?.id || ''}
            onChange={e => {
              const est = establecimientos.find(x => String(x.id) === e.target.value)
              if (est) handleSelectEst(est)
            }}
          >
            <option value="">-- Selecciona un establecimiento --</option>
            {establecimientos.map(est => (
              <option key={est.id} value={est.id}>
                {est.nombre} ({est.tipo})
              </option>
            ))}
          </select>
        )}
      </div>

      {loadingCat && <div className="text-gray-400">Cargando catalogo...</div>}

      {catalogo && (
        <>
          {catalogo._from_cache && (
            <div className="text-xs text-blue-400 mb-3">Datos desde cache Redis (TTL 5 min)</div>
          )}
          {disponibles.length === 0 ? (
            <div className="text-gray-400 text-center py-12">
              Este establecimiento no tiene productos disponibles.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {disponibles.map(prod => (
                <div key={prod.id_producto} className="bg-sidebar border border-gray-700 rounded-xl p-5 flex flex-col">
                  <div className="flex items-start justify-between mb-2">
                    <span className="inline-block bg-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded-full">
                      {prod.categoria}
                    </span>
                    <span className="text-rappi font-bold text-lg">${prod.precio?.toLocaleString('es-AR')}</span>
                  </div>
                  <h3 className="text-white font-bold text-base mb-1">{prod.nombre}</h3>
                  {prod.descripcion && (
                    <p className="text-gray-400 text-sm mb-2 line-clamp-2">{prod.descripcion}</p>
                  )}
                  {prod.atributos && Object.keys(prod.atributos).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {Object.entries(prod.atributos).map(([k, v]) => (
                        <span key={k} className="bg-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded-full">
                          {k}: {v}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="mt-auto">
                    <div className="flex items-center gap-2 mb-3">
                      <button
                        onClick={() => setCantidades(c => ({ ...c, [prod.id_producto]: Math.max(1, (c[prod.id_producto] || 1) - 1) }))}
                        className="w-8 h-8 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center justify-center font-bold"
                      >-</button>
                      <span className="text-white font-semibold w-8 text-center">{cantidades[prod.id_producto] || 1}</span>
                      <button
                        onClick={() => setCantidades(c => ({ ...c, [prod.id_producto]: (c[prod.id_producto] || 1) + 1 }))}
                        className="w-8 h-8 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center justify-center font-bold"
                      >+</button>
                    </div>
                    <button
                      onClick={() => handleAgregar(prod)}
                      className="w-full bg-rappi hover:bg-rappi-dark text-white py-2 rounded-lg text-sm font-semibold transition-colors"
                    >
                      Agregar al carrito
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!catalogo && !loadingCat && selectedEst && (
        <div className="text-gray-400 text-center py-12">
          No hay catalogo para este establecimiento.
        </div>
      )}
    </Layout>
  )
}
