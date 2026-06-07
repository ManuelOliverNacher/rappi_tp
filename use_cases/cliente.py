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
    r = get_redis()
    clave_cache = f"catalogo:establecimiento:{id_establecimiento}"

    cache = r.get(clave_cache)
    if cache:
        print("\n(Catalogo cargado desde cache Redis)\n")
        doc = json.loads(cache)
    else:
        db = get_mongo()
        doc = db.catalogo_establecimientos.find_one({"_id": id_establecimiento})
        if not doc:
            print("\nEste establecimiento todavia no cargo su catalogo")
            input("\nPresione Enter para continuar...")
            return
        doc["_id"] = str(doc["_id"])
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
# AGREGAR AL CARRITO
# ============================================
def agregar_al_carrito(cliente):
    print("\nAGREGAR PRODUCTO AL CARRITO\n")

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

    r = get_redis()
    clave_carrito = f"carrito:cliente:{cliente['id']}"
    est_actual = r.hget(clave_carrito, "_establecimiento_id")
    if est_actual and int(est_actual) != id_est:
        print(f"\nYa tenes productos en tu carrito de otro establecimiento.")
        print(f"Si queres pedir de este otro, primero vacia tu carrito o confirma el pedido actual.")
        input("\nPresione Enter para continuar...")
        return

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

    r.hset(clave_carrito, "_establecimiento_id", id_est)
    r.hset(clave_carrito, "_establecimiento_nombre", nombre_est)

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
    r.expire(clave_carrito, 60 * 60 * 24)

    print(f"\nAgregado al carrito: {cantidad} x {producto['nombre']}")
    input("\nPresione Enter para continuar...")


# ============================================
# VER CARRITO
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
    print(f"  Subtotal: ${total}")

    # Si hay promo aplicada, mostrarla
    codigo_promo = carrito.get("_promo_codigo")
    if codigo_promo:
        descuento_monto = float(carrito.get("_promo_descuento_monto", 0))
        total_final = total - descuento_monto
        print(f"  Promocion aplicada: {codigo_promo} (-${descuento_monto:.2f})")
        print(f"  TOTAL: ${total_final:.2f}")
    else:
        print(f"  TOTAL: ${total}")

    ttl = r.ttl(clave_carrito)
    if ttl > 0:
        horas = ttl // 3600
        minutos = (ttl % 3600) // 60
        print(f"\n  (El carrito expira en {horas}h {minutos}min)")

    input("\nPresione Enter para continuar...")


