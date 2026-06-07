import api from './client.js'

export const login = (email, password, rol) =>
  api.post('/auth/login', { email, password, rol }).then(r => r.data)

export const logout = () =>
  api.post('/auth/logout').then(r => r.data)

export const registerCliente = (data) =>
  api.post('/auth/register/cliente', data).then(r => r.data)

export const registerEstablecimiento = (data) =>
  api.post('/auth/register/establecimiento', data).then(r => r.data)

export const registerRepartidor = (data) =>
  api.post('/auth/register/repartidor', data).then(r => r.data)
