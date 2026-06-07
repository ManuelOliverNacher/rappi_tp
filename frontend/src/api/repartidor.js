import api from './client.js'

export const getEstadoRepartidor = () =>
  api.get('/repartidor/estado').then(r => r.data)

export const marcarDisponible = () =>
  api.post('/repartidor/disponible').then(r => r.data)

export const marcarOcupado = () =>
  api.post('/repartidor/ocupado').then(r => r.data)

export const getPedidosRepartidor = () =>
  api.get('/repartidor/pedidos').then(r => r.data)

export const tomarPedido = (id_pedido) =>
  api.post(`/repartidor/pedido/${id_pedido}/tomar`).then(r => r.data)

export const actualizarEstadoEntrega = (id_pedido, estado, observacion) =>
  api.put(`/repartidor/pedido/${id_pedido}/estado`, { estado, observacion }).then(r => r.data)

export const getCalificacionesRep = () =>
  api.get('/repartidor/calificaciones').then(r => r.data)
