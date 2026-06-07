import React, { useState, useEffect } from 'react'
import Layout from '../../components/Layout.jsx'
import {
  reporteCiudades, reporteProductos, reporteRestaurantes,
  reporteFinde, reporteRapidos, reporteTopProductos
} from '../../api/admin.js'

function DataTable({ columns, rows, loading, empty = 'Sin datos.' }) {
  if (loading) return <div className="text-gray-500 text-sm py-4">Cargando...</div>
  if (!rows || rows.length === 0) return <div className="text-gray-500 text-sm py-4">{empty}</div>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            {columns.map(c => (
              <th key={c} className="text-left text-gray-400 text-xs font-semibold py-2 pr-4 uppercase">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-700/30 hover:bg-gray-700/20">
              {Object.values(row).map((v, j) => (
                <td key={j} className="py-2 pr-4 text-gray-300 text-xs">{String(v ?? '—')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Widget({ title, source, columns, rows, loading }) {
  return (
    <div className="bg-sidebar border border-gray-700 rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-white font-bold text-sm">{title}</h3>
      </div>
      <DataTable columns={columns} rows={rows} loading={loading} />
      <div className="mt-3 pt-2 border-t border-gray-700">
        <span className="text-gray-500 text-xs font-mono">SOURCE: {source}</span>
      </div>
    </div>
  )
}

function exportCSV(rows, filename) {
  if (!rows || rows.length === 0) return
  const keys = Object.keys(rows[0])
  const csv = [keys.join(','), ...rows.map(r => keys.map(k => `"${r[k] ?? ''}"`).join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

export default function Analytics() {
  const [data, setData] = useState({})
  const [loading, setLoading] = useState({})
  const [allLoaded, setAllLoaded] = useState(false)

  const fetchAll = () => {
    const fetchers = {
      ciudades: reporteCiudades,
      productos: reporteProductos,
      restaurantes: reporteRestaurantes,
      finde: reporteFinde,
      rapidos: reporteRapidos,
      top: reporteTopProductos,
    }
    Object.entries(fetchers).forEach(([key, fn]) => {
      setLoading(p => ({ ...p, [key]: true }))
      fn()
        .then(d => setData(p => ({ ...p, [key]: d })))
        .catch(() => setData(p => ({ ...p, [key]: [] })))
        .finally(() => setLoading(p => ({ ...p, [key]: false })))
    })
    setAllLoaded(true)
  }

  useEffect(() => { fetchAll() }, [])

  const handleExport = () => {
    const all = Object.entries(data).flatMap(([k, rows]) =>
      (rows || []).map(r => ({ reporte: k, ...r }))
    )
    exportCSV(all, 'rappi_analytics.csv')
  }

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">System Analytics Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">Reportes en tiempo real desde las 5 bases de datos</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleExport} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
            📥 Export CSV
          </button>
          <button onClick={fetchAll} className="bg-rappi hover:bg-rappi-dark text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Widget
          title="Pedidos por Ciudad"
          source="POSTGRESQL"
          columns={['Ciudad', 'Fecha', 'Pedidos', 'Facturacion ($)']}
          rows={(data.ciudades || []).map(r => ({
            ciudad: r.ciudad, fecha: r.fecha, pedidos: r.pedidos,
            facturacion: `$${parseFloat(r.facturacion).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`
          }))}
          loading={loading.ciudades}
        />

        <Widget
          title="Productos mas pedidos"
          source="NEO4J"
          columns={['Producto', 'Unidades', 'Pedidos distintos']}
          rows={(data.productos || []).map(r => ({ producto: r.producto, unidades: r.unidades, pedidos: r.pedidos }))}
          loading={loading.productos}
        />

        <Widget
          title="Locales mas populares"
          source="NEO4J"
          columns={['Establecimiento', 'Pedidos', 'Calificacion']}
          rows={(data.restaurantes || []).map(r => ({
            establecimiento: r.establecimiento, pedidos: r.pedidos,
            calificacion: r.calificacion != null ? `${r.calificacion} ⭐` : '—'
          }))}
          loading={loading.restaurantes}
        />

        <Widget
          title="Categorias en fines de semana"
          source="POSTGRESQL + MONGODB"
          columns={['Categoria', 'Unidades']}
          rows={(data.finde || []).map(r => ({ categoria: r.categoria, unidades: r.unidades }))}
          loading={loading.finde}
        />

        <Widget
          title="Pedidos rapidos y caros (> $50, < 30min)"
          source="POSTGRESQL + CASSANDRA"
          columns={['Pedido', 'Establecimiento', 'Cliente', 'Total', 'Duracion']}
          rows={(data.rapidos || []).map(r => ({
            pedido: r.id_pedido, establecimiento: r.establecimiento,
            cliente: r.cliente, total: `$${r.total?.toLocaleString('es-AR')}`, duracion: `${r.duracion_min} min`
          }))}
          loading={loading.rapidos}
        />

        <Widget
          title="Top Productos (> 100 uds o local calif > 4.5)"
          source="NEO4J + MONGODB"
          columns={['Producto', 'Establecimiento', 'Unidades', 'Calif. est.']}
          rows={(data.top || []).map(r => ({
            producto: r.producto, establecimiento: r.establecimiento,
            unidades: r.unidades,
            calificacion: r.calificacion_establecimiento != null ? `${r.calificacion_establecimiento} ⭐` : '—'
          }))}
          loading={loading.top}
        />
      </div>
    </Layout>
  )
}
