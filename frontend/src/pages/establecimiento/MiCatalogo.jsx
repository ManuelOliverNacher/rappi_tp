import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import { getCatalogoEst, agregarProducto, toggleDisponibilidad } from '../../api/establecimiento.js'

const CATEGORIAS = ['rolls', 'entrada', 'principal', 'postre', 'bebida', 'medicamento', 'higiene', 'suplemento', 'otro']
const PAGE_SIZE = 10

export default function MiCatalogo() {
  const [catalogo, setCatalogo] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [page, setPage] = useState(1)
  const [form, setForm] = useState({ nombre: '', precio: '', categoria: '', descripcion: '', atributos: '{}' })
  const [submitting, setSubmitting] = useState(false)

  const fetchCatalogo = () => {
    setLoading(true)
    getCatalogoEst()
      .then(doc => setCatalogo(doc.catalogo || []))
      .catch(() => setError('Error cargando catalogo'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchCatalogo() }, [])

  const handleAgregarProducto = async (e) => {
    e.preventDefault()
    if (!form.nombre || !form.categoria || !form.precio) { setError('Nombre, precio y categoria son obligatorios'); return }
    let atributos = {}
    try { atributos = JSON.parse(form.atributos || '{}') } catch { setError('Atributos debe ser JSON valido'); return }
    setSubmitting(true)
    try {
      await agregarProducto({ nombre: form.nombre, precio: parseFloat(form.precio), categoria: form.categoria, descripcion: form.descripcion, atributos })
      setSuccess('Producto agregado correctamente')
      setShowModal(false)
      setForm({ nombre: '', precio: '', categoria: '', descripcion: '', atributos: '{}' })
      fetchCatalogo()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al agregar producto')
    } finally {
      setSubmitting(false)
    }
  }

  const handleToggle = async (prod) => {
    try {
      await toggleDisponibilidad(prod.id_producto, !prod.disponible)
      fetchCatalogo()
    } catch { setError('Error actualizando disponibilidad') }
  }

  const disponibles = catalogo.filter(p => p.disponible !== false).length
  const agotados = catalogo.length - disponibles

  const startIdx = (page - 1) * PAGE_SIZE
  const paginated = catalogo.slice(startIdx, startIdx + PAGE_SIZE)
  const totalPages = Math.ceil(catalogo.length / PAGE_SIZE)

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Mi Catalogo</h1>
          <p className="text-gray-400 text-sm mt-1">Gestion de productos del establecimiento</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-rappi hover:bg-rappi-dark text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors"
        >
          + Agregar producto
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-sidebar border border-gray-700 rounded-xl p-4">
          <div className="text-gray-400 text-xs uppercase font-semibold">Total Productos</div>
          <div className="text-white text-2xl font-bold mt-1">{catalogo.length}</div>
        </div>
        <div className="bg-sidebar border border-gray-700 rounded-xl p-4">
          <div className="text-gray-400 text-xs uppercase font-semibold">Disponibles</div>
          <div className="text-green-400 text-2xl font-bold mt-1">{disponibles}</div>
        </div>
        <div className="bg-sidebar border border-gray-700 rounded-xl p-4">
          <div className="text-gray-400 text-xs uppercase font-semibold">Agotados</div>
          <div className="text-red-400 text-2xl font-bold mt-1">{agotados}</div>
        </div>
      </div>

      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {success && <div className="bg-green-900/50 border border-green-700 text-green-300 px-4 py-3 rounded-lg mb-4 text-sm">{success}</div>}

      {loading ? (
        <div className="text-gray-400">Cargando catalogo desde MongoDB...</div>
      ) : catalogo.length === 0 ? (
        <div className="text-gray-400 text-center py-16">No tienes productos. Agrega el primero.</div>
      ) : (
        <>
          <div className="bg-sidebar border border-gray-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Producto</th>
                  <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Precio</th>
                  <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Categoria</th>
                  <th className="text-left text-gray-400 text-xs font-semibold px-4 py-3 uppercase">Disponible</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map(prod => (
                  <tr key={prod.id_producto} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center text-gray-500 text-xs">IMG</div>
                        <div>
                          <div className="text-white text-sm font-semibold">{prod.nombre}</div>
                          <div className="text-gray-500 text-xs font-mono">{prod.id_producto}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-rappi font-bold text-sm">${prod.precio?.toLocaleString('es-AR')}</td>
                    <td className="px-4 py-3">
                      <span className="bg-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded-full">{prod.categoria}</span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleToggle(prod)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${prod.disponible !== false ? 'bg-green-500' : 'bg-gray-600'}`}
                      >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${prod.disponible !== false ? 'translate-x-6' : 'translate-x-1'}`} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 bg-gray-700 text-white rounded-lg text-sm disabled:opacity-50">Anterior</button>
              <span className="text-gray-400 text-sm">{page} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1.5 bg-gray-700 text-white rounded-lg text-sm disabled:opacity-50">Siguiente</button>
            </div>
          )}
        </>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-sidebar border border-gray-700 rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-bold text-lg">Agregar producto</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white text-xl">✕</button>
            </div>
            <form onSubmit={handleAgregarProducto} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 text-xs mb-1 block">Nombre *</label>
                  <input value={form.nombre} onChange={e => setForm(p => ({ ...p, nombre: e.target.value }))} required
                    className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
                </div>
                <div>
                  <label className="text-gray-400 text-xs mb-1 block">Precio *</label>
                  <input type="number" value={form.precio} onChange={e => setForm(p => ({ ...p, precio: e.target.value }))} required min="0"
                    className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">Categoria *</label>
                <select value={form.categoria} onChange={e => setForm(p => ({ ...p, categoria: e.target.value }))} required
                  className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi">
                  <option value="">Seleccionar...</option>
                  {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">Descripcion</label>
                <input value={form.descripcion} onChange={e => setForm(p => ({ ...p, descripcion: e.target.value }))}
                  className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">Atributos (JSON)</label>
                <textarea value={form.atributos} onChange={e => setForm(p => ({ ...p, atributos: e.target.value }))} rows={3}
                  className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-rappi resize-none" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg text-sm font-semibold">Cancelar</button>
                <button type="submit" disabled={submitting} className="flex-1 bg-rappi hover:bg-rappi-dark text-white py-2 rounded-lg text-sm font-bold disabled:opacity-60">
                  {submitting ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  )
}
