"""
Casos de uso del rol CLIENTE.
"""
import json
from connections import get_postgres, get_mongo, get_redis


def pedir_dato(label, requerido=True):
    while True:
        valor = input(f"  {label} (0 para cancelar): ").strip()
        if valor == "0":
            return None
        if valor or not requerido:
            return valor
        print("  Este campo es obligatorio")


# ============================================
# VER CATALOGOS DE ESTABLECIMIENTOS
# ============================================
def ver_catalogos():
    print("\nCATALOGOS DE ESTABLECIMIENTOS\n")

    # Listar establecimientos desde Postgres
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT id_establecimiento, nombre, tipo, direccion
        FROM establecimiento
        ORDER BY nombre
    """)
    establecimientos = cur.fetchall()
    cur.close()
    conn.close()

    if not establecimientos:
        print("No hay establecimientos registrados todavia")
        input("\nPresione Enter para continuar...")
        return

    print("Establecimientos disponibles:\n")
    for i, (id_est, nombre, tipo, direccion) in enumerate(establecimientos, 1):
        print(f"  {i}. {nombre}  ({tipo})  -  {direccion}")
    print("  0. Volver")

    while True:
        opcion = input("\n  Elegi un establecimiento: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(establecimientos):
                id_est = establecimientos[idx][0]
                mostrar_catalogo(id_est)
                return
        except ValueError:
            pass
        print("  Opcion invalida")


def mostrar_catalogo(id_establecimiento):
    """Muestra el catalogo de un establecimiento. Primero busca en cache (Redis), si no esta va a Mongo."""
    r = get_redis()
    clave_cache = f"catalogo:establecimiento:{id_establecimiento}"

    # Intentar leer de cache
    cache = r.get(clave_cache)
    if cache:
        print("\n(Catalogo cargado desde cache Redis)\n")
        doc = json.loads(cache)
    else:
        # No esta en cache, ir a Mongo
        db = get_mongo()
        doc = db.catalogo_establecimientos.find_one({"_id": id_establecimiento})
        if not doc:
            print("\nEste establecimiento todavia no cargo su catalogo")
            input("\nPresione Enter para continuar...")
            return

        # Convertir el _id a string para poder serializar a JSON
        doc["_id"] = str(doc["_id"])
        # Guardar en cache por 5 minutos
        r.set(clave_cache, json.dumps(doc), ex=300)
        print("\n(Catalogo cargado desde Mongo y guardado en cache)\n")

    print(f"\n{doc['nombre']}  ({doc['tipo']})")
    print("-" * 60)

    if not doc.get("catalogo"):
        print("Este establecimiento todavia no tiene productos")
    else:
        for prod in doc["catalogo"]:
            if not prod.get("disponible", True):
                continue
            print(f"  [{prod['id_producto']}]  {prod['nombre']}  -  ${prod['precio']}")
            print(f"      Categoria: {prod['categoria']}")
            if prod.get("descripcion"):
                print(f"      {prod['descripcion']}")
            if prod.get("atributos"):
                attrs = ", ".join(f"{k}={v}" for k, v in prod["atributos"].items())
                print(f"      Atributos: {attrs}")
            print()

    input("\nPresione Enter para continuar...")


# ============================================
# AGREGAR AL CARRITO (Redis Hash con TTL)
# ============================================
def agregar_al_carrito(cliente):
    print("\nAGREGAR PRODUCTO AL CARRITO\n")

    # Listar establecimientos
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("SELECT id_establecimiento, nombre, tipo FROM establecimiento ORDER BY nombre")
    establecimientos = cur.fetchall()
    cur.close()
    conn.close()

    if not establecimientos:
        print("No hay establecimientos registrados")
        input("\nPresione Enter para continuar...")
        return

    print("Establecimientos:\n")
    for i, (id_est, nombre, tipo) in enumerate(establecimientos, 1):
        print(f"  {i}. {nombre}  ({tipo})")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi un establecimiento: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(establecimientos):
                id_est = establecimientos[idx][0]
                nombre_est = establecimientos[idx][1]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    # Verificar que el carrito (si ya tiene algo) sea del mismo establecimiento
    r = get_redis()
    clave_carrito = f"carrito:cliente:{cliente['id']}"
    est_actual = r.hget(clave_carrito, "_establecimiento_id")
    if est_actual and int(est_actual) != id_est:
        print(f"\nYa tenes productos en tu carrito de otro establecimiento.")
        print(f"Si queres pedir de este otro, primero vacia tu carrito o confirma el pedido actual.")
        input("\nPresione Enter para continuar...")
        return

    # Buscar productos del establecimiento en Mongo
    db = get_mongo()
    doc = db.catalogo_establecimientos.find_one({"_id": id_est})
    if not doc or not doc.get("catalogo"):
        print(f"\n{nombre_est} todavia no tiene productos cargados")
        input("\nPresione Enter para continuar...")
        return

    disponibles = [p for p in doc["catalogo"] if p.get("disponible", True)]
    if not disponibles:
        print(f"\n{nombre_est} no tiene productos disponibles en este momento")
        input("\nPresione Enter para continuar...")
        return

    print(f"\nProductos de {nombre_est}:\n")
    for i, prod in enumerate(disponibles, 1):
        print(f"  {i}. {prod['nombre']}  -  ${prod['precio']}  -  ({prod['categoria']})")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi un producto: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(disponibles):
                producto = disponibles[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    while True:
        cant_str = pedir_dato("Cantidad")
        if cant_str is None:
            return
        try:
            cantidad = int(cant_str)
            if cantidad > 0:
                break
            print("  Tiene que ser mayor a 0")
        except ValueError:
            print("  Tiene que ser un numero entero")

    # Guardar en Redis como Hash
    # _establecimiento_id queda como marcador para saber de que negocio es el carrito
    r.hset(clave_carrito, "_establecimiento_id", id_est)
    r.hset(clave_carrito, "_establecimiento_nombre", nombre_est)

    # La clave del item es el id_producto. Si ya esta, sumamos cantidad.
    item_key = producto["id_producto"]
    existente = r.hget(clave_carrito, item_key)
    if existente:
        item = json.loads(existente)
        item["cantidad"] += cantidad
    else:
        item = {
            "id_producto": producto["id_producto"],
            "nombre": producto["nombre"],
            "precio": producto["precio"],
            "cantidad": cantidad
        }
    r.hset(clave_carrito, item_key, json.dumps(item))

    # TTL de 24 horas
    r.expire(clave_carrito, 60 * 60 * 24)

    print(f"\nAgregado al carrito: {cantidad} x {producto['nombre']}")
    input("\nPresione Enter para continuar...")


# ============================================
# VER CARRITO (Redis)
# ============================================
def ver_carrito(cliente):
    print("\nMI CARRITO\n")

    r = get_redis()
    clave_carrito = f"carrito:cliente:{cliente['id']}"
    carrito = r.hgetall(clave_carrito)

    if not carrito:
        print("Tu carrito esta vacio")
        input("\nPresione Enter para continuar...")
        return

    est_nombre = carrito.get("_establecimiento_nombre", "Desconocido")
    print(f"Establecimiento: {est_nombre}")
    print("-" * 60)

    total = 0
    items = 0
    for key, valor in carrito.items():
        if key.startswith("_"):
            continue
        item = json.loads(valor)
        subtotal = item["precio"] * item["cantidad"]
        total += subtotal
        items += item["cantidad"]
        print(f"  {item['cantidad']} x {item['nombre']}  -  ${item['precio']} c/u  =  ${subtotal}")

    print("-" * 60)
    print(f"  Items totales: {items}")
    print(f"  TOTAL: ${total}")

    # Mostrar TTL del carrito
    ttl = r.ttl(clave_carrito)
    if ttl > 0:
        horas = ttl // 3600
        minutos = (ttl % 3600) // 60
        print(f"\n  (El carrito expira en {horas}h {minutos}min)")

    input("\nPresione Enter para continuar...")


# ============================================
# PLACEHOLDERS (lo demas viene despues)
# ============================================
def confirmar_pedido(cliente):
    print("\nCONFIRMAR PEDIDO\n")

    r = get_redis()
    clave_carrito = f"carrito:cliente:{cliente['id']}"
    carrito = r.hgetall(clave_carrito)

    if not carrito:
        print("Tu carrito esta vacio")
        input("\nPresione Enter para continuar...")
        return

    # ============================================
    # LOCK ANTI-DOBLE-CLICK
    # ============================================
    clave_lock = f"lock:checkout:cliente:{cliente['id']}"
    # SET NX = solo si no existe (atomico). EX 10 = expira en 10s
    if not r.set(clave_lock, "1", nx=True, ex=10):
        print("Ya estas procesando un pedido. Espera un momento.")
        input("\nPresione Enter para continuar...")
        return

    try:
        # ============================================
        # PASO 1: ELEGIR DIRECCION DE ENTREGA
        # ============================================
        nro_direccion = elegir_o_crear_direccion(cliente)
        if nro_direccion is None:
            print("\nPedido cancelado")
            input("\nPresione Enter para continuar...")
            return

        # ============================================
        # PASO 2: ARMAR LISTA DE ITEMS DEL CARRITO
        # ============================================
        id_establecimiento = int(carrito["_establecimiento_id"])
        items = []
        total = 0
        for key, valor in carrito.items():
            if key.startswith("_"):
                continue
            item = json.loads(valor)
            items.append(item)
            total += item["precio"] * item["cantidad"]

        print(f"\nResumen del pedido:")
        print(f"  Establecimiento: {carrito.get('_establecimiento_nombre')}")
        print(f"  Items: {sum(i['cantidad'] for i in items)}")
        print(f"  TOTAL: ${total}")
        confirmacion = input("\nConfirmar pedido? (s/n): ").strip().lower()
        if confirmacion != "s":
            print("\nPedido cancelado")
            input("\nPresione Enter para continuar...")
            return

        # ============================================
        # PASO 3: INSERTAR EN POSTGRES (TRANSACCION)
        # ============================================
        conn = get_postgres()
        cur = conn.cursor()
        try:
            # Insertar pedido
            cur.execute("""
                INSERT INTO pedido (total, id_cliente, id_establecimiento, id_cliente_dir)
                VALUES (%s, %s, %s, %s)
                RETURNING id_pedido, fecha_hora
            """, (total, cliente["id"], id_establecimiento, nro_direccion))
            id_pedido, fecha_hora = cur.fetchone()

            # Insertar detalle
            for item in items:
                subtotal = item["precio"] * item["cantidad"]
                cur.execute("""
                    INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (id_pedido, item["id_producto"], item["cantidad"], item["precio"], subtotal))

            # Insertar pago (estado pendiente, se procesa por separado)
            cur.execute("""
                INSERT INTO pago (id_pedido, monto, metodo, estado)
                VALUES (%s, %s, %s, %s)
            """, (id_pedido, total, "efectivo", "pendiente"))

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"\nError al crear el pedido en Postgres: {e}")
            input("\nPresione Enter para continuar...")
            return
        finally:
            cur.close()
            conn.close()

        # ============================================
        # PASO 4: REGISTRAR ESTADO INICIAL EN CASSANDRA
        # ============================================
        try:
            from connections import get_cassandra
            session = get_cassandra()
            session.execute("""
                INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
                VALUES (%s, %s, %s, %s)
            """, (id_pedido, fecha_hora, "creado", "Pedido creado por el cliente"))
        except Exception as e:
            print(f"\n(Aviso: no se pudo registrar estado en Cassandra: {e})")

        # ============================================
        # PASO 5: CREAR NODOS Y RELACIONES EN NEO4J
        # ============================================
        try:
            from connections import get_neo4j
            driver = get_neo4j()
            with driver.session() as ses:
                # Cliente
                ses.run("""
                    MERGE (c:Cliente {id: $id})
                    SET c.nombre = $nombre
                """, id=cliente["id"], nombre=cliente["nombre"])

                # Establecimiento
                ses.run("""
                    MERGE (e:Establecimiento {id: $id})
                    SET e.nombre = $nombre
                """, id=id_establecimiento, nombre=carrito.get("_establecimiento_nombre"))

                # Pedido
                ses.run("""
                    MERGE (p:Pedido {id: $id})
                    SET p.fecha = $fecha, p.total = $total
                """, id=id_pedido, fecha=str(fecha_hora), total=total)

                # Cliente -> Pedido
                ses.run("""
                    MATCH (c:Cliente {id: $id_cliente}), (p:Pedido {id: $id_pedido})
                    MERGE (c)-[:REALIZO]->(p)
                """, id_cliente=cliente["id"], id_pedido=id_pedido)

                # Productos y Pedido -> Producto -> Establecimiento
                for item in items:
                    ses.run("""
                        MERGE (pr:Producto {id: $id_prod})
                        SET pr.nombre = $nombre, pr.precio = $precio
                    """, id_prod=item["id_producto"], nombre=item["nombre"], precio=item["precio"])

                    ses.run("""
                        MATCH (p:Pedido {id: $id_pedido}), (pr:Producto {id: $id_prod})
                        MERGE (p)-[r:CONTIENE]->(pr)
                        SET r.cantidad = $cantidad
                    """, id_pedido=id_pedido, id_prod=item["id_producto"], cantidad=item["cantidad"])

                    ses.run("""
                        MATCH (pr:Producto {id: $id_prod}), (e:Establecimiento {id: $id_est})
                        MERGE (pr)-[:OFRECIDO_POR]->(e)
                    """, id_prod=item["id_producto"], id_est=id_establecimiento)
            driver.close()
        except Exception as e:
            print(f"\n(Aviso: no se pudo crear el grafo en Neo4j: {e})")

        # ============================================
        # PASO 6: LIMPIAR EL CARRITO DE REDIS
        # ============================================
        r.delete(clave_carrito)

        print(f"\nPedido #{id_pedido} creado correctamente")
        print(f"  Total: ${total}")
        print(f"  Estado: creado")
        print(f"\nSe registro en:")
        print(f"  - Postgres (pedido, detalle, pago)")
        print(f"  - Cassandra (estado inicial)")
        print(f"  - Neo4j (grafo cliente-pedido-productos-establecimiento)")
        print(f"  - Redis (carrito vaciado)")

    finally:
        # Siempre liberar el lock al final
        r.delete(clave_lock)

    input("\nPresione Enter para continuar...")