# ============================================
# CONFIRMAR PEDIDO
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

    # LOCK ANTI-DOBLE-CLICK
    clave_lock = f"lock:checkout:cliente:{cliente['id']}"
    if not r.set(clave_lock, "1", nx=True, ex=10):
        print("Ya estas procesando un pedido. Espera un momento.")
        input("\nPresione Enter para continuar...")
        return

    try:
        # PASO 1: DIRECCION
        nro_direccion = elegir_o_crear_direccion(cliente)
        if nro_direccion is None:
            print("\nPedido cancelado")
            input("\nPresione Enter para continuar...")
            return

        # PASO 2: ARMAR ITEMS
        id_establecimiento = int(carrito["_establecimiento_id"])
        items = []
        total = 0
        for key, valor in carrito.items():
            if key.startswith("_"):
                continue
            item = json.loads(valor)
            items.append(item)
            total += item["precio"] * item["cantidad"]

        # Verificar promocion aplicada
        codigo_promo = carrito.get("_promo_codigo")
        id_promo = carrito.get("_promo_id")
        descuento_monto = float(carrito.get("_promo_descuento_monto", 0))
        total_con_descuento = total - descuento_monto

        print(f"\nResumen del pedido:")
        print(f"  Establecimiento: {carrito.get('_establecimiento_nombre')}")
        print(f"  Items: {sum(i['cantidad'] for i in items)}")
        print(f"  Subtotal: ${total}")
        if codigo_promo:
            print(f"  Promocion aplicada: {codigo_promo} (-${descuento_monto:.2f})")
            print(f"  TOTAL: ${total_con_descuento:.2f}")
        else:
            print(f"  TOTAL: ${total}")

        confirmacion = input("\nConfirmar pedido? (s/n): ").strip().lower()
        if confirmacion != "s":
            print("\nPedido cancelado")
            input("\nPresione Enter para continuar...")
            return

        # El total que va a Postgres es con descuento
        total = total_con_descuento

        # PASO 3: POSTGRES
        conn = get_postgres()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO pedido (total, id_cliente, id_establecimiento, id_cliente_dir)
                VALUES (%s, %s, %s, %s)
                RETURNING id_pedido, fecha_hora
            """, (total, cliente["id"], id_establecimiento, nro_direccion))
            id_pedido, fecha_hora = cur.fetchone()

            for item in items:
                subtotal = item["precio"] * item["cantidad"]
                cur.execute("""
                    INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (id_pedido, item["id_producto"], item["cantidad"], item["precio"], subtotal))

            cur.execute("""
                INSERT INTO pago (id_pedido, monto, metodo, estado)
                VALUES (%s, %s, %s, %s)
            """, (id_pedido, total, "efectivo", "pendiente"))

            # Si hay promocion aplicada, registrarla
            if id_promo:
                cur.execute("""
                    INSERT INTO promocion_pedido (id_promocion, id_pedido, descuento_aplicado)
                    VALUES (%s, %s, %s)
                """, (int(id_promo), id_pedido, descuento_monto))

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"\nError al crear el pedido en Postgres: {e}")
            input("\nPresione Enter para continuar...")
            return
        finally:
            cur.close()
            conn.close()

        # PASO 4: CASSANDRA
        try:
            from connections import get_cassandra
            session = get_cassandra()
            session.execute("""
                INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
                VALUES (%s, %s, %s, %s)
            """, (id_pedido, fecha_hora, "creado", "Pedido creado por el cliente"))
        except Exception as e:
            print(f"\n(Aviso: no se pudo registrar estado en Cassandra: {e})")

        # PASO 5: NEO4J
        try:
            from connections import get_neo4j
            driver = get_neo4j()
            with driver.session() as ses:
                ses.run("""
                    MERGE (c:Cliente {id: $id})
                    SET c.nombre = $nombre
                """, id=cliente["id"], nombre=cliente["nombre"])

                ses.run("""
                    MERGE (e:Establecimiento {id: $id})
                    SET e.nombre = $nombre
                """, id=id_establecimiento, nombre=carrito.get("_establecimiento_nombre"))

                ses.run("""
                    MERGE (p:Pedido {id: $id})
                    SET p.fecha = $fecha, p.total = $total
                """, id=id_pedido, fecha=str(fecha_hora), total=total)

                ses.run("""
                    MATCH (c:Cliente {id: $id_cliente}), (p:Pedido {id: $id_pedido})
                    MERGE (c)-[:REALIZO]->(p)
                """, id_cliente=cliente["id"], id_pedido=id_pedido)

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

        # PASO 6: LIMPIAR CARRITO
        r.delete(clave_carrito)

        print(f"\nPedido #{id_pedido} creado correctamente")
        print(f"  Total: ${total}")
        if codigo_promo:
            print(f"  Promocion aplicada: {codigo_promo}")
        print(f"  Estado: creado")
        print(f"\nSe registro en:")
        print(f"  - Postgres (pedido, detalle, pago" + (", promocion_pedido" if codigo_promo else "") + ")")
        print(f"  - Cassandra (estado inicial)")
        print(f"  - Neo4j (grafo cliente-pedido-productos-establecimiento)")
        print(f"  - Redis (carrito vaciado)")

    finally:
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


