import React, { useState } from 'react'
import Layout from '../../components/Layout.jsx'
import { verificarConexiones, cargarSeed, limpiarBases } from '../../api/admin.js'

const DB_INFO = {
  postgresql: { label: 'PostgreSQL', icon: '🐘', desc: 'Supabase · Datos transaccionales' },
  mongodb:    { label: 'MongoDB',    icon: '🍃', desc: 'Atlas · Catalogo y calificaciones' },
  cassandra:  { label: 'Cassandra',  icon: '👁️',  desc: 'Astra DB · Timeline de estados' },
  neo4j:      { label: 'Neo4j',      icon: '🔗', desc: 'Aura · Grafo de relaciones' },
  redis:      { label: 'Redis',      icon: '⚡', desc: 'Redis Cloud · Cache y sesiones' },
}

export default function System() {
  const [conexiones, setConexiones] = useState({})
  const [loadingConex, setLoadingConex] = useState(false)
  const [lastCheck, setLastCheck] = useState(null)
  const [seedLoading, setSeedLoading] = useState(false)
  const [seedMsg, setSeedMsg] = useState('')
  const [seedErr, setSeedErr] = useState('')
  const [purgeInput, setPurgeInput] = useState('')
  const [purgeLoading, setPurgeLoading] = useState(false)
  const [purgeResult, setPurgeResult] = useState(null)
  const [purgeErr, setPurgeErr] = useState('')

  const handleVerificar = async () => {
    setLoadingConex(true)
    try {
      const data = await verificarConexiones()
      setConexiones(data)
      setLastCheck(new Date().toLocaleString('es-AR'))
    } catch { setConexiones({ error: 'No se pudo conectar al servidor' }) }
    setLoadingConex(false)
  }

  const handleSeed = async () => {
    setSeedLoading(true); setSeedMsg(''); setSeedErr('')
    try {
      await cargarSeed()
      setSeedMsg('Datos de prueba cargados correctamente en las 5 bases.')
    } catch (err) {
      setSeedErr(err.response?.data?.detail || 'Error al cargar datos')
    }
    setSeedLoading(false)
  }

  const handlePurge = async () => {
    if (purgeInput !== 'BORRAR TODO') { setPurgeErr('Escribe exactamente BORRAR TODO'); return }
    setPurgeLoading(true); setPurgeErr(''); setPurgeResult(null)
    try {
      const data = await limpiarBases()
      setPurgeResult(data)
    } catch (err) {
      setPurgeErr(err.response?.data?.detail || 'Error al limpiar bases')
    }
    setPurgeLoading(false)
    setPurgeInput('')
  }

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-white mb-6">System Verification</h1>

      {/* DB Status */}
      <div className="bg-sidebar border border-gray-700 rounded-xl p-5 mb-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-bold">Estado de Bases de Datos</h2>
          <button
            onClick={handleVerificar}
            disabled={loadingConex}
            className="bg-rappi hover:bg-rappi-dark text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-60"
          >
            {loadingConex ? 'Verificando...' : '🔄 Verificar conexiones'}
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {Object.entries(DB_INFO).map(([key, info]) => {
            const status = conexiones[key]
            const isOk = status === 'ok'
            const isError = status && status !== 'ok'
            return (
              <div key={key} className={`border rounded-xl p-4 flex flex-col items-center gap-2 text-center ${isOk ? 'border-green-700 bg-green-900/20' : isError ? 'border-red-700 bg-red-900/20' : 'border-gray-600'}`}>
                <span className="text-2xl">{info.icon}</span>
                <div className="text-white text-sm font-bold">{info.label}</div>
                <div className="text-gray-400 text-xs">{info.desc}</div>
                {status && (
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${isOk ? 'bg-green-800 text-green-300' : 'bg-red-800 text-red-300'}`}>
                    {isOk ? 'ONLINE' : 'ERROR'}
                  </span>
                )}
                {!status && <span className="text-xs text-gray-500">No verificado</span>}
              </div>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
        {/* Seed */}
        <div className="bg-sidebar border border-gray-700 rounded-xl p-5">
          <h2 className="text-white font-bold mb-2">Cargar datos de prueba</h2>
          <p className="text-gray-400 text-sm mb-4">
            Inserta 3 clientes, 3 establecimientos, 3 repartidores, 12 pedidos, calificaciones y 2 promos en las 5 bases de datos.
          </p>
          {seedMsg && <div className="bg-green-900/40 border border-green-700 text-green-300 px-3 py-2 rounded-lg text-sm mb-3">{seedMsg}</div>}
          {seedErr && <div className="bg-red-900/40 border border-red-700 text-red-300 px-3 py-2 rounded-lg text-sm mb-3">{seedErr}</div>}
          <button
            onClick={handleSeed}
            disabled={seedLoading}
            className="bg-gray-700 hover:bg-gray-600 text-white px-5 py-2.5 rounded-lg text-sm font-bold transition-colors disabled:opacity-60"
          >
            {seedLoading ? 'Cargando...' : '🌱 Confirmar Carga'}
          </button>
        </div>

        {/* Purge */}
        <div className="bg-sidebar border border-red-900/50 rounded-xl p-5">
          <h2 className="text-red-400 font-bold mb-2">⛔ Limpiar todas las bases</h2>
          <p className="text-gray-400 text-sm mb-4">
            Borra TODOS los datos de las 5 bases de datos. Esta accion no se puede deshacer.
          </p>
          {purgeErr && <div className="bg-red-900/40 border border-red-700 text-red-300 px-3 py-2 rounded-lg text-sm mb-3">{purgeErr}</div>}
          {purgeResult && (
            <div className="mb-3 space-y-1">
              {Object.entries(purgeResult).map(([db, msg]) => (
                <div key={db} className={`text-xs ${msg === 'ok' ? 'text-green-400' : 'text-red-400'}`}>
                  {db}: {msg === 'ok' ? '✅ Limpiado' : `❌ ${msg}`}
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              value={purgeInput}
              onChange={e => setPurgeInput(e.target.value)}
              placeholder='Escribe "BORRAR TODO"'
              className="flex-1 bg-gray-700 border border-red-700/50 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-red-500"
            />
            <button
              onClick={handlePurge}
              disabled={purgeLoading || purgeInput !== 'BORRAR TODO'}
              className="bg-red-700 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors disabled:opacity-40"
            >
              {purgeLoading ? '...' : 'Execute Purge'}
            </button>
          </div>
        </div>
      </div>

      {/* Resultado de la última verificación */}
      {lastCheck && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">
              Último chequeo: {lastCheck}
            </span>
          </div>
          <div className="font-mono text-xs space-y-1">
            {Object.entries(DB_INFO).map(([key, info]) => {
              const status = conexiones[key]
              const isOk = status === 'ok'
              return (
                <div key={key} className={isOk ? 'text-green-400' : 'text-red-400'}>
                  [{new Date().toLocaleTimeString('es-AR')}] {info.label}: {isOk ? 'conexion OK' : `ERROR — ${status}`}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </Layout>
  )
}