def elegir_o_crear_direccion(cliente):
    """Devuelve el nro_direccion elegido, o None si cancela."""
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT nro_direccion, calle, numero, ciudad, alias
        FROM direccion
        WHERE id_cliente = %s
        ORDER BY nro_direccion
    """, (cliente["id"],))
    direcciones = cur.fetchall()

    if direcciones:
        print("\nTus direcciones:")
        for i, (nro, calle, numero, ciudad, alias) in enumerate(direcciones, 1):
            etiqueta = f" ({alias})" if alias else ""
            print(f"  {i}. {calle} {numero}, {ciudad}{etiqueta}")
        print(f"  {len(direcciones) + 1}. Agregar nueva direccion")
        print("  0. Cancelar")

        while True:
            opcion = input("\n  Elegi una direccion: ").strip()
            if opcion == "0":
                cur.close()
                conn.close()
                return None
            if opcion == str(len(direcciones) + 1):
                break
            try:
                idx = int(opcion) - 1
                if 0 <= idx < len(direcciones):
                    nro = direcciones[idx][0]
                    cur.close()
                    conn.close()
                    return nro
            except ValueError:
                pass
            print("  Opcion invalida")

    # Crear direccion nueva
    print("\nNueva direccion:")
    calle = pedir_dato("Calle")
    if calle is None:
        cur.close()
        conn.close()
        return None
    numero = pedir_dato("Numero", requerido=False)
    if numero is None:
        cur.close()
        conn.close()
        return None
    ciudad = pedir_dato("Ciudad")
    if ciudad is None:
        cur.close()
        conn.close()
        return None
    cp = pedir_dato("Codigo Postal", requerido=False)
    if cp is None:
        cur.close()
        conn.close()
        return None
    alias = pedir_dato("Alias (ej: casa, trabajo)", requerido=False)
    if alias is None:
        cur.close()
        conn.close()
        return None

    try:
        # Calcular el siguiente nro_direccion
        cur.execute("""
            SELECT COALESCE(MAX(nro_direccion), 0) + 1
            FROM direccion
            WHERE id_cliente = %s
        """, (cliente["id"],))
        nuevo_nro = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO direccion (id_cliente, nro_direccion, calle, numero, ciudad, cp, alias)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (cliente["id"], nuevo_nro, calle, numero, ciudad, cp, alias))
        conn.commit()
        print(f"\nDireccion agregada (#{nuevo_nro})")
        return nuevo_nro
    except Exception as e:
        conn.rollback()
        print(f"Error al guardar direccion: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def ver_mis_pedidos(cliente):
    print("\nMIS PEDIDOS\n")

    # Traer pedidos del cliente desde Postgres
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_cliente = %s
        ORDER BY p.fecha_hora DESC
    """, (cliente["id"],))
    pedidos = cur.fetchall()
    cur.close()
    conn.close()

    if not pedidos:
        print("Todavia no hiciste ningun pedido")
        input("\nPresione Enter para continuar...")
        return

    # Para cada pedido, traer el estado mas reciente desde Cassandra
    from connections import get_cassandra
    session = get_cassandra()

    print(f"Tenes {len(pedidos)} pedido(s):\n")
    print("-" * 70)

    for id_pedido, fecha_hora, total, est_nombre in pedidos:
        # En Cassandra el clustering es por fecha_hora DESC, asi que el primero es el mas reciente
        rows = session.execute("""
            SELECT estado, fecha_hora, observacion
            FROM estado_pedido
            WHERE id_pedido = %s
            LIMIT 1
        """, (id_pedido,))
        estado_actual = list(rows)

        if estado_actual:
            ultimo = estado_actual[0]
            estado_txt = f"{ultimo.estado.upper()}"
            if ultimo.observacion:
                estado_txt += f" ({ultimo.observacion})"
        else:
            estado_txt = "SIN ESTADOS REGISTRADOS"

        print(f"  Pedido #{id_pedido}  -  {fecha_hora.strftime('%d/%m/%Y %H:%M')}")
        print(f"  Establecimiento: {est_nombre}")
        print(f"  Total: ${total}")
        print(f"  Estado actual: {estado_txt}")
        print("-" * 70)

    # Opcion de ver detalle/historial de un pedido
    print("\n  Para ver el historial completo de estados de un pedido, escribi su numero.")
    opcion = input("  Numero de pedido (Enter para volver): ").strip()

    if opcion:
        try:
            id_buscar = int(opcion)
            # Validar que sea un pedido del cliente
            ids_validos = [p[0] for p in pedidos]
            if id_buscar not in ids_validos:
                print(f"  No tenes ningun pedido con ese numero")
                input("\nPresione Enter para continuar...")
                return

            # Traer toda la timeline desde Cassandra
            print(f"\nHISTORIAL DE ESTADOS - Pedido #{id_buscar}\n")
            rows = session.execute("""
                SELECT estado, fecha_hora, observacion
                FROM estado_pedido
                WHERE id_pedido = %s
            """, (id_buscar,))
            timeline = list(rows)

            if not timeline:
                print("Sin estados registrados")
            else:
                # Cassandra ya viene ordenado DESC por clustering, pero queremos ASC
                timeline.sort(key=lambda r: r.fecha_hora)
                for r in timeline:
                    obs = f" - {r.observacion}" if r.observacion else ""
                    print(f"  {r.fecha_hora.strftime('%d/%m %H:%M:%S')}  ->  {r.estado.upper()}{obs}")

        except ValueError:
            pass

    input("\nPresione Enter para continuar...")

