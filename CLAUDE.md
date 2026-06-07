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

Credenciales en `.env` (no commiteado). Cassandra requiere `secure-connect-rappi-db.zip` en la raíz.

## Estructura de archivos

```
rappi_tp/
├── main.py              # Menú CLI con login por rol
├── app_web.py           # UI web con Streamlit (alternativa al CLI)
├── api_server.py        # Backend FastAPI — expone toda la lógica como REST JSON
├── connections.py       # Fábrica de conexiones a las 5 bases
├── frontend/            # SPA React + Vite que consume api_server en :8000
│   └── src/api/         # auth.js, cliente.js, establecimiento.js, repartidor.js, admin.js
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
cliente(id_cliente PK, nombre, email, password_hash, telefono, ciudad)
direccion(id_direccion PK, id_cliente FK, calle, numero, ciudad, provincia)
establecimiento(id_establecimiento PK, nombre, email, password_hash, ciudad, tipo)
  → restaurante(id_establecimiento PK FK, tipo_cocina, horario)
  → tienda(id_establecimiento PK FK, categoria)
repartidor(id_repartidor PK, nombre, email, password_hash, vehiculo, disponible)
pedido(id_pedido PK, id_cliente FK, id_establecimiento FK, id_repartidor FK,
       estado, fecha_hora, total, tiempo_entrega_min, direccion_entrega)
detalle_pedido(id_pedido FK, id_producto, nombre_producto, cantidad, precio_unitario)
pago(id_pago PK, id_pedido FK, metodo, monto, estado, fecha_hora)
promocion(id_promocion PK, id_establecimiento FK, codigo, descuento_porcentaje,
          fecha_inicio, fecha_fin, uso_maximo, usos_actuales)
promocion_pedido(id_pedido FK, id_promocion FK)
```
Índices en: `fecha_hora`, `id_cliente`, `id_establecimiento`, fechas de promociones.

## Cassandra

Tabla única:
```cql
estado_pedido(id_pedido UUID, fecha_hora TIMESTAMP, estado TEXT)
PRIMARY KEY (id_pedido, fecha_hora) WITH CLUSTERING ORDER BY (fecha_hora DESC)
```
Se usa para el historial de transiciones de estado de cada pedido.

## MongoDB (3 colecciones)

- **catalogo**: `{ establecimiento_id, nombre, descripcion, precio, disponible, categoria, atributos:{} }`  
  Atributos dinámicos según categoría (rolls, entrada, principal, postre, bebida, medicamento, etc.)
- **calificaciones**: `{ id_pedido, id_cliente, id_establecimiento, id_repartidor, nota_establecimiento, nota_repartidor, comentario, respuesta_establecimiento, fecha }`
- **historial**: mirror de pedidos para consultas documentales

## Neo4j (nodos y relaciones)

**Nodos**: `Cliente`, `Establecimiento`, `Repartidor`, `Pedido`, `Producto`  
**Relaciones**:
- `(Cliente)-[:REALIZO]->(Pedido)`
- `(Pedido)-[:CONTIENE]->(Producto)`
- `(Producto)-[:OFRECIDO_POR]->(Establecimiento)`
- `(Repartidor)-[:ENTREGO]->(Pedido)`
- `(Cliente)-[:CALIFICO {nota}]->(Establecimiento)`
- `(Cliente)-[:CALIFICO {nota}]->(Repartidor)`

Constraints en: `Cliente.id`, `Establecimiento.id`, `Producto.id`, `Pedido.id`, `Repartidor.id`.

## Redis (patrones de uso)

| Key pattern                        | Uso                                          |
|------------------------------------|----------------------------------------------|
| `session:{id_usuario}`             | Sesión activa (TTL 10 min)                   |
| `carrito:{id_cliente}`             | Hash con productos del carrito               |
| `catalogo:{id_establecimiento}`    | Cache del catálogo (JSON, TTL variable)      |
| `promo:{codigo}`                   | Cache de promociones válidas                 |
| `lock:pedido:{id_cliente}`         | Anti-double-click (NX + TTL corto)           |
| `repartidores_disponibles`         | Set con IDs de repartidores libres           |

## Patrones arquitecturales clave

1. **Operación confirmar pedido** (multi-DB atómica manual):  
   PostgreSQL (pedido + detalle + pago) → Cassandra (estado "creado") → Neo4j (relaciones) → Redis (limpia carrito + lock)

2. **Lock distribuido**: `SET lock:pedido:{id} NX EX 5` para evitar doble click en confirmación y doble asignación de repartidor.

3. **Cache-aside**: catálogos y promociones se guardan en Redis; se invalidan al modificar. Si Redis miss → busca en MongoDB/Postgres.

4. **Seed data** (`admin.py`): inserta 3 clientes, 3 establecimientos, 3 repartidores, 12 pedidos con estados variados, 2 promociones en todas las bases.

## Cómo correr

```bash
cd rappi_tp
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install psycopg2-binary pymongo cassandra-driver neo4j redis python-dotenv streamlit fastapi uvicorn bcrypt
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
CASSANDRA_CLIENT_ID=...
CASSANDRA_CLIENT_SECRET=...
# + secure-connect-rappi-db.zip en la raíz del proyecto

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
- **SELECT**: usa path-based URL `/keyspaces/rappi/{table}/{id_pedido}` — la forma correcta para buscar por partition key en Astra REST v2. Aplica sort por `fecha_hora DESC` y LIMIT en Python para respetar el clustering order de Cassandra.
- **INSERT**: serializa datetimes con `.isoformat() + "Z"` (Astra requiere UTC explícito), y `None` como `null` JSON.
- **TRUNCATE**: elimina todas las filas vía DELETE iterativo.

**Estado actual**: PostgreSQL ✅ MongoDB ✅ Neo4j ✅ Redis ✅ Cassandra ✅ (REST API)

**Endpoint REST**: `https://2e7d5d41-c9b7-45c0-8218-d63ca04c4471-us-east-2.apps.astra.datastax.com/api/rest/v2`  
**Auth**: header `X-Cassandra-Token` con `ASTRA_TOKEN` del `.env`

### Rows de Cassandra son dicts
`AstraRestSession` devuelve dicts crudos del JSON de la API REST. Todo el código en `use_cases/` que antes usaba acceso por atributo (`row.estado`, `row.fecha_hora`) fue migrado a acceso por clave (`row["estado"]`, `row.get("fecha_hora")`).

### Otros
- `bcrypt` se usa para hashing de passwords en `auth.py` y `api_server.py`.
- `secure-connect-rappi-db.zip` puede estar en la raíz pero no se usa (el driver nativo fue reemplazado por REST).
