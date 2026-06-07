import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout.jsx'
import { getCarrito, getDirecciones, agregarDireccion, confirmarPedido } from '../../api/cliente.js'

const METODOS = [
  { id: 'efectivo', label: 'Efectivo', icon: '💵' },
  { id: 'tarjeta_credito', label: 'Tarjeta Credito', icon: '💳' },
  { id: 'tarjeta_debito', label: 'Tarjeta Debito', icon: '🏧' },
]

export default function Checkout() {
  const navigate = useNavigate()
  const [carrito, setCarrito] = useState(null)
  const [direcciones, setDirecciones] = useState([])
  const [selectedDir, setSelectedDir] = useState(null)
  const [metodo, setMetodo] = useState('efectivo')
  const [nuevaDir, setNuevaDir] = useState({ calle: '', numero: '', ciudad: '', cp: '', alias: '' })
  const [showNuevaDir, setShowNuevaDir] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(null)

  useEffect(() => {
    Promise.all([getCarrito(), getDirecciones()])
      .then(([c, d]) => {
        setCarrito(c)
        setDirecciones(d)
        if (d.length > 0) setSelectedDir(d[0].nro_direccion)
        else setShowNuevaDir(true)
      })
      .catch(() => setError('Error cargando datos'))
      .finally(() => setLoading(false))
  }, [])

  const handleAgregarDir = async () => {
    if (!nuevaDir.calle || !nuevaDir.ciudad) { setError('Calle y ciudad son obligatorios'); return }
    try {
      const res = await agregarDireccion(nuevaDir)
      const d = await getDirecciones()
      setDirecciones(d)
      setSelectedDir(res.nro_direccion)
      setShowNuevaDir(false)
      setNuevaDir({ calle: '', numero: '', ciudad: '', cp: '', alias: '' })
    } catch (err) {
      setError(err.response?.data?.detail || 'Error agregando direccion')
    }
  }

  const handleConfirmar = async () => {
    if (!selectedDir) { setError('Selecciona una direccion'); return }
    setSubmitting(true)
    setError('')
    try {
      const res = await confirmarPedido(selectedDir, metodo)
      setSuccess(res)
      setTimeout(() => navigate('/mis-pedidos'), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al confirmar pedido')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Layout><div className="text-gray-400">Cargando...</div></Layout>

  const items = carrito?.items || []
  const subtotal = items.reduce((s, i) => s + i.precio * i.cantidad, 0)
  const descuento = parseFloat(carrito?.promo_descuento_monto || 0)
  const total = subtotal - descuento

  if (success) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center py-20">
          <div className="text-6xl mb-4">✅</div>
          <h2 className="text-2xl font-bold text-white mb-2">Pedido Confirmado</h2>
          <div className="text-gray-400 text-lg mb-2">Pedido #{success.id_pedido}</div>
          <div className="text-rappi font-bold text-xl mb-6">${success.total?.toFixed(2)}</div>
          <div className="text-gray-500 text-sm">Redirigiendo a Mis Pedidos...</div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-white mb-6">Confirmar Pedido</h1>
      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Address + Payment */}
        <div className="space-y-5">
          {/* Address selector */}
          <div className="bg-sidebar border border-gray-700 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-white font-bold">Direccion de entrega</h2>
              <button
                onClick={() => setShowNuevaDir(!showNuevaDir)}
                className="text-rappi text-sm hover:underline"
              >
                + Nueva direccion
              </button>
            </div>
            <div className="space-y-2">
              {direcciones.map(d => (
                <label key={d.nro_direccion} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${selectedDir === d.nro_direccion ? 'border-rappi bg-rappi/10' : 'border-gray-600 hover:border-gray-500'}`}>
                  <input
                    type="radio"
                    name="direccion"
                    value={d.nro_direccion}
                    checked={selectedDir === d.nro_direccion}
                    onChange={() => setSelectedDir(d.nro_direccion)}
                    className="accent-rappi"
                  />
                  <div>
                    <div className="text-white text-sm font-medium">{d.calle} {d.numero || ''}, {d.ciudad}</div>
                    {d.alias && <div className="text-gray-400 text-xs">{d.alias}</div>}
                  </div>
                </label>
              ))}
              {direcciones.length === 0 && !showNuevaDir && (
                <div className="text-gray-400 text-sm">No tienes direcciones. Agrega una.</div>
              )}
            </div>

            {showNuevaDir && (
              <div className="mt-4 space-y-3 border-t border-gray-700 pt-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-gray-400 text-xs mb-1 block">Calle *</label>
                    <input value={nuevaDir.calle} onChange={e => setNuevaDir(p => ({ ...p, calle: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
                  </div>
                  <div>
                    <label className="text-gray-400 text-xs mb-1 block">Numero</label>
                    <input value={nuevaDir.numero} onChange={e => setNuevaDir(p => ({ ...p, numero: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-gray-400 text-xs mb-1 block">Ciudad *</label>
                    <input value={nuevaDir.ciudad} onChange={e => setNuevaDir(p => ({ ...p, ciudad: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
                  </div>
                  <div>
                    <label className="text-gray-400 text-xs mb-1 block">ZIP</label>
                    <input value={nuevaDir.cp} onChange={e => setNuevaDir(p => ({ ...p, cp: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
                  </div>
                  <div>
                    <label className="text-gray-400 text-xs mb-1 block">Alias</label>
                    <input value={nuevaDir.alias} onChange={e => setNuevaDir(p => ({ ...p, alias: e.target.value }))} placeholder="Casa"
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi" />
                  </div>
                </div>
                <button onClick={handleAgregarDir} className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded-lg text-sm font-semibold">
                  Guardar direccion
                </button>
              </div>
            )}
          </div>

          {/* Payment method */}
          <div className="bg-sidebar border border-gray-700 rounded-xl p-5">
            <h2 className="text-white font-bold mb-3">Metodo de pago</h2>
            <div className="flex gap-3">
              {METODOS.map(m => (
                <button
                  key={m.id}
                  onClick={() => setMetodo(m.id)}
                  className={`flex-1 flex flex-col items-center gap-1 py-3 rounded-lg border-2 text-sm font-medium transition-colors ${metodo === m.id ? 'border-rappi bg-rappi/10 text-white' : 'border-gray-600 text-gray-400 hover:border-gray-500'}`}
                >
                  <span className="text-xl">{m.icon}</span>
                  <span className="text-xs">{m.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Order summary */}
        <div className="bg-sidebar border border-gray-700 rounded-xl p-5 h-fit">
          <h2 className="text-white font-bold text-lg mb-4">Resumen del Pedido</h2>
          {carrito?.establecimiento_nombre && (
            <div className="text-gray-400 text-sm mb-3">{carrito.establecimiento_nombre}</div>
          )}
          <div className="space-y-2 mb-4">
            {items.map(item => (
              <div key={item.id_producto} className="flex justify-between text-sm">
                <span className="text-gray-300">{item.cantidad}x {item.nombre}</span>
                <span className="text-gray-300">${(item.precio * item.cantidad).toLocaleString('es-AR')}</span>
              </div>
            ))}
          </div>
          <div className="border-t border-gray-700 pt-3 space-y-2 text-sm">
            <div className="flex justify-between text-gray-400"><span>Subtotal</span><span>${subtotal.toLocaleString('es-AR')}</span></div>
            {descuento > 0 && <div className="flex justify-between text-green-400"><span>Descuento</span><span>-${descuento.toFixed(2)}</span></div>}
            <div className="flex justify-between text-white font-bold text-lg border-t border-gray-700 pt-2">
              <span>Total</span>
              <span className="text-rappi">${total.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</span>
            </div>
          </div>
          <button
            onClick={handleConfirmar}
            disabled={submitting || items.length === 0}
            className="w-full mt-5 bg-rappi hover:bg-rappi-dark text-white py-4 rounded-lg font-black text-base uppercase tracking-wide transition-colors disabled:opacity-60"
          >
            {submitting ? 'Procesando...' : 'Confirmar Pedido'}
          </button>
          <div className="text-gray-500 text-xs text-center mt-2">Registrado en 5 bases de datos simultaneamente</div>
        </div>
      </div>
    </Layout>
  )
}
