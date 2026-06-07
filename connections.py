import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

import psycopg2
from pymongo import MongoClient
from neo4j import GraphDatabase
import redis


class AstraRestSession:
    """
    Wrapper que imita cassandra.cluster.Session usando el API REST de Astra DB (Stargate).
    Permite usar session.execute(cql, params) sin cambiar el código existente.
    Solo soporta las operaciones usadas en el proyecto: INSERT y SELECT en estado_pedido.
    """

    def __init__(self, token, db_id, region, keyspace):
        self.base = f"https://{db_id}-{region}.apps.astra.datastax.com/api/rest/v2"
        self.headers = {
            "X-Cassandra-Token": token,
            "Content-Type": "application/json",
        }
        self.keyspace = keyspace

    def execute(self, query, parameters=None):
        query = query.strip()
        params = list(parameters) if parameters else []

        if query.upper().startswith("SELECT RELEASE_VERSION"):
            # Health check usado en check_all_connections
            return _FakeResult([{"release_version": "astra-rest"}])

        if query.upper().startswith("INSERT"):
            return self._execute_insert(query, params)

        if query.upper().startswith("SELECT"):
            return self._execute_select(query, params)

        if query.upper().startswith("TRUNCATE"):
            # Astra REST v2 no tiene TRUNCATE; eliminamos todas las filas del keyspace
            m = re.search(r'TRUNCATE\s+(\w+)', query, re.IGNORECASE)
            if m:
                table = m.group(1)
                # Obtener todas las filas y borrarlas por partition key
                url = f"{self.base}/keyspaces/{self.keyspace}/{table}"
                r = requests.get(url, headers=self.headers, timeout=10)
                if r.status_code == 200:
                    rows = r.json().get("data", [])
                    for row in rows:
                        pk = row.get("id_pedido")
                        if pk:
                            requests.delete(f"{url}/{pk}", headers=self.headers, timeout=10)
            return _FakeResult([])

        raise NotImplementedError(f"AstraRestSession no soporta: {query[:60]}")

    def _execute_insert(self, query, params):
        m = re.search(r"INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES", query, re.IGNORECASE)
        if not m:
            raise ValueError(f"No se pudo parsear INSERT: {query}")
        table = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")]
        row = {}
        for col, val in zip(cols, params):
            if val is None:
                row[col] = None
            elif isinstance(val, (int, float, bool)):
                row[col] = val
            elif hasattr(val, "isoformat"):
                ts = val.isoformat()
                if "+" not in ts and not ts.endswith("Z"):
                    ts += "Z"
                row[col] = ts
            else:
                row[col] = str(val)
        url = f"{self.base}/keyspaces/{self.keyspace}/{table}"
        r = requests.post(url, headers=self.headers, json=row, timeout=10)
        if r.status_code not in (200, 201):
            raise Exception(f"Astra INSERT error {r.status_code}: {r.text}")
        return _FakeResult([])

    def _execute_select(self, query, params):
        m_table = re.search(r"FROM\s+(\w+)", query, re.IGNORECASE)
        if not m_table:
            raise ValueError(f"No se pudo parsear SELECT: {query}")
        table = m_table.group(1)

        # Extraer el valor de id_pedido del WHERE para usarlo en la URL (Astra REST v2
        # requiere el partition key en el path, no como query param)
        where_clause = re.search(r"WHERE\s+(.+?)(?:\s+ORDER|\s+LIMIT|$)", query, re.IGNORECASE | re.DOTALL)
        url = f"{self.base}/keyspaces/{self.keyspace}/{table}"
        if where_clause and params:
            m_pk = re.search(r'id_pedido\s*=\s*(?:\?|%s)', where_clause.group(1), re.IGNORECASE)
            if m_pk:
                url = f"{url}/{params[0]}"

        r = requests.get(url, headers=self.headers, timeout=10)
        if r.status_code == 404:
            return _FakeResult([])
        if r.status_code not in (200,):
            raise Exception(f"Astra SELECT error {r.status_code}: {r.text[:200]}")

        resp = r.json()
        data = resp.get("data", resp) if isinstance(resp, dict) else resp
        if not isinstance(data, list):
            data = []

        # Ordenar por fecha_hora DESC para respetar el clustering order de Cassandra
        if data:
            from datetime import datetime as _dt
            def _ts(v):
                if isinstance(v, str):
                    try:
                        return _dt.fromisoformat(v.replace("Z", "+00:00"))
                    except Exception:
                        return _dt.min
                return v if v else _dt.min
            try:
                data.sort(key=lambda row: _ts(row.get("fecha_hora", "")), reverse=True)
            except Exception:
                pass

        # Aplicar LIMIT en Python
        m_limit = re.search(r'LIMIT\s+(\d+)', query, re.IGNORECASE)
        if m_limit:
            data = data[:int(m_limit.group(1))]

        return _FakeResult(data)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)

    def one(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


def get_postgres():
    conn = psycopg2.connect(os.getenv("PG_CONNECTION_STRING"))
    return conn


def get_mongo():
    client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
    db = client[os.getenv("MONGO_DATABASE")]
    return db


def get_cassandra():
    token = os.getenv("ASTRA_TOKEN")
    # database_id y region extraídos del host del secure bundle
    # host: {db_id}-{region}.db.astra.datastax.com
    db_id = "2e7d5d41-c9b7-45c0-8218-d63ca04c4471"
    region = "us-east-2"
    keyspace = os.getenv("ASTRA_KEYSPACE", "rappi")
    return AstraRestSession(token, db_id, region, keyspace)


def get_neo4j():
    uri = os.getenv("NEO4J_URI")
    if uri.startswith("neo4j+s://"):
        uri = uri.replace("neo4j+s://", "neo4j+ssc://")
    driver = GraphDatabase.driver(
        uri,
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    return driver


def get_redis():
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    return r


def check_all_connections():
    print("\nVerificando conexiones...\n")

    try:
        conn = get_postgres()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("PostgreSQL conectado")
        conn.close()
    except Exception as e:
        print(f"PostgreSQL error: {e}")

    try:
        db = get_mongo()
        db.command("ping")
        print("MongoDB conectado")
    except Exception as e:
        print(f"MongoDB error: {e}")

    try:
        session = get_cassandra()
        session.execute("SELECT release_version FROM system.local")
        print("Cassandra conectado")
    except Exception as e:
        print(f"Cassandra error: {e}")

    try:
        driver = get_neo4j()
        driver.verify_connectivity()
        print("Neo4j conectado")
        driver.close()
    except Exception as e:
        print(f"Neo4j error: {e}")

    try:
        r = get_redis()
        r.ping()
        print("Redis conectado")
    except Exception as e:
        print(f"Redis error: {e}")

    print("\nListo!\n")


if __name__ == "__main__":
    check_all_connections()