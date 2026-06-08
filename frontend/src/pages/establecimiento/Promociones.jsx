import React, { useState } from 'react'
import Layout from '../../components/Layout.jsx'
import { crearPromocion } from '../../api/establecimiento.js'

const EMPTY = { codigo: '', descripcion: '', descuento: '', monto_minimo: '', dias: '30', condiciones: '' }

export default function Promociones() {
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.codigo.trim() || !form.descripcion.trim() || !form.descuento) {
      setError('Codigo, descripcion y descuento son obligatorios')
      return
    }
    const descuento = parseFloat(form.descuento)
    if (isNaN(descuento) || descuento <= 0 || descuento > 100) {
      setError('El descuento debe ser un porcentaje entre 1 y 100')
      return
    }
    setLoading(true)
    setError('')
    try {
      await crearPromocion({
        codigo: form.codigo.trim().toUpperCase(),
        descripcion: form.descripcion.trim(),
        descuento,
        monto_minimo: parseFloat(form.monto_minimo) || 0,
        dias: parseInt(form.dias) || 30,
        condiciones: form.condiciones.trim() || null,
      })
      setSuccess(`Promocion "${form.codigo.toUpperCase()}" creada exitosamente`)
      setForm(EMPTY)
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al crear la promocion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-white mb-6">Crear Codigo de Descuento</h1>

      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
      {success && <div className="bg-green-900/50 border border-green-700 text-green-300 px-4 py-3 rounded-lg mb-4 text-sm">{success}</div>}

      <div className="max-w-lg">
        <form onSubmit={handleSubmit} className="bg-sidebar border border-gray-700 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-gray-400 text-sm mb-1">Codigo *</label>
            <input
              value={form.codigo}
              onChange={e => set('codigo', e.target.value.toUpperCase())}
              placeholder="Ej: VERANO20"
              maxLength={20}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi uppercase"
            />
          </div>

          <div>
            <label className="block text-gray-400 text-sm mb-1">Descripcion *</label>
            <input
              value={form.descripcion}
              onChange={e => set('descripcion', e.target.value)}
              placeholder="Ej: Descuento de verano"
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">Descuento (%) *</label>
              <input
                type="number"
                min="1"
                max="100"
                step="0.01"
                value={form.descuento}
                onChange={e => set('descuento', e.target.value)}
                placeholder="Ej: 15"
                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi"
              />
            </div>
            <div>
              <label className="block text-gray-400 text-sm mb-1">Monto minimo ($)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.monto_minimo}
                onChange={e => set('monto_minimo', e.target.value)}
                placeholder="0"
                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-400 text-sm mb-1">Vigencia (dias)</label>
            <input
              type="number"
              min="1"
              max="365"
              value={form.dias}
              onChange={e => set('dias', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi"
            />
          </div>

          <div>
            <label className="block text-gray-400 text-sm mb-1">Condiciones</label>
            <textarea
              value={form.condiciones}
              onChange={e => set('condiciones', e.target.value)}
              placeholder="Ej: Solo valido para pedidos de mas de $5000"
              rows={2}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-rappi hover:bg-rappi-dark text-white py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-60"
          >
            {loading ? 'Creando...' : 'Crear Promocion'}
          </button>
        </form>
      </div>
    </Layout>
  )
}
