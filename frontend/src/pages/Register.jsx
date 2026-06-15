import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { registerCliente, registerEstablecimiento, registerRepartidor } from '../api/auth.js'

const ROLES = [
  { id: 'cliente',         label: 'Cliente',         icon: '👤' },
  { id: 'establecimiento', label: 'Establecimiento',  icon: '🏪' },
  { id: 'repartidor',      label: 'Repartidor',       icon: '🛵' },
]

function Field({ label, type = 'text', value, onChange, placeholder, required = true }) {
  const icons = {
    text:     '✏️',
    email:    '✉️',
    password: '🔒',
    tel:      '📞',
  }
  return (
    <div className="relative">
      <span className="absolute left-3 top-3 text-gray-400 text-sm">{icons[type] || '✏️'}</span>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={`${label}${required ? ' *' : ' (opcional)'}`}
        required={required}
        className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-rappi bg-white"
      />
    </div>
  )
}

export default function Register() {
  const navigate = useNavigate()
  const [rol, setRol]       = useState('cliente')
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')
  const [success, setSuccess] = useState('')

  // campos comunes
  const [nombre,   setNombre]   = useState('')
  const [apellido, setApellido] = useState('')
  const [email,    setEmail]    = useState('')
  const [telefono, setTelefono] = useState('')
  const [password, setPassword] = useState('')
  const [confirm,  setConfirm]  = useState('')

  // establecimiento
  const [tipo,      setTipo]      = useState('restaurante')
  const [extra,     setExtra]     = useState('')
  const [direccion, setDireccion] = useState('')
  const [horario,   setHorario]   = useState('')

  // repartidor
  const [vehiculo, setVehiculo] = useState('')

  const resetForm = () => {
    setNombre(''); setApellido(''); setEmail(''); setTelefono('')
    setPassword(''); setConfirm(''); setTipo('restaurante')
    setExtra(''); setDireccion(''); setHorario(''); setVehiculo('')
    setError(''); setSuccess('')
  }

  const handleRolChange = (nuevoRol) => {
    setRol(nuevoRol)
    resetForm()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Las contraseñas no coinciden'); return }
    if (password.length < 6)  { setError('La contraseña debe tener al menos 6 caracteres'); return }

    setLoading(true)
    try {
      let res
      if (rol === 'cliente') {
        res = await registerCliente({ nombre, apellido, email, telefono: telefono || null, password })
      } else if (rol === 'establecimiento') {
        if (!extra) { setError('Especialidad / Rubro es obligatorio'); setLoading(false); return }
        res = await registerEstablecimiento({ nombre, email, password, tipo, extra, direccion, telefono: telefono || null, horario: horario || null })
      } else {
        res = await registerRepartidor({ nombre, apellido, email, password, vehiculo: vehiculo || 'moto', telefono: telefono || null })
      }
      const displayName = rol === 'establecimiento' ? nombre : `${nombre} ${apellido}`.trim()
      const saved = JSON.parse(localStorage.getItem('registered_users') || '[]')
      saved.push({ nombre: displayName, email, pwd: password, rol })
      localStorage.setItem('registered_users', JSON.stringify(saved))
      setSuccess(`¡Cuenta creada exitosamente! ID: ${res.id} — Ahora podés iniciar sesión.`)
      resetForm()
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al registrar la cuenta')
    } finally {
      setLoading(false)
    }
  }

  const extraLabel = tipo === 'restaurante' ? 'Especialidad culinaria' : 'Rubro'
  const extraPlaceholder = tipo === 'restaurante' ? 'italiana, sushi, parrilla…' : 'farmacia, electrónica, kiosco…'

  return (
    <div
      className="min-h-screen flex items-center justify-center py-10"
      style={{
        background: '#111827',
        backgroundImage: 'radial-gradient(circle, #374151 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }}
    >
      <div className="bg-white text-gray-800 rounded-xl shadow-2xl p-8 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-6">
          <div className="text-5xl font-black text-rappi tracking-tight">rappi</div>
          <div className="text-gray-500 text-sm font-medium">Crear cuenta</div>
        </div>

        {/* Role selector */}
        <div className="grid grid-cols-3 gap-2 mb-6">
          {ROLES.map(r => (
            <button
              key={r.id}
              type="button"
              onClick={() => handleRolChange(r.id)}
              className={`flex flex-col items-center gap-1 px-3 py-2.5 rounded-lg border-2 text-xs font-semibold transition-all ${
                rol === r.id
                  ? 'bg-rappi text-white border-rappi'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-rappi hover:text-rappi'
              }`}
            >
              <span className="text-xl">{r.icon}</span>
              {r.label}
            </button>
          ))}
        </div>

        {success ? (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-4 rounded-lg text-sm text-center">
              {success}
            </div>
            <button
              onClick={() => navigate('/login')}
              className="w-full bg-rappi hover:bg-rappi-dark text-white font-bold py-3 rounded-lg transition-colors"
            >
              Ir a iniciar sesión
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">

            {/* Cliente y Repartidor: nombre + apellido */}
            {rol !== 'establecimiento' && (
              <div className="grid grid-cols-2 gap-3">
                <Field label="Nombre"   value={nombre}   onChange={setNombre} />
                <Field label="Apellido" value={apellido} onChange={setApellido} />
              </div>
            )}

            {/* Establecimiento: nombre del negocio */}
            {rol === 'establecimiento' && (
              <>
                <Field label="Nombre del establecimiento" value={nombre} onChange={setNombre} />
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 font-semibold uppercase tracking-wide">Tipo *</label>
                    <select
                      value={tipo}
                      onChange={e => setTipo(e.target.value)}
                      className="mt-1 w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-rappi bg-white"
                    >
                      <option value="restaurante">Restaurante</option>
                      <option value="tienda">Tienda</option>
                    </select>
                  </div>
                  <Field label={extraLabel} value={extra} onChange={setExtra} placeholder={extraPlaceholder} />
                </div>
                <Field label="Dirección" value={direccion} onChange={setDireccion} required={false} />
                <Field label="Horario (ej: Lun-Vie 10-22)" value={horario} onChange={setHorario} required={false} />
              </>
            )}

            {/* Repartidor: vehículo */}
            {rol === 'repartidor' && (
              <div>
                <label className="text-xs text-gray-500 font-semibold uppercase tracking-wide">Vehículo</label>
                <select
                  value={vehiculo}
                  onChange={e => setVehiculo(e.target.value)}
                  className="mt-1 w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-rappi bg-white"
                >
                  <option value="moto">Moto</option>
                  <option value="auto">Auto</option>
                  <option value="bici">Bicicleta</option>
                </select>
              </div>
            )}

            <Field label="Teléfono" type="tel" value={telefono} onChange={setTelefono} required={false} />
            <Field label="Email" type="email" value={email} onChange={setEmail} />
            <div className="grid grid-cols-2 gap-3">
              <Field label="Contraseña"  type="password" value={password} onChange={setPassword} />
              <Field label="Confirmar"   type="password" value={confirm}  onChange={setConfirm} />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-rappi hover:bg-rappi-dark text-white font-bold py-3 rounded-lg transition-colors disabled:opacity-60"
            >
              {loading ? 'Creando cuenta...' : 'Crear cuenta'}
            </button>
          </form>
        )}

        <div className="text-center mt-4 text-sm text-gray-500">
          ¿Ya tenés cuenta?{' '}
          <span
            className="text-rappi cursor-pointer hover:underline font-medium"
            onClick={() => navigate('/login')}
          >
            Iniciar sesión
          </span>
        </div>
      </div>
    </div>
  )
}
