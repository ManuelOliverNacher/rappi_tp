import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connections import get_cassandra

def run_schema():
    print("🟧 Ejecutando schema de Cassandra...\n")

    schema_path = os.path.join(os.path.dirname(__file__), "cassandra_init.cql")
    with open(schema_path, "r") as f:
        sql = f.read()

    statements = [s.strip() for s in sql.split(";") if s.strip()]

    session = get_cassandra()
    try:
        for stmt in statements:
            lines = [l for l in stmt.split("\n") if not l.strip().startswith("--")]
            clean_stmt = "\n".join(lines).strip()
            if clean_stmt:
                session.execute(clean_stmt)
        print("✅ Schema creado correctamente\n")

        rows = session.execute("""
            SELECT table_name FROM system_schema.tables
            WHERE keyspace_name = 'rappi';
        """)
        tablas = list(rows)
        print(f"📋 Tablas en el keyspace 'rappi' ({len(tablas)}):")
        for t in tablas:
            print(f"   • {t.table_name}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.shutdown()

if __name__ == "__main__":
    run_schema()