# Rappi TP - Ingeniería de Datos II (UADE)

TP integrador que simula una app de delivery conectada a **5 bases de datos en simultáneo**.

## Stack de bases de datos

| Base       | Proveedor    | Uso principal                                    |
|------------|--------------|--------------------------------------------------|
| PostgreSQL | Supabase     | Datos transaccionales (pedidos, pagos, usuarios) |
| MongoDB    | Atlas        | Catálogos de productos, calificaciones           |
| Cassandra  | Astra DB     | Timeline de estados de pedido (REST API)         |
| Neo4j      | Aura         | Grafo de relaciones entre entidades              |
| Redis      | Redis Cloud  | Cache, sesiones, carrito, locks distribuidos     |

## Estructura del proyecto

```
rappi_tp/
├── main.py              # CLI con login por rol
├── app_web.py           # UI web con Streamlit (alternativa al CLI)
├── api_server.py        # Backend FastAPI (REST JSON para el frontend)
├── connections.py       # Fábrica de conexiones a las 5 bases
├── frontend/            # UI React + Vite (consume api_server)
│   ├── src/
│   │   ├── pages/       # Login, cliente, establecimiento, repartidor, admin
│   │   ├── api/         # Clientes HTTP por módulo
│   │   └── components/  # Componentes reutilizables
│   └── package.json
├── schema/
│   ├── postgres_init.sql
│   ├── cassandra_init.cql
│   ├── run_postgres.py
│   ├── run_mongo.py
│   ├── run_cassandra.py
│   └── run_neo4j.py
└── use_cases/
    ├── auth.py
    ├── cliente.py
    ├── establecimiento.py
    ├── repartidor.py
    └── admin.py
```

## Setup inicial

1. Pedile a un compañero el archivo `.env` y el `secure-connect-rappi-db.zip`
2. Ponelos en la raíz del proyecto
3. Crear entorno virtual e instalar dependencias:

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

pip install psycopg2-binary pymongo cassandra-driver neo4j redis python-dotenv \
            streamlit fastapi uvicorn bcrypt
```

4. Verificar las 5 conexiones:

```bash
python connections.py
# Debe mostrar 5 ✅
```

## Cómo correr

### Opción A — CLI (consola)

```bash
python main.py
```

### Opción B — Web con Streamlit

```bash
streamlit run app_web.py
# Abre en http://localhost:8501
```

### Opción C — Frontend React + API (recomendado)

Requiere dos terminales:

**Terminal 1 — Backend FastAPI:**
```bash
uvicorn api_server:app --reload --port 8000
# API en http://localhost:8000
```

**Terminal 2 — Frontend Vite:**
```bash
cd frontend
npm install   # solo la primera vez
npm run dev
# Abre en http://localhost:5173
```

## Credenciales de prueba

| Rol              | Email               | Password   |
|------------------|---------------------|------------|
| Admin (hardcoded)| `admin`             | `admin1234`|
| Clientes seed    | `manu@test.com`     | `test123`  |
|                  | `fiona@test.com`    | `test123`  |
|                  | `lucho@test.com`    | `test123`  |
| Establecimientos | `sushi@test.com`    | `test123`  |
|                  | `bk@test.com`       | `test123`  |
|                  | `farmacia@test.com` | `test123`  |
| Repartidores     | `juan@test.com`     | `test123`  |
|                  | `maria@test.com`    | `test123`  |
|                  | `carlos@test.com`   | `test123`  |

> Los datos de prueba se cargan desde el panel Admin → "Cargar datos de prueba"

## Variables de entorno requeridas (`.env`)

```env
# PostgreSQL (Supabase)
PG_CONNECTION_STRING=postgresql://...

# MongoDB Atlas
MONGO_CONNECTION_STRING=mongodb+srv://...
MONGO_DATABASE=rappi

# Cassandra (Astra DB) — REST API
ASTRA_TOKEN=AstraCS:...
ASTRA_KEYSPACE=rappi

# Neo4j Aura
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Redis Cloud
REDIS_HOST=...
REDIS_PORT=...
REDIS_PASSWORD=...
```

## Notas técnicas

### Cassandra — AstraRestSession
Astra DB Serverless usa protocolo DSE que `cassandra-driver` 3.x no soporta.
Se implementó `AstraRestSession` en `connections.py`: un wrapper que traduce
`session.execute(cql, params)` a llamadas HTTP al endpoint REST v2 de Astra.
Soporta INSERT, SELECT (por partition key) y TRUNCATE sobre `estado_pedido`.

### Patrones clave
- **Lock distribuido**: `SET lock:checkout:cliente:{id} NX EX 10` — evita doble pedido
- **Cache-aside**: catálogos y promos en Redis; invalidación al modificar
- **Multi-DB atómica manual**: confirmar pedido escribe en PostgreSQL → Cassandra → Neo4j → limpia Redis

## Equipo

UADE — Ingeniería de Datos II
