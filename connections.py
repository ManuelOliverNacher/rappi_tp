import os
from dotenv import load_dotenv

load_dotenv()

# Compatibilidad para Cassandra en Python 3.12+
# IMPORTANTE: tiene que ir ANTES del import de cassandra.cluster
# porque ese import carga 'asyncore' que no existe en Python 3.12+
CASSANDRA_CONNECTION_CLASS = None
if os.getenv("USE_ASYNCIO_CASSANDRA", "false").lower() == "true":
    try:
        from cassandra.io.asyncioreactor import AsyncioConnection
        CASSANDRA_CONNECTION_CLASS = AsyncioConnection
    except ImportError:
        pass

import psycopg2
from pymongo import MongoClient
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import json
from neo4j import GraphDatabase
import redis

load_dotenv()

# Compatibilidad para Cassandra en Python 3.12+
# Se activa solo si la variable USE_ASYNCIO_CASSANDRA esta en "true"
CASSANDRA_CONNECTION_CLASS = None
if os.getenv("USE_ASYNCIO_CASSANDRA", "false").lower() == "true":
    try:
        from cassandra.io.asyncioreactor import AsyncioConnection
        CASSANDRA_CONNECTION_CLASS = AsyncioConnection
    except ImportError:
        pass

def get_postgres():
    conn = psycopg2.connect(os.getenv("PG_CONNECTION_STRING"))
    return conn


def get_mongo():
    client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
    db = client[os.getenv("MONGO_DATABASE")]
    return db


def get_cassandra():
    cloud_config = {
        'secure_connect_bundle': os.getenv("ASTRA_SECURE_BUNDLE")
    }
    auth_provider = PlainTextAuthProvider(
        os.getenv("ASTRA_CLIENT_ID"),
        os.getenv("ASTRA_SECRET")
    )
    kwargs = {
        "cloud": cloud_config,
        "auth_provider": auth_provider,
        "protocol_version": 4
    }
    if CASSANDRA_CONNECTION_CLASS:
        kwargs["connection_class"] = CASSANDRA_CONNECTION_CLASS
    cluster = Cluster(**kwargs)
    session = cluster.connect(os.getenv("ASTRA_KEYSPACE"))
    return session


def get_neo4j():
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
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