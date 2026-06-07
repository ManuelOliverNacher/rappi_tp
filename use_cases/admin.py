"""
Casos de uso del rol ADMIN.
Reportes y mantenimiento del sistema.
"""
from connections import get_postgres, get_mongo, get_redis, get_cassandra, get_neo4j


# ============================================
# CARGAR DATOS DE PRUEBA (placeholder por ahora)
# ============================================
def cargar_datos_prueba():
    """Carga datos de prueba realistas en las 5 bases manteniendo consistencia."""
    print("\nCARGAR DATOS DE PRUEBA\n")
    print("Esto va a cargar:")
    print("  - 3 clientes con direcciones en distintas ciudades")
    print("  - 3 establecimientos (Sushi Club, Burger King, Farmacia Doc) con catalogos")
    print("  - 3 repartidores")
    print("  - 12 pedidos en distintos estados")
    print("  - Calificaciones en pedidos entregados")
    print("  - 2 promociones")
    print("\nADVERTENCIA: si ya cargaste datos, esto puede generar conflictos.")
    print("Es mejor correr primero 'Limpiar TODAS las bases'.\n")

    confirm = input("Continuar? (s/n): ").strip().lower()
    if confirm != "s":
        print("\nCancelado")
        input("\nPresione Enter para continuar...")
        return

    print("\nCargando...\n")

    import bcrypt
    import json
    import uuid
    from datetime import datetime, timedelta

    def hp(p):
        return bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # ============================================
    # POSTGRES: clientes, direcciones, establecimientos, repartidores, promociones
    # ============================================
    conn = get_postgres()
    cur = conn.cursor()

    # CLIENTES
    clientes = [
        ("Manuel", "Oliver", "manu@test.com", "1162822101", hp("test123")),
        ("Fiona", "Garcia", "fiona@test.com", "1145678901", hp("test123")),
        ("Lucho", "Perez", "lucho@test.com", "1198765432", hp("test123")),
    ]
    ids_clientes = []
    for c in clientes:
        cur.execute("""
            INSERT INTO cliente (nombre, apellido, email, telefono, password)
            VALUES (%s, %s, %s, %s, %s) RETURNING id_cliente
        """, c)
        ids_clientes.append(cur.fetchone()[0])
    print(f"  Postgres: {len(ids_clientes)} clientes creados")

    # DIRECCIONES (varias por cliente, distintas ciudades)
    direcciones = [
        (ids_clientes[0], 1, "Cotagaita", "1690", "Ramos Mejia", "1704", "Casa"),
        (ids_clientes[0], 2, "Av. Corrientes", "1234", "CABA", "1043", "Trabajo"),
        (ids_clientes[1], 1, "Belgrano", "5678", "CABA", "1067", "Casa"),
        (ids_clientes[2], 1, "Mitre", "234", "La Plata", "1900", "Casa"),
        (ids_clientes[2], 2, "9 de Julio", "789", "CABA", "1058", "Oficina"),
    ]
    for d in direcciones:
        cur.execute("""
            INSERT INTO direccion (id_cliente, nro_direccion, calle, numero, ciudad, cp, alias)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, d)
    print(f"  Postgres: {len(direcciones)} direcciones creadas")

    # ESTABLECIMIENTOS
    establecimientos = [
        ("Sushi Club", "Lima 123", "1123435678", "Lun-Vie 13-23", "restaurante", "sushi@test.com", hp("test123"), "Japonesa"),
        ("Burger King", "Av. Cabildo 4000", "1144556677", "Todos los dias 11-23", "restaurante", "bk@test.com", hp("test123"), "Hamburguesas"),
        ("Farmacia Doc", "Santa Fe 2500", "1155667788", "24hs", "tienda", "farmacia@test.com", hp("test123"), "Farmacia"),
    ]
    ids_estab = []
    nombres_estab = []
    tipos_estab = []
    for e in establecimientos:
        nombre, dir_, tel, hor, tipo, email, pwd, extra = e
        cur.execute("""
            INSERT INTO establecimiento (nombre, direccion, telefono, horario, tipo, email, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_establecimiento
        """, (nombre, dir_, tel, hor, tipo, email, pwd))
        id_e = cur.fetchone()[0]
        ids_estab.append(id_e)
        nombres_estab.append(nombre)
        tipos_estab.append(tipo)
        if tipo == "restaurante":
            cur.execute("INSERT INTO restaurante (id_establecimiento, especialidad_culinaria) VALUES (%s, %s)",
                        (id_e, extra))
        else:
            cur.execute("INSERT INTO tienda (id_establecimiento, rubro) VALUES (%s, %s)", (id_e, extra))
    print(f"  Postgres: {len(ids_estab)} establecimientos creados")

    # REPARTIDORES
    repartidores = [
        ("Juan", "Lopez", "moto", True, "1166778899", "juan@test.com", hp("test123")),
        ("Maria", "Gomez", "bici", True, "1177889900", "maria@test.com", hp("test123")),
        ("Carlos", "Diaz", "auto", True, "1188990011", "carlos@test.com", hp("test123")),
    ]
    ids_rep = []
    nombres_rep = []
    for r in repartidores:
        cur.execute("""
            INSERT INTO repartidor (nombre, apellido, vehiculo, disponibilidad, telefono, email, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_repartidor
        """, r)
        ids_rep.append(cur.fetchone()[0])
        nombres_rep.append(r[0])
    print(f"  Postgres: {len(ids_rep)} repartidores creados")

    # PROMOCIONES
    hoy = datetime.now().date()
    promos = [
        ("VERANO20", "20% off en restaurantes", 20.0, hoy - timedelta(days=10), hoy + timedelta(days=30), 1000.0, "Solo para restaurantes", "admin"),
        ("ENVIOGRATIS", "Envio gratis", 100.0, hoy - timedelta(days=5), hoy + timedelta(days=60), 500.0, "Cualquier categoria", "admin"),
    ]
    ids_promos = []
    for p in promos:
        cur.execute("""
            INSERT INTO promocion (codigo, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo, condiciones, creada_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_promocion
        """, p)
        ids_promos.append(cur.fetchone()[0])
    print(f"  Postgres: {len(ids_promos)} promociones creadas")

    conn.commit()

    # ============================================
    # MONGO: catalogos
    # ============================================
    db = get_mongo()

    productos_sushi = [
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Roll California", "precio": 4500, "categoria": "rolls", "descripcion": "Palta, kanikama, queso", "disponible": True, "atributos": {"piezas": 8, "picante": "no", "sin_tacc": "si"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Roll Salmon", "precio": 5200, "categoria": "rolls", "descripcion": "Salmon, palta, queso", "disponible": True, "atributos": {"piezas": 8, "picante": "no", "sin_tacc": "si"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Gyoza", "precio": 3200, "categoria": "entrada", "descripcion": "Empanaditas japonesas", "disponible": True, "atributos": {"porciones": 6, "vegetariano": "no"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Coca Cola", "precio": 1800, "categoria": "bebida", "descripcion": "Botella 500ml", "disponible": True, "atributos": {"ml": 500, "alcohol": "no"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Mochi de chocolate", "precio": 2500, "categoria": "postre", "descripcion": "3 unidades", "disponible": True, "atributos": {"porciones": 3, "sin_azucar": "no"}},
    ]
    productos_bk = [
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Whopper", "precio": 6500, "categoria": "principal", "descripcion": "Hamburguesa clasica", "disponible": True, "atributos": {"porciones": 1, "ingredientes": "carne, tomate, lechuga, cebolla"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Doble Whopper", "precio": 8500, "categoria": "principal", "descripcion": "Doble carne", "disponible": True, "atributos": {"porciones": 1}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Papas medianas", "precio": 2800, "categoria": "entrada", "descripcion": "Papas fritas", "disponible": True, "atributos": {"porciones": 1}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Pepsi", "precio": 1500, "categoria": "bebida", "descripcion": "Lata 354ml", "disponible": True, "atributos": {"ml": 354, "alcohol": "no"}},
    ]
    productos_farma = [
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Ibuprofeno 400mg", "precio": 2200, "categoria": "medicamento", "descripcion": "10 comprimidos", "disponible": True, "atributos": {"marca": "Actron", "requiere_receta": "no"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Alcohol en gel", "precio": 1500, "categoria": "higiene", "descripcion": "250ml", "disponible": True, "atributos": {"marca": "Algabo", "contenido": "250ml"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Vitamina C", "precio": 3500, "categoria": "suplemento", "descripcion": "30 comprimidos efervescentes", "disponible": True, "atributos": {"marca": "Bayer"}},
    ]

    db.catalogo_establecimientos.insert_many([
        {"_id": ids_estab[0], "nombre": nombres_estab[0], "tipo": tipos_estab[0], "catalogo": productos_sushi},
        {"_id": ids_estab[1], "nombre": nombres_estab[1], "tipo": tipos_estab[1], "catalogo": productos_bk},
        {"_id": ids_estab[2], "nombre": nombres_estab[2], "tipo": tipos_estab[2], "catalogo": productos_farma},
    ])
    print(f"  Mongo: 3 catalogos cargados con {len(productos_sushi) + len(productos_bk) + len(productos_farma)} productos en total")

    # ============================================
    # PEDIDOS: armamos 12 pedidos variados
    # ============================================
    session = get_cassandra()
    driver = get_neo4j()

    # Configuracion: lista de pedidos a generar
    # (id_cliente, id_direccion, id_establecimiento, productos_y_cantidades, dias_atras, estado_final)
    pedidos_a_crear = [
        # Lunes pasado
        (0, 1, 0, [(0, 2), (3, 1)], 7, "entregado"),
        # Sabado pasado (finde)
        (1, 1, 1, [(0, 1), (2, 1), (3, 2)], 6, "entregado"),
        # Domingo pasado (finde)
        (0, 1, 1, [(1, 1)], 5, "entregado"),
        # Sabado pasado (finde)
        (2, 1, 0, [(0, 1), (4, 2)], 5, "entregado"),
        # Hace 4 dias
        (1, 1, 2, [(0, 1), (1, 1)], 4, "entregado"),
        # Hace 3 dias
        (0, 2, 0, [(1, 2), (4, 1)], 3, "entregado"),
        # Hace 2 dias
        (2, 2, 1, [(0, 1), (3, 1)], 2, "en_camino"),
        # Ayer
        (1, 1, 0, [(2, 2)], 1, "listo_para_retirar"),
        # Hoy
        (0, 1, 2, [(0, 1)], 0, "preparando"),
        # Hoy
        (2, 1, 1, [(0, 1), (2, 1)], 0, "creado"),
        # Hoy
        (1, 1, 1, [(1, 1), (2, 1), (3, 1)], 0, "entregado"),
        # Hoy
        (0, 1, 0, [(0, 1)], 0, "creado"),
    ]

    catalogos_por_estab = [productos_sushi, productos_bk, productos_farma]

    print(f"  Generando {len(pedidos_a_crear)} pedidos...")

    estados_intermedios = {
        "creado": ["creado"],
        "preparando": ["creado", "aceptado", "preparando"],
        "listo_para_retirar": ["creado", "aceptado", "preparando", "listo_para_retirar"],
        "en_camino": ["creado", "aceptado", "preparando", "listo_para_retirar", "repartidor_asignado", "en_camino"],
        "entregado": ["creado", "aceptado", "preparando", "listo_para_retirar", "repartidor_asignado", "en_camino", "entregado"],
    }

    for idx_p, (idx_cli, nro_dir, idx_est, prods, dias_atras, estado_final) in enumerate(pedidos_a_crear):
        id_cli = ids_clientes[idx_cli]
        id_est = ids_estab[idx_est]
        nombre_est = nombres_estab[idx_est]
        catalogo = catalogos_por_estab[idx_est]

        # Calcular total
        items = []
        total = 0
        for idx_prod, cant in prods:
            prod = catalogo[idx_prod]
            subtotal = prod["precio"] * cant
            total += subtotal
            items.append({"prod": prod, "cant": cant, "subtotal": subtotal})

        # Fecha del pedido
        fecha_pedido = datetime.now() - timedelta(days=dias_atras, hours=2)

        # Si el pedido esta avanzado, asignar repartidor
        id_repartidor = None
        if estado_final in ("en_camino", "entregado"):
            id_repartidor = ids_rep[idx_p % len(ids_rep)]

        # Insertar pedido en Postgres
        cur.execute("""
            INSERT INTO pedido (fecha_hora, total, id_cliente, id_establecimiento, id_repartidor, id_cliente_dir)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_pedido
        """, (fecha_pedido, total, id_cli, id_est, id_repartidor, nro_dir))
        id_pedido = cur.fetchone()[0]

        # Detalle
        for item in items:
            cur.execute("""
                INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_pedido, item["prod"]["id_producto"], item["cant"], item["prod"]["precio"], item["subtotal"]))

        # Pago
        estado_pago = "completado" if estado_final == "entregado" else "pendiente"
        cur.execute("""
            INSERT INTO pago (id_pedido, monto, fecha, metodo, estado)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_pedido, total, fecha_pedido, "efectivo", estado_pago))

        # Cassandra: timeline de estados (con timestamps escalonados)
        timeline = estados_intermedios[estado_final]
        # Para pedidos entregados, queremos que tarden distinto: algunos rapidos (< 30 min), otros largos
        if estado_final == "entregado":
            # Pedidos rapidos: 25 minutos en total
            duracion_total_min = 25 if idx_p % 3 == 0 else 75
        else:
            duracion_total_min = 30
        delta = duracion_total_min / max(len(timeline) - 1, 1)
        for i, estado in enumerate(timeline):
            fecha_estado = fecha_pedido + timedelta(minutes=delta * i)
            obs_map = {
                "creado": "Pedido creado por el cliente",
                "aceptado": "Pedido recibido",
                "preparando": "Pedido en elaboracion",
                "listo_para_retirar": "Pedido listo para retirar",
                "repartidor_asignado": f"Tomado por {nombres_rep[idx_p % len(ids_rep)]}" if id_repartidor else None,
                "en_camino": "Saliendo del local",
                "entregado": "Pedido entregado al cliente",
            }
            session.execute("""
                INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
                VALUES (%s, %s, %s, %s)
            """, (id_pedido, fecha_estado, estado, obs_map.get(estado)))

        # Neo4j: nodos y relaciones
        with driver.session() as ses:
            ses.run("MERGE (c:Cliente {id: $id}) SET c.nombre = $nombre",
                    id=id_cli, nombre=clientes[idx_cli][0])
            ses.run("MERGE (e:Establecimiento {id: $id}) SET e.nombre = $nombre, e.tipo = $tipo",
                    id=id_est, nombre=nombre_est, tipo=tipos_estab[idx_est])
            ses.run("MERGE (p:Pedido {id: $id}) SET p.fecha = $fecha, p.total = $total",
                    id=id_pedido, fecha=str(fecha_pedido), total=total)
            ses.run("MATCH (c:Cliente {id: $c}), (p:Pedido {id: $p}) MERGE (c)-[:REALIZO]->(p)",
                    c=id_cli, p=id_pedido)
            for item in items:
                ses.run("""
                    MERGE (pr:Producto {id: $id})
                    SET pr.nombre = $nombre, pr.precio = $precio, pr.categoria = $cat
                """, id=item["prod"]["id_producto"], nombre=item["prod"]["nombre"],
                    precio=item["prod"]["precio"], cat=item["prod"]["categoria"])
                ses.run("""
                    MATCH (p:Pedido {id: $p}), (pr:Producto {id: $pr})
                    MERGE (p)-[r:CONTIENE]->(pr) SET r.cantidad = $cant
                """, p=id_pedido, pr=item["prod"]["id_producto"], cant=item["cant"])
                ses.run("""
                    MATCH (pr:Producto {id: $pr}), (e:Establecimiento {id: $e})
                    MERGE (pr)-[:OFRECIDO_POR]->(e)
                """, pr=item["prod"]["id_producto"], e=id_est)

            if id_repartidor and estado_final == "entregado":
                idx_rep_use = idx_p % len(ids_rep)
                ses.run("MERGE (r:Repartidor {id: $id}) SET r.nombre = $nombre",
                        id=id_repartidor, nombre=nombres_rep[idx_rep_use])
                ses.run("""
                    MATCH (r:Repartidor {id: $r}), (p:Pedido {id: $p})
                    MERGE (r)-[:ENTREGO]->(p)
                """, r=id_repartidor, p=id_pedido)

        # Calificaciones: solo para entregados, una si y una no
        if estado_final == "entregado" and idx_p % 2 == 0:
            puntaje_est_val = 5 if idx_p % 3 == 0 else 4
            puntaje_rep_val = 5 if idx_p % 4 == 0 else 4
            db.calificaciones.insert_one({
                "_id": f"pedido_{id_pedido}",
                "id_cliente": id_cli,
                "id_establecimiento": id_est,
                "id_repartidor": id_repartidor,
                "fecha": fecha_pedido.isoformat(),
                "calificacion_establecimiento": {
                    "puntaje": puntaje_est_val,
                    "comentario": "Todo excelente" if puntaje_est_val == 5 else "Estuvo bien",
                    "respuesta_establecimiento": "Gracias por elegirnos!" if puntaje_est_val == 5 else None
                },
                "calificacion_repartidor": {
                    "puntaje": puntaje_rep_val,
                    "comentario": "Llego rapido y amable" if puntaje_rep_val == 5 else "OK"
                }
            })
            # Neo4j: relacion CALIFICO
            with driver.session() as ses:
                ses.run("""
                    MATCH (c:Cliente {id: $c}), (e:Establecimiento {id: $e})
                    MERGE (c)-[r:CALIFICO]->(e) SET r.puntaje = $p
                """, c=id_cli, e=id_est, p=puntaje_est_val)
                if id_repartidor:
                    ses.run("""
                        MATCH (c:Cliente {id: $c}), (r:Repartidor {id: $r})
                        MERGE (c)-[rel:CALIFICO]->(r) SET rel.puntaje = $p
                    """, c=id_cli, r=id_repartidor, p=puntaje_rep_val)

    conn.commit()
    cur.close()
    conn.close()
    driver.close()

    print(f"  Cassandra: estados de los {len(pedidos_a_crear)} pedidos cargados")
    print(f"  Neo4j: grafo cliente-pedido-producto-establecimiento creado")
    print(f"  Mongo: calificaciones de pedidos entregados cargadas")

    # Redis: estados de repartidores
    r = get_redis()
    for id_r in ids_rep:
        r.sadd("repartidores:disponibles", str(id_r))
    print(f"  Redis: {len(ids_rep)} repartidores marcados como disponibles")

    print("\nDatos de prueba cargados correctamente")
    print("\nUsuarios de prueba (password en todos: test123):")
    print("  Clientes:           manu@test.com, fiona@test.com, lucho@test.com")
    print("  Establecimientos:   sushi@test.com, bk@test.com, farmacia@test.com")
    print("  Repartidores:       juan@test.com, maria@test.com, carlos@test.com")
    print("  Promociones:        VERANO20, ENVIOGRATIS")
    input("\nPresione Enter para continuar...")

# ============================================
# VERIFICAR CONEXIONES
# ============================================
def verificar_conexiones():
    from connections import check_all_connections
    check_all_connections()
    input("\nPresione Enter para continuar...")


# ============================================
# REPORTE 1: PEDIDOS POR CIUDAD
# Postgres puro (JOIN pedido + direccion)
# ============================================
def reporte_pedidos_por_ciudad():
    print("\nREPORTE: PEDIDOS POR CIUDAD\n")

    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.ciudad,
               DATE(p.fecha_hora) as fecha,
               COUNT(*) as cantidad,
               SUM(p.total) as facturacion
        FROM pedido p
        JOIN direccion d ON d.id_cliente = p.id_cliente AND d.nro_direccion = p.id_cliente_dir
        GROUP BY d.ciudad, DATE(p.fecha_hora)
        ORDER BY fecha DESC, cantidad DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        print("No hay pedidos registrados")
        input("\nPresione Enter para continuar...")
        return

    print(f"{'CIUDAD':<25} {'FECHA':<15} {'PEDIDOS':<10} {'FACTURACION':<15}")
    print("-" * 70)
    for ciudad, fecha, cant, fact in rows:
        print(f"{ciudad:<25} {str(fecha):<15} {cant:<10} ${fact}")

    print(f"\nFuente: PostgreSQL (JOIN pedido + direccion)")
    input("\nPresione Enter para continuar...")


# ============================================
# REPORTE 2: PRODUCTOS MAS SOLICITADOS
# Neo4j (cuenta relaciones CONTIENE)
# ============================================
def reporte_productos_mas_solicitados():
    print("\nREPORTE: PRODUCTOS MAS SOLICITADOS\n")

    driver = get_neo4j()
    with driver.session() as ses:
        result = ses.run("""
            MATCH (p:Pedido)-[c:CONTIENE]->(pr:Producto)
            RETURN pr.id AS id, pr.nombre AS nombre,
                   SUM(c.cantidad) AS total_solicitado,
                   COUNT(DISTINCT p) AS pedidos_distintos
            ORDER BY total_solicitado DESC
            LIMIT 10
        """)
        rows = list(result)
    driver.close()

    if not rows:
        print("No hay datos de productos pedidos todavia")
        input("\nPresione Enter para continuar...")
        return

    print(f"{'PRODUCTO':<30} {'UNIDADES':<12} {'PEDIDOS':<10}")
    print("-" * 60)
    for r in rows:
        print(f"{r['nombre']:<30} {r['total_solicitado']:<12} {r['pedidos_distintos']:<10}")

    print(f"\nFuente: Neo4j (relaciones CONTIENE en el grafo)")
    input("\nPresione Enter para continuar...")


# ============================================
# REPORTE 3: RESTAURANTES MAS POPULARES
# Neo4j (cuenta pedidos por establecimiento)
# ============================================
def reporte_restaurantes_populares():
    print("\nREPORTE: RESTAURANTES MAS POPULARES\n")

    driver = get_neo4j()
    with driver.session() as ses:
        result = ses.run("""
            MATCH (p:Pedido)-[:CONTIENE]->(pr:Producto)-[:OFRECIDO_POR]->(e:Establecimiento)
            WITH e, COUNT(DISTINCT p) AS pedidos
            OPTIONAL MATCH (c:Cliente)-[r:CALIFICO]->(e)
            RETURN e.id AS id, e.nombre AS nombre,
                   pedidos,
                   AVG(r.puntaje) AS promedio_calificacion
            ORDER BY pedidos DESC
            LIMIT 10
        """)
        rows = list(result)
    driver.close()

    if not rows:
        print("No hay datos de establecimientos todavia")
        input("\nPresione Enter para continuar...")
        return

    print(f"{'ESTABLECIMIENTO':<30} {'PEDIDOS':<10} {'CALIF PROMEDIO':<15}")
    print("-" * 60)
    for r in rows:
        calif = f"{r['promedio_calificacion']:.2f}" if r['promedio_calificacion'] else "sin calif"
        print(f"{r['nombre']:<30} {r['pedidos']:<10} {calif:<15}")

    print(f"\nFuente: Neo4j (grafo) + calificaciones promedio")
    input("\nPresione Enter para continuar...")


# ============================================
# REPORTE 4: CATEGORIAS MAS PEDIDAS LOS FINDES
# Postgres (filtra dias) + Mongo (categoria del producto)
# ============================================
def reporte_categorias_findes():
    print("\nREPORTE: CATEGORIAS MAS PEDIDAS LOS FINES DE SEMANA\n")

    # Postgres: traer items de pedidos hechos sabados o domingos
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT dp.id_producto, SUM(dp.cantidad) as total
        FROM detalle_pedido dp
        JOIN pedido p ON dp.id_pedido = p.id_pedido
        WHERE EXTRACT(DOW FROM p.fecha_hora) IN (0, 6)
        GROUP BY dp.id_producto
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        print("No hay pedidos los findes todavia")
        input("\nPresione Enter para continuar...")
        return

    # Mongo: para cada producto, ver su categoria
    db = get_mongo()
    categorias = {}
    for id_producto, cantidad in rows:
        doc = db.catalogo_establecimientos.find_one(
            {"catalogo.id_producto": id_producto},
            {"catalogo.$": 1}
        )
        if doc and doc.get("catalogo"):
            cat = doc["catalogo"][0].get("categoria", "sin_categoria")
            categorias[cat] = categorias.get(cat, 0) + int(cantidad)

    if not categorias:
        print("No se pudieron resolver las categorias")
        input("\nPresione Enter para continuar...")
        return

    ranking = sorted(categorias.items(), key=lambda x: x[1], reverse=True)

    print(f"{'CATEGORIA':<25} {'UNIDADES PEDIDAS':<15}")
    print("-" * 45)
    for cat, total in ranking:
        print(f"{cat:<25} {total:<15}")

    print(f"\nFuente: Postgres (filtra dias) + Mongo (categoria del producto)")
    input("\nPresione Enter para continuar...")


# ============================================
# REPORTE 5: PEDIDOS > $50 ENTREGADOS EN < 30 MIN
# Postgres (filtra monto) + Cassandra (calcula tiempo de entrega)
# ============================================
def reporte_rapidos_y_caros():
    print("\nREPORTE: PEDIDOS > $50 ENTREGADOS EN < 30 MINUTOS\n")

    # Postgres: pedidos con total > 50
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre, c.nombre, c.apellido
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.total > 50
        ORDER BY p.fecha_hora DESC
    """)
    candidatos = cur.fetchall()
    cur.close()
    conn.close()

    if not candidatos:
        print("No hay pedidos con total > $50")
        input("\nPresione Enter para continuar...")
        return

    # Cassandra: por cada pedido, calcular tiempo entre 'creado' y 'entregado'
    session = get_cassandra()
    rapidos = []

    for id_pedido, fecha, total, est, c_nom, c_ape in candidatos:
        rows = list(session.execute("""
            SELECT estado, fecha_hora FROM estado_pedido WHERE id_pedido = %s
        """, (id_pedido,)))

        from datetime import datetime as _dt
        def _ts(v):
            if isinstance(v, str):
                return _dt.fromisoformat(v.replace("Z", "+00:00").replace("+0000", "+00:00"))
            return v
        creado = None
        entregado = None
        for r in rows:
            estado_r = r["estado"] if isinstance(r, dict) else r.estado
            fh_r = _ts(r["fecha_hora"]) if isinstance(r, dict) else r.fecha_hora
            if estado_r == "creado":
                creado = fh_r
            elif estado_r == "entregado":
                entregado = fh_r

        if creado and entregado:
            duracion_seg = (entregado - creado).total_seconds()
            duracion_min = duracion_seg / 60
            if duracion_min < 30:
                rapidos.append((id_pedido, est, c_nom, c_ape, total, duracion_min))

    if not rapidos:
        print("Ningun pedido > $50 fue entregado en menos de 30 min")
        print(f"(Total candidatos > $50: {len(candidatos)})")
        input("\nPresione Enter para continuar...")
        return

    print(f"{'PEDIDO':<10} {'ESTABLECIMIENTO':<25} {'CLIENTE':<25} {'TOTAL':<10} {'DURACION':<10}")
    print("-" * 85)
    for id_p, est, n, a, total, dur in rapidos:
        print(f"#{id_p:<9} {est:<25} {n + ' ' + a:<25} ${total:<8} {dur:.1f} min")

    print(f"\nFuente: Postgres (total) + Cassandra (timestamps de estados)")
    input("\nPresione Enter para continuar...")


# ============================================
# REPORTE 6: PRODUCTOS > 100 PEDIDOS OR CALIFICACION > 4.5
# Neo4j (conteo de pedidos) + Mongo (calificaciones del establecimiento)
# ============================================
def reporte_top_productos():
    print("\nREPORTE: PRODUCTOS CON >100 PEDIDOS O CALIF >4.5\n")

    # Neo4j: productos con conteo de cuantas veces fueron pedidos
    driver = get_neo4j()
    with driver.session() as ses:
        result = ses.run("""
            MATCH (p:Pedido)-[c:CONTIENE]->(pr:Producto)-[:OFRECIDO_POR]->(e:Establecimiento)
            RETURN pr.id AS id_producto,
                   pr.nombre AS nombre,
                   e.id AS id_establecimiento,
                   e.nombre AS establecimiento,
                   SUM(c.cantidad) AS unidades
            ORDER BY unidades DESC
        """)
        productos = list(result)
    driver.close()

    if not productos:
        print("No hay productos en el grafo todavia")
        input("\nPresione Enter para continuar...")
        return

    # Mongo: calificacion promedio por establecimiento
    db = get_mongo()
    califs_pipeline = list(db.calificaciones.aggregate([
        {"$group": {
            "_id": "$id_establecimiento",
            "promedio": {"$avg": "$calificacion_establecimiento.puntaje"}
        }}
    ]))
    promedio_por_est = {c["_id"]: c["promedio"] for c in califs_pipeline}

    # Filtrar: >100 pedidos OR promedio_establecimiento > 4.5
    seleccionados = []
    for p in productos:
        unidades = p["unidades"]
        promedio_est = promedio_por_est.get(p["id_establecimiento"], 0)
        if unidades > 100 or promedio_est > 4.5:
            seleccionados.append((p["nombre"], p["establecimiento"], unidades, promedio_est))

    if not seleccionados:
        print("Ningun producto cumple los criterios todavia")
        print(f"(El criterio se cumple cuando hay >100 pedidos del mismo producto o el establecimiento tiene calif >4.5)")
        input("\nPresione Enter para continuar...")
        return

    print(f"{'PRODUCTO':<25} {'ESTABLECIMIENTO':<25} {'UNIDADES':<10} {'CALIF EST':<10}")
    print("-" * 75)
    for nombre, est, unidades, promedio in seleccionados:
        calif_txt = f"{promedio:.2f}" if promedio else "sin calif"
        print(f"{nombre:<25} {est:<25} {unidades:<10} {calif_txt:<10}")

    print(f"\nFuente: Neo4j (conteo de pedidos por producto) + Mongo (calificacion promedio)")
    input("\nPresione Enter para continuar...")


# ============================================
# LIMPIAR TODAS LAS BASES (cuidado!)
# ============================================
def limpiar_todas_las_bases():
    print("\nLIMPIAR TODAS LAS BASES")
    print("\nADVERTENCIA: Esto va a BORRAR TODOS LOS DATOS de las 5 bases.")
    confirm = input("\nEscribi 'BORRAR TODO' para confirmar: ").strip()
    if confirm != "BORRAR TODO":
        print("\nCancelado")
        input("\nPresione Enter para continuar...")
        return

    print("\nLimpiando bases...\n")

    # Postgres: re-ejecutar el script de schema (borra y recrea todas las tablas)
    try:
        import os
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema", "postgres_init.sql")
        with open(schema_path, "r") as f:
            sql = f.read()
        conn = get_postgres()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()
        print("  Postgres limpiado y recreado")
    except Exception as e:
        print(f"  Error Postgres: {e}")

    # Mongo: dropear las colecciones
    try:
        db = get_mongo()
        for col in ["catalogo_establecimientos", "calificaciones", "historial_pedidos"]:
            if col in db.list_collection_names():
                db[col].drop()
        print("  Mongo limpiado")
    except Exception as e:
        print(f"  Error Mongo: {e}")

    # Cassandra: truncate
    try:
        session = get_cassandra()
        session.execute("TRUNCATE estado_pedido")
        print("  Cassandra limpiado")
    except Exception as e:
        print(f"  Error Cassandra: {e}")

    # Neo4j: borrar todos los nodos
    try:
        driver = get_neo4j()
        with driver.session() as ses:
            ses.run("MATCH (n) DETACH DELETE n")
        driver.close()
        print("  Neo4j limpiado")
    except Exception as e:
        print(f"  Error Neo4j: {e}")

    # Redis: flush
    try:
        r = get_redis()
        r.flushdb()
        print("  Redis limpiado")
    except Exception as e:
        print(f"  Error Redis: {e}")

    print("\nTodas las bases limpiadas")
    input("\nPresione Enter para continuar...")