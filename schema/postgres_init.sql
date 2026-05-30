-- ============================================
-- RAPPI TP - PostgreSQL Schema
-- ============================================

-- Borramos todo si existe (para poder re-correr el script)
DROP TABLE IF EXISTS promocion_pedido CASCADE;
DROP TABLE IF EXISTS pago CASCADE;
DROP TABLE IF EXISTS detalle_pedido CASCADE;
DROP TABLE IF EXISTS pedido CASCADE;
DROP TABLE IF EXISTS promocion CASCADE;
DROP TABLE IF EXISTS direccion CASCADE;
DROP TABLE IF EXISTS cliente CASCADE;
DROP TABLE IF EXISTS restaurante CASCADE;
DROP TABLE IF EXISTS tienda CASCADE;
DROP TABLE IF EXISTS establecimiento CASCADE;
DROP TABLE IF EXISTS repartidor CASCADE;

-- ============================================
-- CLIENTE
-- ============================================
CREATE TABLE cliente (
    id_cliente SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    telefono VARCHAR(30),
    fecha_registro DATE DEFAULT CURRENT_DATE,
    password VARCHAR(255) NOT NULL
);

-- ============================================
-- DIRECCION (múltiples por cliente)
-- ============================================
CREATE TABLE direccion (
    id_cliente INT NOT NULL,
    nro_direccion INT NOT NULL,
    calle VARCHAR(150) NOT NULL,
    numero VARCHAR(20),
    ciudad VARCHAR(100) NOT NULL,
    cp VARCHAR(20),
    alias VARCHAR(50),
    PRIMARY KEY (id_cliente, nro_direccion),
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente) ON DELETE CASCADE
);

-- ============================================
-- ESTABLECIMIENTO (jerarquía: restaurante o tienda)
-- ============================================
CREATE TABLE establecimiento (
    id_establecimiento SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    telefono VARCHAR(30),
    horario VARCHAR(100),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('restaurante', 'tienda')),
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE restaurante (
    id_establecimiento INT PRIMARY KEY,
    especialidad_culinaria VARCHAR(100),
    FOREIGN KEY (id_establecimiento) REFERENCES establecimiento(id_establecimiento) ON DELETE CASCADE
);

CREATE TABLE tienda (
    id_establecimiento INT PRIMARY KEY,
    rubro VARCHAR(100),
    FOREIGN KEY (id_establecimiento) REFERENCES establecimiento(id_establecimiento) ON DELETE CASCADE
);

-- ============================================
-- REPARTIDOR
-- ============================================
CREATE TABLE repartidor (
    id_repartidor SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    vehiculo VARCHAR(50),
    disponibilidad BOOLEAN DEFAULT true,
    telefono VARCHAR(30),
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- ============================================
-- PEDIDO
-- ============================================
CREATE TABLE pedido (
    id_pedido SERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10, 2) NOT NULL,
    id_cliente INT NOT NULL,
    id_establecimiento INT NOT NULL,
    id_repartidor INT,
    id_cliente_dir INT NOT NULL,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente) ON DELETE CASCADE,
    FOREIGN KEY (id_establecimiento) REFERENCES establecimiento(id_establecimiento),
    FOREIGN KEY (id_repartidor) REFERENCES repartidor(id_repartidor) ON DELETE SET NULL,
    FOREIGN KEY (id_cliente, id_cliente_dir) REFERENCES direccion(id_cliente, nro_direccion)
);
-- ============================================
-- DETALLE_PEDIDO
-- ============================================
CREATE TABLE detalle_pedido (
    id_pedido INT NOT NULL,
    id_producto VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (id_pedido, id_producto),
    FOREIGN KEY (id_pedido) REFERENCES pedido(id_pedido) ON DELETE CASCADE
);

-- ============================================
-- PAGO
-- ============================================
CREATE TABLE pago (
    id_pago SERIAL PRIMARY KEY,
    id_pedido INT NOT NULL,
    monto DECIMAL(10, 2) NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metodo VARCHAR(50) NOT NULL,
    estado VARCHAR(30) DEFAULT 'pendiente',
    FOREIGN KEY (id_pedido) REFERENCES pedido(id_pedido) ON DELETE CASCADE
);

-- ============================================
-- PROMOCION
-- ============================================
CREATE TABLE promocion (
    id_promocion SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    descripcion VARCHAR(255),
    descuento DECIMAL(5, 2) NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    monto_minimo DECIMAL(10, 2) DEFAULT 0,
    condiciones VARCHAR(255),
    creada_por VARCHAR(100)
);

CREATE TABLE promocion_pedido (
    id_promocion INT NOT NULL,
    id_pedido INT NOT NULL,
    descuento_aplicado DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (id_promocion, id_pedido),
    FOREIGN KEY (id_promocion) REFERENCES promocion(id_promocion),
    FOREIGN KEY (id_pedido) REFERENCES pedido(id_pedido) ON DELETE CASCADE
);

-- ============================================
-- ÍNDICES para mejorar consultas
-- ============================================
CREATE INDEX idx_pedido_fecha ON pedido(fecha_hora);
CREATE INDEX idx_pedido_cliente ON pedido(id_cliente);
CREATE INDEX idx_pedido_establecimiento ON pedido(id_establecimiento);
CREATE INDEX idx_promocion_fechas ON promocion(fecha_inicio, fecha_fin);