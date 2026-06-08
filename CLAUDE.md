# CLAUDE.md — Rappi TP (Ingeniería de Datos II, UADE)

Proyecto académico que simula una app de delivery conectada a **5 bases de datos simultáneas**. Tiene tres interfaces: CLI (`main.py`), web Streamlit (`app_web.py`) y frontend React (`frontend/`) con backend FastAPI (`api_server.py`).

## Stack

| Base         | Proveedor      | Uso principal                                      |
|--------------|----------------|----------------------------------------------------|
| PostgreSQL   | Supabase       | Datos transaccionales (pedidos, pagos, usuarios)   |
| MongoDB      | Atlas          | Catálogos de productos, calificaciones, historial  |
| Cassandra    | Astra DB       | Timeline de estados de pedido                      |
| Neo4j        | Aura           | Grafo de relaciones (cliente→pedido→producto→local)|
| Redis        | Redis Cloud    | Cache, sesiones, carrito, locks distribuidos        |

Credenciales en `.env` (no commiteado). Cassandra requiere `secure-connect-rappi-db.zip` en la raíz (no se usa actualmente — reemplazado por REST API).

## Estructura de archivos

```
rappi_tp/
├── main.py              # Menú CLI con login por rol
├── app_web.py           # UI web con Streamlit (alternativa al CLI)
├── api_server.py        # Backend FastAPI — expone toda la lógica como REST JSON
├── connections.py       # Fábrica de conexiones a las 5 bases
├── frontend/            # SPA React + Vite que consume api_server en :8000
│   └── src/
│       ├── api/         # auth.js, cliente.js, establecimiento.js, repartidor.js
│       ├── components/  # Layout.jsx, Badge.jsx, StatCard.jsx
│       └── pages/
│           ├── Login.jsx
│           ├── cliente/        # Catalog, Cart, Checkout, MisPedidos, Calificar
│           ├── establecimiento/ # MiCatalogo, Pedidos, PedidosPendientes,
│           │                    # Calificaciones, Promociones
│           ├── repartidor/     # Dashboard, Calificaciones
│           └── admin/          # System, Analytics
├── schema/
│   ├── postgres_init.sql     # DDL completo con cascade deletes
│   ├── cassandra_init.cql    # Tabla estado_pedido (clustered DESC)
│   ├── run_postgres.py       # Ejecuta el SQL y verifica tablas
│   ├── run_mongo.py          # Crea colecciones e índices
│   ├── run_cassandra.py      # Parsea y ejecuta CQL
│   └── run_neo4j.py          # Crea constraints e índices
└── use_cases/
    ├── auth.py               # Registro + login + sesiones Redis
    ├── cliente.py            # Catálogos, carrito, pedidos, ratings
    ├── establecimiento.py    # Catálogo, gestión de pedidos, promos
    ├── repartidor.py         # Disponibilidad, toma de pedidos, entrega
    └── admin.py              # Seed data, reportes, limpieza de bases
```

## Roles y contraseñas

- **Cliente / Establecimiento / Repartidor**: se registran en la app
- **Admin hardcodeado**: usuario `admin`, password `admin1234`
- **Test users** (Streamlit): password `test123`

## Esquema PostgreSQL (tablas principales)

```
cliente(id_cliente PK, nombre, apellido, email, password, telefono, ciudad)
direccion(id_cliente FK, nro_direccion, calle, numero, ciudad, cp, alias)
  PRIMARY KEY (id_cliente, nro_direccion)
establecimiento(id_establecimiento PK, nombre, email, password, ciudad, tipo)
  → restaurante(id_establecimiento PK FK, tipo_cocina, horario)
  → tienda(id_establecimiento PK FK, categoria)
repartidor(id_repartidor PK, nombre, apellido, email, password, vehiculo, disponibilidad)
pedido(id_pedido PK, id_cliente FK, id_establecimiento FK, id_repartidor FK,
       fecha_hora, total, id_cliente_dir FK)
detalle_pedido(id_pedido FK, id_producto, cantidad, precio_unitario, subtotal)
pago(id_pago PK, id_pedido FK, metodo, monto, estado, fecha)
promocion(id_promocion PK, codigo UNIQUE, descripcion, descuento,
          fecha_inicio, fecha_fin, monto_minimo, condiciones, creada_por)
promocion_pedido(id_promocion FK, id_pedido FK)
```
Índices en: `fecha_hora`, `id_cliente`, `id_establecimiento`, fechas de promociones.

