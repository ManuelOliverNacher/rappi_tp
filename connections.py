import os
from dotenv import load_dotenv
import psycopg2
from pymongo import MongoClient
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import json
from neo4j import GraphDatabase
import redis

load_dotenv()

# PostgreSQL
def get_postgres():
    conn = psycopg2.connect(os.getenv("PG_CONNECTION_STRING"))
    return conn

# MongoDB
def get_mongo():
    client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
    db = client[os.getenv("MONGO_DATABASE")]
    return db

# Cassandra
def get_cassandra():
    cloud_config = {
        'secure_connect_bundle': os.getenv("ASTRA_SECURE_BUNDLE")
    }
    auth_provider = PlainTextAuthProvider(
        os.getenv("ASTRA_CLIENT_ID"),
        os.getenv("ASTRA_SECRET")
    )
    cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
    session = cluster.connect(os.getenv("ASTRA_KEYSPACE"))
    return session

# Neo4j
def get_neo4j():
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    return driver

# Redis
def get_redis():
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    return r

# Test de todas las conexiones
def check_all_connections():
    print("\n🔌 Verificando conexiones...\n")

    try:
        conn = get_postgres()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("✅ PostgreSQL conectado")
        conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")

    try:
        db = get_mongo()
        db.command("ping")
        print("✅ MongoDB conectado")
    except Exception as e:
        print(f"❌ MongoDB error: {e}")

    try:
        session = get_cassandra()
        session.execute("SELECT release_version FROM system.local")
        print("✅ Cassandra conectado")
    except Exception as e:
        print(f"❌ Cassandra error: {e}")

    try:
        driver = get_neo4j()
        driver.verify_connectivity()
        print("✅ Neo4j conectado")
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j error: {e}")

    try:
        r = get_redis()
        r.ping()
        print("✅ Redis conectado")
    except Exception as e:
        print(f"❌ Redis error: {e}")

    print("\n✨ Listo!\n")

if __name__ == "__main__":
    check_all_connections()