def calificar_pedido(cliente):
    print("\nCALIFICAR PEDIDO\n")

    # Postgres: traer pedidos del cliente
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.id_establecimiento, e.nombre,
               r.id_repartidor, r.nombre, r.apellido
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        LEFT JOIN repartidor r ON p.id_repartidor = r.id_repartidor
        WHERE p.id_cliente = %s
        ORDER BY p.fecha_hora DESC
    """, (cliente["id"],))
    pedidos = cur.fetchall()
    cur.close()
    conn.close()

    if not pedidos:
        print("Todavia no hiciste ningun pedido")
        input("\nPresione Enter para continuar...")
        return

    # Cassandra: filtrar solo los entregados
    from connections import get_cassandra
    session = get_cassandra()

    entregados = []
    for pedido in pedidos:
        id_p = pedido[0]
        rows = list(session.execute(
            "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1",
            (id_p,)
        ))
        if rows and rows[0].estado == "entregado":
            entregados.append(pedido)

    if not entregados:
        print("No tenes pedidos entregados para calificar")
        input("\nPresione Enter para continuar...")
        return

    # Mongo: filtrar los que ya estan calificados
    db = get_mongo()
    sin_calificar = []
    for pedido in entregados:
        id_p = pedido[0]
        ya_calificado = db.calificaciones.find_one({"_id": f"pedido_{id_p}"})
        if not ya_calificado:
            sin_calificar.append(pedido)

    if not sin_calificar:
        print("Ya calificaste todos tus pedidos entregados")
        input("\nPresione Enter para continuar...")
        return

    print("Pedidos pendientes de calificar:\n")
    for i, p in enumerate(sin_calificar, 1):
        id_p, fecha, total, _, est_nombre, _, rep_n, rep_a = p
        repartidor_txt = f"{rep_n} {rep_a}" if rep_n else "sin repartidor"
        print(f"  {i}. Pedido #{id_p}  -  {est_nombre}  -  Repartidor: {repartidor_txt}")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi un pedido: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(sin_calificar):
                pedido_sel = sin_calificar[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    id_pedido, fecha, total, id_est, est_nombre, id_rep, rep_n, rep_a = pedido_sel

    # Pedir calificacion del establecimiento
    print(f"\nCalificacion del establecimiento ({est_nombre}):")
    puntaje_est = pedir_puntaje()
    if puntaje_est is None:
        return
    comentario_est = input("  Comentario (Enter para saltear): ").strip()

    # Pedir calificacion del repartidor (si hay)
    calif_rep = None
    if id_rep:
        print(f"\nCalificacion del repartidor ({rep_n} {rep_a}):")
        puntaje_rep = pedir_puntaje()
        if puntaje_rep is None:
            return
        comentario_rep = input("  Comentario (Enter para saltear): ").strip()
        calif_rep = {
            "puntaje": puntaje_rep,
            "comentario": comentario_rep or None
        }

    # Mongo: insertar documento de calificacion
    from datetime import datetime
    doc = {
        "_id": f"pedido_{id_pedido}",
        "id_cliente": cliente["id"],
        "id_establecimiento": id_est,
        "id_repartidor": id_rep,
        "fecha": datetime.utcnow().isoformat(),
        "calificacion_establecimiento": {
            "puntaje": puntaje_est,
            "comentario": comentario_est or None,
            "respuesta_establecimiento": None
        }
    }
    if calif_rep:
        doc["calificacion_repartidor"] = calif_rep

    db.calificaciones.insert_one(doc)

    # Neo4j: crear relacion CALIFICO
    try:
        from connections import get_neo4j
        driver = get_neo4j()
        with driver.session() as ses:
            ses.run("""
                MATCH (c:Cliente {id: $id_c}), (e:Establecimiento {id: $id_e})
                MERGE (c)-[r:CALIFICO]->(e)
                SET r.puntaje = $puntaje, r.id_pedido = $id_p
            """, id_c=cliente["id"], id_e=id_est, puntaje=puntaje_est, id_p=id_pedido)

            if id_rep:
                ses.run("""
                    MATCH (c:Cliente {id: $id_c}), (r:Repartidor {id: $id_r})
                    MERGE (c)-[rel:CALIFICO]->(r)
                    SET rel.puntaje = $puntaje, rel.id_pedido = $id_p
                """, id_c=cliente["id"], id_r=id_rep,
                     puntaje=calif_rep["puntaje"], id_p=id_pedido)
        driver.close()
    except Exception as e:
        print(f"\n(Aviso Neo4j: {e})")

    print(f"\nCalificacion registrada correctamente")
    print(f"  - Mongo: documento de calificacion guardado")
    print(f"  - Neo4j: relacion (Cliente)-[CALIFICO]->(Establecimiento) creada")
    input("\nPresione Enter para continuar...")


def pedir_puntaje():
    """Pide un puntaje del 1 al 5. Devuelve int o None si cancela."""
    while True:
        valor = input("  Puntaje (1-5, 0 para cancelar): ").strip()
        if valor == "0":
            return None
        try:
            puntaje = int(valor)
            if 1 <= puntaje <= 5:
                return puntaje
        except ValueError:
            pass
        print("  Tiene que ser un numero del 1 al 5")


def ver_historial(cliente):
    print("Ver historial - Aun no implementado")
    input("\nPresione Enter para continuar...")


def aplicar_promocion(cliente):
    print("Aplicar promocion - Aun no implementado")
    input("\nPresione Enter para continuar...")