# ============================================
# VER MIS PEDIDOS
# ============================================
def ver_mis_pedidos(cliente):
    print("\nMIS PEDIDOS\n")

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

    from connections import get_cassandra
    session = get_cassandra()

    print(f"Tenes {len(pedidos)} pedido(s):\n")
    print("-" * 70)

    for id_pedido, fecha_hora, total, est_nombre in pedidos:
        rows = session.execute("""
            SELECT estado, fecha_hora, observacion
            FROM estado_pedido
            WHERE id_pedido = %s
            LIMIT 1
        """, (id_pedido,))
        estado_actual = list(rows)

        if estado_actual:
            ultimo = estado_actual[0]
            estado_txt = f"{ultimo['estado'].upper()}"
            if ultimo.get("observacion"):
                estado_txt += f" ({ultimo['observacion']})"
        else:
            estado_txt = "SIN ESTADOS REGISTRADOS"

        print(f"  Pedido #{id_pedido}  -  {fecha_hora.strftime('%d/%m/%Y %H:%M')}")
        print(f"  Establecimiento: {est_nombre}")
        print(f"  Total: ${total}")
        print(f"  Estado actual: {estado_txt}")
        print("-" * 70)

    print("\n  Para ver el historial completo de estados de un pedido, escribi su numero.")
    opcion = input("  Numero de pedido (Enter para volver): ").strip()

    if opcion:
        try:
            id_buscar = int(opcion)
            ids_validos = [p[0] for p in pedidos]
            if id_buscar not in ids_validos:
                print(f"  No tenes ningun pedido con ese numero")
                input("\nPresione Enter para continuar...")
                return

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
                from datetime import datetime as _dt
                def _ts(v):
                    if isinstance(v, str):
                        return _dt.fromisoformat(v.replace("Z", "+00:00").replace("+0000", "+00:00"))
                    return v
                timeline.sort(key=lambda r: _ts(r["fecha_hora"]) if isinstance(r, dict) else r.fecha_hora)
                for r in timeline:
                    fh = _ts(r["fecha_hora"]) if isinstance(r, dict) else r.fecha_hora
                    obs = f" - {r.get('observacion')}" if isinstance(r, dict) and r.get("observacion") else (f" - {r.observacion}" if not isinstance(r, dict) and r.observacion else "")
                    estado_r = r["estado"] if isinstance(r, dict) else r.estado
                    print(f"  {fh.strftime('%d/%m %H:%M:%S')}  ->  {estado_r.upper()}{obs}")

        except ValueError:
            pass

    input("\nPresione Enter para continuar...")


# ============================================
# CALIFICAR PEDIDO
# ============================================
def calificar_pedido(cliente):
    print("\nCALIFICAR PEDIDO\n")

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

    from connections import get_cassandra
    session = get_cassandra()

    entregados = []
    for pedido in pedidos:
        id_p = pedido[0]
        rows = list(session.execute(
            "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1",
            (id_p,)
        ))
        if rows and rows[0]["estado"] == "entregado":
            entregados.append(pedido)

    if not entregados:
        print("No tenes pedidos entregados para calificar")
        input("\nPresione Enter para continuar...")
        return

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

    print(f"\nCalificacion del establecimiento ({est_nombre}):")
    puntaje_est = pedir_puntaje()
    if puntaje_est is None:
        return
    comentario_est = input("  Comentario (Enter para saltear): ").strip()

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


