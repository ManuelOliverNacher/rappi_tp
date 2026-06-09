# Rappi TP — Ingeniería de Datos II (UADE)

Trabajo práctico integrador que simula una aplicación de delivery con **persistencia políglota**: 5 bases de datos corriendo simultáneamente, cada una resolviendo el problema para el que fue diseñada.

**Equipo:** Manuel Oliver Nacher · Fiona Pardo · Luciano Frasca · Matias Vilches · Tomas Zocchi

---

## Stack tecnológico

### Bases de datos

| Base       | Proveedor    | Rol en el sistema                                         |
|------------|--------------|-----------------------------------------------------------|
| PostgreSQL | Supabase     | Transacciones ACID: pedidos, pagos, usuarios, promociones |
| MongoDB    | Atlas        | Catálogos de productos (schema flexible) y calificaciones |
| Cassandra  | Astra DB     | Historial de estados de cada pedido (serie temporal)      |
| Neo4j      | Aura         | Grafo de relaciones cliente → pedido → producto → local   |
| Redis      | Redis Cloud  | Sesiones, carrito, caché de catálogos, locks distribuidos |

### Aplicación

| Capa       | Tecnología                              |
|------------|-----------------------------------------|
| Backend    | Python · FastAPI · Uvicorn              |
| Frontend   | React 18 · Vite · Tailwind CSS · Axios |
| CLI / Web  | Python · Streamlit                      |

---

## Estructura del proyecto

```
rappi_tp/
├── .env                    # Credenciales (no commiteado)
├── secure-connect-rappi-db.zip  # Bundle Astra (no commiteado)
│
├── main.py                 # Interfaz CLI con menú por rol
├── app_web.py              # Interfaz web alternativa (Streamlit)
├── api_server.py           # Backend REST (FastAPI) — consumido por el frontend
├── connections.py          # Fábrica de conexiones a las 5 bases
│
├── frontend/               # SPA React + Vite
│   └── src/
│       ├── api/            # Clientes HTTP por módulo (auth, cliente, establecimiento, repartidor, admin)
│       ├── components/     # Layout, Badge, StatCard
│       └── pages/
│           ├── Login.jsx
│           ├── cliente/        # Catalog, Cart, Checkout, MisPedidos, Calificar
│           ├── establecimiento/ # MiCatalogo, Pedidos, PedidosPendientes, Calificaciones, Promociones
│           ├── repartidor/     # Dashboard, Calificaciones
│           └── admin/          # System, Analytics
│
├── schema/
│   ├── postgres_init.sql   # DDL completo de PostgreSQL
│   ├── cassandra_init.cql  # Tabla estado_pedido
│   ├── run_postgres.py     # Inicializa PostgreSQL
│   ├── run_mongo.py        # Crea colecciones e índices en MongoDB
│   ├── run_cassandra.py    # Ejecuta el CQL en Astra
│   └── run_neo4j.py        # Crea constraints e índices en Neo4j
│
└── use_cases/
    ├── auth.py             # Registro, login, sesiones Redis
    ├── cliente.py          # Catálogos, carrito, pedidos, ratings
    ├── establecimiento.py  # CRUD catálogo, gestión pedidos, promos
    ├── repartidor.py       # Disponibilidad, toma y entrega de pedidos
    └── admin.py            # Seed data, reportes, limpieza
```

---

## Setup inicial

### 1. Requisitos previos

- Python 3.9+
- Node.js 18+ y npm
- Acceso a internet (las 5 bases son cloud)

### 2. Clonar y preparar archivos de credenciales

Necesitás dos archivos que **no están en el repositorio**:

- `.env` — variables de entorno con todas las credenciales
- `secure-connect-rappi-db.zip` — bundle de conexión de Astra DB

Copialos a la raíz del proyecto antes de continuar.

### 3. Entorno virtual Python

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
.\venv\Scripts\activate

# Activar (macOS / Linux)
source venv/bin/activate
```

### 4. Instalar dependencias Python

```bash
pip install psycopg2-binary pymongo neo4j redis python-dotenv \
            streamlit fastapi uvicorn bcrypt pydantic requests