## Cassandra

Tabla única:
```cql
estado_pedido(id_pedido INT, fecha_hora TIMESTAMP, estado TEXT, observacion TEXT)
PRIMARY KEY (id_pedido, fecha_hora) WITH CLUSTERING ORDER BY (fecha_hora DESC)
```
Se usa para el historial de transiciones de estado de cada pedido. Clustering DESC permite obtener el estado más reciente en LIMIT 1.

## MongoDB (3 colecciones)

- **catalogo_establecimientos**: `{ _id: id_establecimiento, nombre, tipo, catalogo: [{id_producto, nombre, precio, categoria, disponible, atributos:{}}] }`
  Atributos dinámicos según categoría (rolls, entrada, principal, postre, bebida, medicamento, etc.)
- **calificaciones**: `{ _id, id_pedido, id_cliente, id_establecimiento, id_repartidor, calificacion_establecimiento:{puntaje, comentario, respuesta_establecimiento}, calificacion_repartidor:{puntaje, comentario}, fecha }`
- **historial**: mirror de pedidos para consultas documentales

## Neo4j (nodos y relaciones)

**Nodos**: `Cliente`, `Establecimiento`, `Repartidor`, `Pedido`, `Producto`
**Relaciones**:
- `(Cliente)-[:REALIZO]->(Pedido)`
- `(Pedido)-[:CONTIENE {cantidad}]->(Producto)`
- `(Producto)-[:OFRECIDO_POR]->(Establecimiento)`
- `(Repartidor)-[:ENTREGO]->(Pedido)`
- `(Cliente)-[:CALIFICO {nota}]->(Establecimiento)`
- `(Cliente)-[:CALIFICO {nota}]->(Repartidor)`

Constraints en: `Cliente.id`, `Establecimiento.id`, `Producto.id`, `Pedido.id`, `Repartidor.id`.

## Redis (patrones de uso)

| Key pattern                             | Tipo   | Uso                                          |
|-----------------------------------------|--------|----------------------------------------------|
| `session:{token}`                       | String | Sesión activa (TTL 10 min)                   |
| `carrito:cliente:{id}`                  | Hash   | Productos del carrito + metadata promo       |
| `catalogo:establecimiento:{id}`         | String | Cache del catálogo (JSON, TTL variable)      |
| `promo:{codigo}`                        | String | Cache de promociones válidas                 |
| `lock:pedido:{id_cliente}`              | String | Anti-double-click en confirmación (NX + EX 5)|
| `lock:repartidor:asignacion:{id_pedido}`| String | Anti-doble-asignación de repartidor (NX + EX 5)|
| `repartidores:disponibles`             | Set    | IDs de repartidores libres                   |
| `repartidores:ocupados`                | Set    | IDs de repartidores con pedido activo        |

## Patrones arquitecturales clave

1. **Operación confirmar pedido** (multi-DB manual):
   PostgreSQL (pedido + detalle + pago) → Cassandra (estado "creado") → Neo4j (relaciones grafo) → Redis (limpia carrito + libera lock)

2. **Operación tomar pedido** (repartidor):
   Redis (lock anti-duplicado) → PostgreSQL (asigna id_repartidor) → PostgreSQL (disponibilidad=false) → Cassandra (estado "repartidor_asignado") → Redis (mueve a set ocupados)

3. **Operación entregar pedido**:
   Cassandra (estado "entregado") → Redis (smove ocupados→disponibles) → PostgreSQL (disponibilidad=true) → Neo4j (relación ENTREGO)

4. **Lock distribuido**: `SET key NX EX 5` — si la clave ya existe, la operación falla. Previene doble confirmación y doble asignación.

5. **Cache-aside**: catálogos y promociones se leen de Redis; si miss → MongoDB/Postgres. Se invalida al modificar.

6. **Seed data** (`admin.py`): inserta 3 clientes, 3 establecimientos, 3 repartidores, 12 pedidos con estados variados en todas las bases simultáneamente.

## Vistas del frontend (por rol)

### Cliente
- **Catálogos**: browse establecimientos y productos desde MongoDB
- **Carrito**: hash en Redis, soporta código de descuento
- **Checkout**: confirma pedido → operación multi-DB
- **Mis Pedidos**: historial con estados desde Cassandra (expandible por pedido)
- **Calificar**: rating 1–5 para establecimiento y repartidor → MongoDB + Neo4j

