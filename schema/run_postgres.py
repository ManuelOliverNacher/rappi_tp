import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connections import get_postgres

def run_schema():
    print("🐘 Ejecutando schema de PostgreSQL...\n")

    # Leer el archivo SQL
    schema_path = os.path.join(os.path.dirname(__file__), "postgres_init.sql")
    with open(schema_path, "r") as f:
        sql = f.read()

    # Conectarse y ejecutar
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        print("✅ Schema creado correctamente\n")

        # Verificar las tablas creadas
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tablas = cur.fetchall()
        print(f"📋 Tablas en la base ({len(tablas)}):")
        for t in tablas:
            print(f"   • {t[0]}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_schema()