import React from 'react'

const ESTADO_STYLES = {
  creado:               'bg-blue-900 text-blue-300 border border-blue-700',
  aceptado:             'bg-yellow-900 text-yellow-300 border border-yellow-700',
  preparando:           'bg-orange-900 text-orange-300 border border-orange-700',
  listo_para_retirar:   'bg-green-900 text-green-300 border border-green-700',
  repartidor_asignado:  'bg-purple-900 text-purple-300 border border-purple-700',
  en_camino:            'bg-purple-900 text-purple-300 border border-purple-700',
  entregado:            'bg-emerald-900 text-emerald-300 border border-emerald-700',
  cancelado:            'bg-red-900 text-red-300 border border-red-700',
  desconocido:          'bg-gray-700 text-gray-300 border border-gray-600',
}

export default function Badge({ estado }) {
  const style = ESTADO_STYLES[estado?.toLowerCase()] || ESTADO_STYLES.desconocido
  const label = (estado || 'desconocido').replace(/_/g, ' ').toUpperCase()
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${style}`}>
      {label}
    </span>
  )
}
