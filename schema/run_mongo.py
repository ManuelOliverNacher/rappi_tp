import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connections import get_mongo

def run_schema():
    print("🍃 Ejecutando schema de MongoDB...\n")

    db = get_mongo()

    # Borramos colecciones existentes para arrancar limpio
    for col in ["catalogo_establecimientos", "calificaciones", "historial_pedidos"]:
        if col in db.list_collection_names():
            db[col].drop()
            print(f"   🗑️  {col} eliminada")

    # CATALOGO ESTABLECIMIENTOS
    db.create_collection("catalogo_establecimientos")
    db.catalogo_establecimientos.create_index("tipo")
    db.catalogo_establecimientos.create_index("catalogo.categoria")
    db.catalogo_establecimientos.create_index("catalogo.id_producto", unique=True)

    # CALIFICACIONES
    db.create_collection("calificaciones")
    db.calificaciones.create_index("id_cliente")
    db.calificaciones.create_index("id_establecimiento")
    db.calificaciones.create_index("id_repartidor")
    db.calificaciones.create_index("calificacion_establecimiento.puntaje")

    # HISTORIAL PEDIDOS
    db.create_collection("historial_pedidos")
    db.historial_pedidos.create_index("id_cliente")
    db.historial_pedidos.create_index("fecha")

    print("\n✅ Schema creado correctamente\n")

    # Verificar
    colecciones = db.list_collection_names()
    print(f"📋 Colecciones en la base '{db.name}' ({len(colecciones)}):")
    for c in sorted(colecciones):
        count = db[c].count_documents({})
        indexes = len(list(db[c].list_indexes()))
        print(f"   • {c}  ({count} docs, {indexes} índices)")

if __name__ == "__main__":
    run_schema()