### Establecimiento
- **Mi Catálogo**: CRUD de productos en MongoDB (paginado)
- **Pedidos Pendientes**: solo pedidos en estado "creado"
- **Todos los Pedidos**: gestión de estados (aceptado → preparando → listo_para_retirar)
- **Calificaciones**: reseñas recibidas con nombre del cliente, promedio, respuesta
- **Promociones**: creación de códigos de descuento → PostgreSQL + Redis

### Repartidor
- **Dashboard**: disponibilidad, pedidos disponibles (listo_para_retirar), pedidos asignados con cambio de estado
- **Calificaciones**: reseñas recibidas con nombre del cliente y promedio

### Admin
- **Sistema**: verificación de las 5 conexiones en tiempo real
- **Analytics**: reportes desde PostgreSQL, MongoDB, Cassandra y Neo4j

## Cómo correr

```bash
cd rappi_tp
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install psycopg2-binary pymongo cassandra-driver neo4j redis python-dotenv streamlit fastapi uvicorn bcrypt pydantic
python connections.py            # Verifica las 5 conexiones (debe mostrar 5 ✅)
python main.py                   # CLI
streamlit run app_web.py         # Web Streamlit

# Frontend React (requiere dos terminales):
uvicorn api_server:app --reload --port 8000   # Terminal 1 — API en :8000
cd frontend && npm install && npm run dev      # Terminal 2 — UI en :5173
```

## Variables de entorno requeridas (`.env`)

```
# PostgreSQL (Supabase)
POSTGRES_HOST=...
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_PORT=5432

# MongoDB Atlas
MONGO_URI=mongodb+srv://...

# Cassandra (Astra DB)
ASTRA_TOKEN=...
ASTRA_DB_ID=...
ASTRA_REGION=...
# secure-connect-rappi-db.zip en la raíz (no se usa, reemplazado por REST)

# Neo4j Aura
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Redis Cloud
REDIS_HOST=...
REDIS_PORT=...
REDIS_PASSWORD=...
```

## Notas de compatibilidad

### Cassandra — AstraRestSession (REST API en lugar de CQL nativo)
Astra DB Serverless usa protocolo DSE que `cassandra-driver` 3.x no soporta. Se implementó `AstraRestSession` en `connections.py`:
- Misma interfaz que `cassandra.cluster.Session`: `session.execute(cql, params)`
- **SELECT**: usa path-based URL `/keyspaces/rappi/{table}/{id_pedido}`. Aplica sort por `fecha_hora DESC` y LIMIT en Python.
- **INSERT**: serializa datetimes con `.isoformat() + "Z"` (Astra requiere UTC explícito), y `None` como `null` JSON.
- **TRUNCATE**: elimina todas las filas vía DELETE iterativo.
- **Health check**: usa `SELECT id_pedido FROM estado_pedido LIMIT 1` (no `system.local`).

**Estado actual**: PostgreSQL ✅ MongoDB ✅ Neo4j ✅ Redis ✅ Cassandra ✅ (REST API)

**Endpoint REST**: `https://{ASTRA_DB_ID}-{ASTRA_REGION}.apps.astra.datastax.com/api/rest/v2`
**Auth**: header `X-Cassandra-Token` con `ASTRA_TOKEN` del `.env`

### Rows de Cassandra son dicts
`AstraRestSession` devuelve dicts crudos del JSON de la API REST. El código accede por clave: `row["estado"]`, `row.get("observacion")`.

### Validaciones Pydantic
Los modelos usan `from pydantic import BaseModel, Field`:
- `CalificarBody.puntaje_*`: `Field(ge=1, le=5)` — solo acepta 1 a 5
- `PromocionBody.codigo`: `Field(max_length=20)`, `.descuento`: `Field(gt=0, le=100)`

### Seguridad de rutas (frontend)
`ProtectedRoute` en `router.jsx` valida sesión Y rol. Un usuario autenticado con rol incorrecto es redirigido a su home (`/catalog`, `/establishment/catalog`, etc.) en lugar de ver una página rota.

### Otros
- `bcrypt` se usa para hashing de passwords.
- Passwords: mínimo implícito por bcrypt; validación de rango en ratings y promociones via Pydantic Field.