# ============================================
# VER HISTORIAL DE PEDIDOS (Mongo)
# ============================================
def ver_historial(cliente):
    print("\nHISTORIAL DE PEDIDOS\n")

    # Postgres: cabecera de pedidos
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre, e.tipo
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_cliente = %s
        ORDER BY p.fecha_hora DESC
    """, (cliente["id"],))
    pedidos = cur.fetchall()

    if not pedidos:
        cur.close()
        conn.close()
        print("Todavia no hiciste ningun pedido")
        input("\nPresione Enter para continuar...")
        return

    print(f"Total de pedidos historicos: {len(pedidos)}\n")
    print("-" * 70)

    for id_pedido, fecha, total, est_nombre, est_tipo in pedidos:
        # Postgres: detalle del pedido
        cur.execute("""
            SELECT id_producto, cantidad, precio_unitario, subtotal
            FROM detalle_pedido
            WHERE id_pedido = %s
        """, (id_pedido,))
        detalle = cur.fetchall()

        # Mongo: traer nombres de productos
        db = get_mongo()
        productos_info = []
        for id_prod, cant, precio, subtotal in detalle:
            doc = db.catalogo_establecimientos.find_one(
                {"catalogo.id_producto": id_prod},
                {"catalogo.$": 1}
            )
            if doc and doc.get("catalogo"):
                nombre_prod = doc["catalogo"][0]["nombre"]
            else:
                nombre_prod = id_prod
            productos_info.append((nombre_prod, cant, precio, subtotal))

        print(f"  Pedido #{id_pedido}  -  {fecha.strftime('%d/%m/%Y %H:%M')}")
        print(f"  Establecimiento: {est_nombre} ({est_tipo})")
        for nombre, cant, precio, subtotal in productos_info:
            print(f"    {cant} x {nombre}  -  ${precio} c/u  =  ${subtotal}")
        print(f"  TOTAL: ${total}")
        print("-" * 70)

    cur.close()
    conn.close()

    # Opcion: volver a pedir uno (rearmar carrito desde el historial)
    print("\n  Para volver a pedir uno, escribi su numero.")
    opcion = input("  Numero de pedido (Enter para volver): ").strip()
    if opcion:
        try:
            id_buscar = int(opcion)
            ids_validos = [p[0] for p in pedidos]
            if id_buscar in ids_validos:
                rearmar_carrito_desde_pedido(cliente, id_buscar)
        except ValueError:
            pass

    input("\nPresione Enter para continuar...")


def rearmar_carrito_desde_pedido(cliente, id_pedido):
    """Recrea el carrito en Redis a partir de un pedido viejo (para volver a pedir)."""
    r = get_redis()
    clave_carrito = f"carrito:cliente:{cliente['id']}"

    # Verificar que no haya carrito activo
    if r.hget(clave_carrito, "_establecimiento_id"):
        print("\nYa tenes un carrito armado. Confirmalo o vacialo primero.")
        return

    # Postgres: traer datos del pedido y detalle
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_establecimiento, e.nombre
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_pedido = %s
    """, (id_pedido,))
    cab = cur.fetchone()
    if not cab:
        cur.close()
        conn.close()
        return
    id_est, nombre_est = cab

    cur.execute("""
        SELECT id_producto, cantidad
        FROM detalle_pedido
        WHERE id_pedido = %s
    """, (id_pedido,))
    items_pedido = cur.fetchall()
    cur.close()
    conn.close()

    # Mongo: traer info actualizada de cada producto
    db = get_mongo()
    r.hset(clave_carrito, "_establecimiento_id", id_est)
    r.hset(clave_carrito, "_establecimiento_nombre", nombre_est)

    agregados = 0
    no_disponibles = 0
    for id_prod, cantidad in items_pedido:
        doc = db.catalogo_establecimientos.find_one(
            {"catalogo.id_producto": id_prod},
            {"catalogo.$": 1}
        )
        if doc and doc.get("catalogo"):
            prod = doc["catalogo"][0]
            if prod.get("disponible", True):
                item = {
                    "id_producto": id_prod,
                    "nombre": prod["nombre"],
                    "precio": prod["precio"],
                    "cantidad": cantidad
                }
                r.hset(clave_carrito, id_prod, json.dumps(item))
                agregados += 1
            else:
                no_disponibles += 1

    r.expire(clave_carrito, 60 * 60 * 24)

    print(f"\nCarrito armado con {agregados} producto(s) del pedido #{id_pedido}")
    if no_disponibles:
        print(f"  ({no_disponibles} producto(s) ya no estan disponibles)")


