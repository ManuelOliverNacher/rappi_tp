import api from './client.js'

export const verificarConexiones = () =>
  api.get('/admin/conexiones').then(r => r.data)

export const cargarSeed = () =>
  api.post('/admin/seed').then(r => r.data)

export const limpiarBases = () =>
  api.delete('/admin/bases').then(r => r.data)

export const reporteCiudades = () =>
  api.get('/admin/reporte/ciudades').then(r => r.data)

export const reporteProductos = () =>
  api.get('/admin/reporte/productos').then(r => r.data)

export const reporteRestaurantes = () =>
  api.get('/admin/reporte/restaurantes').then(r => r.data)

export const reporteFinde = () =>
  api.get('/admin/reporte/finde').then(r => r.data)

export const reporteRapidos = () =>
  api.get('/admin/reporte/rapidos').then(r => r.data)

export const reporteTopProductos = () =>
  api.get('/admin/reporte/top-productos').then(r => r.data)