```

### 5. Verificar las 5 conexiones

```bash
python connections.py
```

La salida esperada es:

```
PostgreSQL conectado
MongoDB conectado
Cassandra conectado
Neo4j conectado
Redis conectado
```

Si alguna falla, verificá que el `.env` esté en la raíz y que las credenciales sean correctas.

---

## Cómo correr la aplicación

### Opción A — Frontend React + API (recomendado para demo)

Requiere **dos terminales abiertas al mismo tiempo**.

**Terminal 1 — Backend FastAPI:**
```bash
uvicorn api_server:app --reload --port 8000
```
La API queda disponible en `http://localhost:8000`.
Podés explorar todos los endpoints en `http://localhost:8000/docs`.

**Terminal 2 — Frontend Vite:**
```bash
cd frontend
npm install       # solo la primera vez
npm run dev
```
La UI queda disponible en `http://localhost:5173`.

---

### Opción B — CLI (consola)

```bash
python main.py
```

Mostrará un menú interactivo por rol: Cliente, Establecimiento, Repartidor o Admin.

---

### Opción C — Web con Streamlit

```bash
streamlit run app_web.py
```

Se abre automáticamente en `http://localhost:8501`.

---

## Cargar datos de prueba

La primera vez que corrés la app, las bases están vacías. Para poblarlas:

1. Entrá al frontend con usuario `admin` / password `admin1234`
2. Ir a **Admin → Sistema**
3. Hacer click en **"Cargar datos de prueba"**

Esto inserta clientes, establecimientos, repartidores y pedidos en todas las bases simultáneamente.

---

## Credenciales de prueba

| Rol              | Email               | Password   |
|------------------|---------------------|------------|
| Admin (hardcoded)| `admin`             | `admin1234`|
| Cliente          | `manu@test.com`     | `test123`  |
| Cliente          | `fiona@test.com`    | `test123`  |
| Cliente          | `lucho@test.com`    | `test123`  |
| Establecimiento  | `sushi@test.com`    | `test123`  |
| Establecimiento  | `bk@test.com`       | `test123`  |
| Establecimiento  | `farmacia@test.com` | `test123`  |
| Repartidor       | `juan@test.com`     | `test123`  |
| Repartidor       | `maria@test.com`    | `test123`  |
| Repartidor       | `carlos@test.com`   | `test123`  |

---

## Variables de entorno (`.env`)

El archivo `.env` debe estar en la raíz del proyecto con la siguiente estructura:

```env
# PostgreSQL (Supabase)
PG_CONNECTION_STRING=postgresql://usuario:password@host:5432/postgres

# MongoDB Atlas
MONGO_CONNECTION_STRING=mongodb+srv://usuario:password@cluster.mongodb.net/
MONGO_DATABASE=rappi

# Cassandra (Astra DB) — se usa REST API, no driver nativo
ASTRA_TOKEN=AstraCS:...
ASTRA_KEYSPACE=rappi

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Redis Cloud
REDIS_HOST=...
REDIS_PORT=...
REDIS_PASSWORD=...
```

---

## Inicializar los schemas desde cero

Si necesitás recrear las estructuras en las bases (por ejemplo, en una cuenta nueva):

```bash
# PostgreSQL — crea todas las tablas e índices
python schema/run_postgres.py

# MongoDB — crea colecciones e índices
python schema/run_mongo.py

# Cassandra — crea la tabla estado_pedido
python schema/run_cassandra.py

# Neo4j — crea constraints e índices de grafo
python schema/run_neo4j.py
```

---

## Arquitectura y flujos clave

### Flujo de un pedido completo

Cuando un cliente confirma un pedido, el sistema escribe en **4 bases en secuencia**:

```
1. PostgreSQL  → INSERT pedido + detalle_pedido + pago
2. Cassandra   → INSERT estado "creado" con timestamp
3. Neo4j       → CREATE nodo Pedido + relaciones REALIZO / CONTIENE
4. Redis       → DEL carrito:cliente:{id}  +  DEL lock:pedido:{id}
```

### Flujo de entrega (repartidor)