# ============================================
# APLICAR PROMOCION
# ============================================
def aplicar_promocion(cliente):
    print("\nAPLICAR PROMOCION AL CARRITO\n")

    r = get_redis()
    clave_carrito = f"carrito:cliente:{cliente['id']}"
    carrito = r.hgetall(clave_carrito)
    if not carrito:
        print("Tu carrito esta vacio. Primero agrega productos.")
        input("\nPresione Enter para continuar...")
        return

    codigo = input("  Ingresa el codigo de la promocion (0 para cancelar): ").strip().upper()
    if codigo == "0" or not codigo:
        return

    promo = buscar_promocion(codigo)
    if not promo:
        print(f"\nLa promocion '{codigo}' no existe o expiro")
        input("\nPresione Enter para continuar...")
        return

    from datetime import datetime
    hoy = datetime.now().date()
    fecha_inicio = datetime.fromisoformat(promo["fecha_inicio"]).date() if isinstance(promo["fecha_inicio"], str) else promo["fecha_inicio"]
    fecha_fin = datetime.fromisoformat(promo["fecha_fin"]).date() if isinstance(promo["fecha_fin"], str) else promo["fecha_fin"]
    if hoy < fecha_inicio or hoy > fecha_fin:
        print(f"\nLa promocion '{codigo}' no esta vigente en este momento")
        input("\nPresione Enter para continuar...")
        return

    total = 0
    for key, valor in carrito.items():
        if key.startswith("_"):
            continue
        item = json.loads(valor)
        total += item["precio"] * item["cantidad"]

    monto_minimo = float(promo.get("monto_minimo", 0))
    if total < monto_minimo:
        print(f"\nEsta promocion requiere un monto minimo de ${monto_minimo}")
        print(f"Tu carrito suma ${total}. Faltan ${monto_minimo - total}.")
        input("\nPresione Enter para continuar...")
        return

    descuento = float(promo["descuento"])
    descuento_monto = total * descuento / 100
    total_final = total - descuento_monto

    r.hset(clave_carrito, "_promo_codigo", codigo)
    r.hset(clave_carrito, "_promo_id", str(promo["id_promocion"]))
    r.hset(clave_carrito, "_promo_descuento", str(descuento))
    r.hset(clave_carrito, "_promo_descuento_monto", str(descuento_monto))

    print(f"\nPromocion aplicada: {codigo}")
    print(f"  Descripcion: {promo['descripcion']}")
    print(f"  Subtotal: ${total}")
    print(f"  Descuento ({descuento}%): -${descuento_monto:.2f}")
    print(f"  Total con descuento: ${total_final:.2f}")
    input("\nPresione Enter para continuar...")


def buscar_promocion(codigo):
    """Busca primero en Redis (cache), si no esta va a Postgres."""
    r = get_redis()
    cache = r.get(f"promo:{codigo}")
    if cache:
        print("\n(Promocion encontrada en cache Redis)")
        return json.loads(cache)

    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT id_promocion, codigo, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo, condiciones
        FROM promocion WHERE codigo = %s
    """, (codigo,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    print("\n(Promocion encontrada en Postgres, cacheada en Redis)")

    promo = {
        "id_promocion": row[0],
        "codigo": row[1],
        "descripcion": row[2],
        "descuento": float(row[3]),
        "fecha_inicio": str(row[4]),
        "fecha_fin": str(row[5]),
        "monto_minimo": float(row[6]),
        "condiciones": row[7]
    }
    from datetime import datetime
    dias_restantes = (row[5] - datetime.now().date()).days
    if dias_restantes > 0:
        r.set(f"promo:{codigo}", json.dumps(promo), ex=dias_restantes * 24 * 60 * 60)

    return promo