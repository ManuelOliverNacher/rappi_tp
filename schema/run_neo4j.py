import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connections import get_neo4j

def run_schema():
    print("🔵 Ejecutando schema de Neo4j...\n")

    driver = get_neo4j()

    constraints = [
        "CREATE CONSTRAINT cliente_id IF NOT EXISTS FOR (c:Cliente) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT establecimiento_id IF NOT EXISTS FOR (e:Establecimiento) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT producto_id IF NOT EXISTS FOR (p:Producto) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT repartidor_id IF NOT EXISTS FOR (r:Repartidor) REQUIRE r.id IS UNIQUE",
        "CREATE CONSTRAINT pedido_id IF NOT EXISTS FOR (p:Pedido) REQUIRE p.id IS UNIQUE",
    ]

    indexes = [
        "CREATE INDEX cliente_ciudad IF NOT EXISTS FOR (c:Cliente) ON (c.ciudad)",
        "CREATE INDEX establecimiento_tipo IF NOT EXISTS FOR (e:Establecimiento) ON (e.tipo)",
        "CREATE INDEX producto_categoria IF NOT EXISTS FOR (p:Producto) ON (p.categoria)",
        "CREATE INDEX pedido_fecha IF NOT EXISTS FOR (p:Pedido) ON (p.fecha)",
    ]

    try:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("   🗑️  Grafo limpiado\n")

            for c in constraints:
                session.run(c)
            print(f"✅ {len(constraints)} constraints creadas")

            for i in indexes:
                session.run(i)
            print(f"✅ {len(indexes)} índices creados\n")

            result = session.run("SHOW CONSTRAINTS")
            cons = list(result)
            print(f"📋 Constraints activos ({len(cons)}):")
            for c in cons:
                print(f"   • {c['name']}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    run_schema()