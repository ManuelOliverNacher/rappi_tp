# 🛵 Rappi TP - Ingeniería de Datos II

TP integrador que usa 5 bases de datos en simultáneo:
- **PostgreSQL** (Supabase) - datos transaccionales
- **MongoDB** (Atlas) - catálogos y calificaciones
- **Cassandra** (Astra DB) - estados del pedido
- **Neo4j** (Aura) - grafo de relaciones
- **Redis** (Redis Cloud) - cache, sesiones, concurrencia

## Setup

1. Pedile a Manuel el archivo `.env` y el `secure-connect-rappi-db.zip`
2. Ponelos en la carpeta del proyecto
3. Ejecutá:

```bash
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary pymongo cassandra-driver neo4j redis python-dotenv
python3 connections.py
```

Si ves los 5 ✅, estás listo.

## Estructura

```
rappi_tp/
├── main.py              # Menú principal con login por rol
├── connections.py        # Conexiones a las 5 bases
├── schema/              # Scripts de creación de tablas
└── use_cases/           # Casos de uso por rol
    ├── auth.py
    ├── cliente.py
    ├── establecimiento.py
    ├── repartidor.py
    └── admin.py
```

## Cómo ejecutar

```bash
python3 main.py
```

## Equipo

UADE - Ingeniería de Datos IIßß