import React from 'react'

export default function StatCard({ label, value, sub, color = 'text-rappi' }) {
  return (
    <div className="bg-sidebar border border-gray-700 rounded-xl p-4">
      <div className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      {sub && <div className="text-gray-500 text-xs mt-1">{sub}</div>}
    </div>
  )
}
