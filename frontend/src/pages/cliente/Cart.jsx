import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout.jsx'
import { getCarrito, vaciarCarrito, quitarItemCarrito, aplicarPromo, agregarAlCarrito } from '../../api/cliente.js'

export default function Cart() {
  const navigate = useNavigate()
  const [carrito, setCarrito] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [codigoPromo, setCodigoPromo] = useState('')
  const [promoMsg, setPromoMsg] = useState('')
  const [promoErr, setPromoErr] = useState('')

  const fetchCarrito = () => {
    setLoading(true)
    getCarrito()
      .then(setCarrito)
      .catch(() => setError('Error cargando carrito'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchCarrito() }, [])

  const handleVaciar = async () => {
    try {
      await vaciarCarrito()
      fetchCarrito()
    } catch { setError('Error al vaciar carrito') }
  }

  const handleQuitar = async (id_producto) => {
    setCarrito(prev => prev ? { ...prev, items: prev.items.filter(i => i.id_producto !== id_producto) } : prev)
    try {
      await quitarItemCarrito(id_producto)
    } catch {
      setError('Error al quitar item')
      fetchCarrito()
    }
  }

  const handlePromo = async () => {
    setPromoMsg(''); setPromoErr('')
    try {
      const res = await aplicarPromo(codigoPromo)
      setPromoMsg(`Promo aplicada: ${res.descuento}% off (-$${res.monto_descuento?.toFixed(2)})`)
      fetchCarrito()
    } catch (err) {
      setPromoErr(err.response?.data?.detail || 'Error aplicando promo')
    }
  }

  const handleCantidad = async (item, delta) => {
    const nuevaCant = item.cantidad + delta
    if (nuevaCant <= 0) {
      await handleQuitar(item.id_producto)
      return
    }
    setCarrito(prev => prev ? {
      ...prev,
      items: prev.items.map(i => i.id_producto === item.id_producto ? { ...i, cantidad: nuevaCant } : i)
    } : prev)
    try {
      if (!carrito) return
      await agregarAlCarrito({
        id_establecimiento: parseInt(carrito.establecimiento_id),
        nombre_establecimiento: carrito.establecimiento_nombre || '',
        id_producto: item.id_producto,
        nombre: item.nombre,
        precio: item.precio,
        cantidad: delta,
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Error actualizando cantidad')
      fetchCarrito()
    }
  }

  if (loading) return <Layout><div className="text-gray-400">Cargando carrito...</div></Layout>

  const items = carrito?.items || []
  const subtotal = items.reduce((s, i) => s + i.precio * i.cantidad, 0)
  const descuento = parseFloat(carrito?.promo_descuento_monto || 0)
  const total = subtotal - descuento
  const ttl = carrito?.ttl || 0
  const ttlH = Math.floor(ttl / 3600)
  const ttlM = Math.floor((ttl % 3600) / 60)

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Mi Carrito</h1>
          {ttl > 0 && (
            <div className="text-xs text-blue-400 mt-1">TTL del carrito: {ttlH}h {ttlM}min (Redis)</div>
          )}
        </div>
        {items.length > 0 && (
          <button onClick={handleVaciar} className="text-red-400 hover:text-red-300 text-sm border border-red-700 px-3 py-1.5 rounded-lg transition-colors">
            Vaciar carrito
          </button>
        )}
      </div>

      {error && <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}

      {items.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">🛒</div>
          <div className="text-gray-400 text-lg mb-4">Tu carrito esta vacio</div>
          <button onClick={() => navigate('/catalog')} className="bg-rappi text-white px-6 py-2.5 rounded-lg font-semibold">
            Ir al catalogo
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Items */}
          <div className="lg:col-span-2 space-y-3">
            {carrito?.establecimiento_nombre && (
              <div className="text-gray-400 text-sm mb-2">
                Pedido en: <span className="text-white font-semibold">{carrito.establecimiento_nombre}</span>
              </div>
            )}
            {items.map(item => (
              <div key={item.id_producto} className="bg-sidebar border border-gray-700 rounded-xl p-4 flex items-center gap-4">
                <div className="flex-1">
                  <div className="text-white font-semibold">{item.nombre}</div>
                  <div className="text-gray-400 text-xs mt-0.5">Ref: {item.id_producto}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleCantidad(item, -1)} className="w-7 h-7 bg-gray-700 hover:bg-gray-600 text-white rounded flex items-center justify-center text-sm">-</button>
                  <span className="text-white font-semibold w-6 text-center">{item.cantidad}</span>
                  <button onClick={() => handleCantidad(item, 1)} className="w-7 h-7 bg-gray-700 hover:bg-gray-600 text-white rounded flex items-center justify-center text-sm">+</button>
                </div>
                <div className="text-rappi font-bold w-24 text-right">${(item.precio * item.cantidad).toLocaleString('es-AR')}</div>
                <button onClick={() => handleQuitar(item.id_producto)} className="text-gray-500 hover:text-red-400 transition-colors text-lg">🗑️</button>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="bg-sidebar border border-gray-700 rounded-xl p-5 h-fit space-y-4">
            <h2 className="text-white font-bold text-lg">Resumen del Pedido</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-400">
                <span>Subtotal</span>
                <span>${subtotal.toLocaleString('es-AR')}</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Envio</span>
                <span>$0</span>
              </div>
              {descuento > 0 && (
                <div className="flex justify-between text-green-400">
                  <span>Descuento ({carrito?.promo_codigo})</span>
                  <span>-${descuento.toFixed(2)}</span>
                </div>
              )}
              <div className="border-t border-gray-700 pt-2 flex justify-between text-white font-bold text-lg">
                <span>Total</span>
                <span className="text-rappi">${total.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>

            {/* Promo */}
            {!carrito?.promo_codigo ? (
              <div>
                <div className="text-gray-400 text-xs mb-2">Codigo de promocion</div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={codigoPromo}
                    onChange={e => setCodigoPromo(e.target.value.toUpperCase())}
                    placeholder="VERANO20"
                    className="flex-1 bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-rappi"
                  />
                  <button onClick={handlePromo} className="bg-gray-600 hover:bg-gray-500 text-white px-3 py-2 rounded-lg text-sm font-semibold">Aplicar</button>
                </div>
                {promoMsg && <div className="text-green-400 text-xs mt-1">{promoMsg}</div>}
                {promoErr && <div className="text-red-400 text-xs mt-1">{promoErr}</div>}
              </div>
            ) : (
              <div className="bg-green-900/30 border border-green-700 rounded-lg px-3 py-2 text-green-400 text-sm">
                Promo <strong>{carrito.promo_codigo}</strong> aplicada ({carrito.promo_descuento}% off)
              </div>
            )}

            <button
              onClick={() => navigate('/checkout')}
              className="w-full bg-rappi hover:bg-rappi-dark text-white py-3 rounded-lg font-bold text-sm transition-colors"
            >
              Ir a confirmar
            </button>
          </div>
        </div>
      )}
    </Layout>
  )
}
