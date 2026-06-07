import api from './client.js'

export const getEstablecimientos = () =>
  api.get('/cliente/establecimientos').then(r => r.data)

export const getCatalogo = (id) =>
  api.get(`/cliente/catalogo/${id}`).then(r => r.data)

export const getCarrito = () =>
  api.get('/cliente/carrito').then(r => r.data)

export const agregarAlCarrito = (data) =>
  api.post('/cliente/carrito/agregar', data).then(r => r.data)

export const vaciarCarrito = () =>
  api.delete('/cliente/carrito').then(r => r.data)

export const quitarItemCarrito = (id_producto) =>
  api.delete(`/cliente/carrito/item/${id_producto}`).then(r => r.data)

export const aplicarPromo = (codigo) =>
  api.post('/cliente/promocion/aplicar', { codigo }).then(r => r.data)

export const getDirecciones = () =>
  api.get('/cliente/direcciones').then(r => r.data)

export const agregarDireccion = (data) =>
  api.post('/cliente/direcciones', data).then(r => r.data)

export const confirmarPedido = (nro_direccion, metodo_pago) =>
  api.post('/cliente/pedido/confirmar', { nro_direccion, metodo_pago }).then(r => r.data)

export const getMisPedidos = () =>
  api.get('/cliente/pedidos').then(r => r.data)

export const getEstadosPedido = (id_pedido) =>
  api.get(`/cliente/pedido/${id_pedido}/estados`).then(r => r.data)

export const getPedidosCalificar = () =>
  api.get('/cliente/pedidos/calificar').then(r => r.data)

export const calificarPedido = (data) =>
  api.post('/cliente/pedido/calificar', data).then(r => r.data)

export const getHistorial = () =>
  api.get('/cliente/historial').then(r => r.data)
