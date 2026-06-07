import api from './client.js'

export const getCatalogoEst = () =>
  api.get('/establecimiento/catalogo').then(r => r.data)

export const agregarProducto = (data) =>
  api.post('/establecimiento/producto', data).then(r => r.data)

export const toggleDisponibilidad = (id_producto, disponible) =>
  api.put(`/establecimiento/producto/${id_producto}/disponibilidad`, { disponible }).then(r => r.data)

export const getPedidosEst = () =>
  api.get('/establecimiento/pedidos').then(r => r.data)

export const cambiarEstadoPedido = (id_pedido, estado, observacion) =>
  api.put(`/establecimiento/pedido/${id_pedido}/estado`, { estado, observacion }).then(r => r.data)

export const getCalificacionesEst = () =>
  api.get('/establecimiento/calificaciones').then(r => r.data)

export const responderCalificacion = (id_calificacion, respuesta) =>
  api.post(`/establecimiento/calificacion/${id_calificacion}/responder`, { respuesta }).then(r => r.data)

export const crearPromocion = (data) =>
  api.post('/establecimiento/promocion', data).then(r => r.data)

export const actualizarProducto = (id_producto, campos) =>
  api.patch(`/establecimiento/producto/${id_producto}`, campos).then(r => r.data)