```
Tomar pedido:
  Redis      → SET lock:repartidor:asignacion:{id_pedido} NX EX 5
  PostgreSQL → UPDATE pedido SET id_repartidor + UPDATE repartidor SET disponibilidad=false
  Cassandra  → INSERT estado "repartidor_asignado"
  Redis      → SMOVE repartidores:disponibles → repartidores:ocupados

Entregar pedido:
  Cassandra  → INSERT estado "entregado"
  Redis      → SMOVE repartidores:ocupados → repartidores:disponibles
  PostgreSQL → UPDATE repartidor SET disponibilidad=true
  Neo4j      → CREATE (Repartidor)-[:ENTREGO]->(Pedido)
```

### Patrones de Redis

| Key                                    | Tipo   | TTL      | Uso                              |
|----------------------------------------|--------|----------|----------------------------------|
| `session:{token}`                      | String | 10 min   | Sesión activa                    |
| `carrito:cliente:{id}`                 | Hash   | 2 hs     | Carrito en curso                 |
| `catalogo:establecimiento:{id}`        | String | 1 hora   | Caché de catálogo (cache-aside)  |
| `establecimientos:lista`               | String | 1 hora   | Caché de lista de establecimientos|
| `promo:{codigo}`                       | String | variable | Caché de promoción válida        |
| `lock:pedido:{id_cliente}`             | String | 5 seg    | Anti-doble-click en checkout     |
| `lock:repartidor:asignacion:{id}`      | String | 5 seg    | Anti-doble-asignación            |
| `repartidores:disponibles`             | Set    | —        | IDs de repartidores libres       |
| `repartidores:ocupados`                | Set    | —        | IDs con pedido activo            |

### Cassandra — AstraRestSession

Astra DB Serverless usa protocolo DSE que `cassandra-driver` 3.x no soporta nativamente. Se implementó `AstraRestSession` en `connections.py`, un wrapper que:

- Expone la misma interfaz que `cassandra.cluster.Session` (`session.execute(cql, params)`)
- Traduce internamente INSERT y SELECT a llamadas HTTP al endpoint REST v2 de Astra
- Ordena los resultados por `fecha_hora DESC` en Python para respetar el clustering order
- Serializa timestamps con `.isoformat() + "Z"` (Astra requiere UTC explícito)

---

## Reportes disponibles (Admin → Analytics)

| Reporte | Bases usadas | Descripción |
|---------|-------------|-------------|
| Pedidos por ciudad | PostgreSQL | COUNT y SUM por ciudad y fecha |
| Productos más pedidos | Neo4j | Suma de cantidades por producto |
| Locales más populares | Neo4j | Pedidos + calificación promedio |
| Categorías en fines de semana | PostgreSQL + MongoDB | DOW IN (0,6) cruzado con categorías del catálogo |
| Pedidos rápidos y caros | PostgreSQL + Cassandra | Total alto + duración < 30 min (creado → entregado) |
| Top productos | Neo4j + MongoDB | Más de 100 unidades O calificación promedio > 4.5 |

---

## Vistas por rol

### Cliente
- **Catálogos** — browse establecimientos y productos (MongoDB + Redis cache)
- **Carrito** — hash en Redis con soporte de código de descuento
- **Checkout** — confirma pedido multi-DB, selecciona dirección y método de pago
- **Mis Pedidos** — historial con estados expandibles desde Cassandra
- **Calificar** — rating 1–5 para establecimiento y repartidor → MongoDB + Neo4j

### Establecimiento
- **Mi Catálogo** — CRUD de productos en MongoDB (paginado)
- **Pedidos Pendientes** — solo pedidos en estado "creado"
- **Todos los Pedidos** — cambio de estado: aceptado → preparando → listo_para_retirar
- **Calificaciones** — reseñas recibidas con promedio y opción de respuesta
- **Promociones** — crear códigos de descuento con período de validez y monto mínimo

### Repartidor
- **Dashboard** — disponibilidad, pedidos disponibles para tomar, cambio de estado de entrega
- **Calificaciones** — reseñas recibidas con nombre del cliente y promedio

### Admin
- **Sistema** — verificación en tiempo real de las 5 conexiones + seed data
- **Analytics** — 6 reportes cruzando las distintas bases, con exportación a CSV
