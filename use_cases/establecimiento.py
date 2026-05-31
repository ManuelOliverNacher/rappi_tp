"""
Casos de uso del rol ESTABLECIMIENTO (restaurantes y tiendas).
"""
import uuid
from connections import get_mongo, get_redis, get_postgres


def pedir_dato(label, requerido=True):
    while True:
        valor = input(f"  {label}: ").strip()
        if valor or not requerido:
            return valor
        print("  Este campo es obligatorio")


# ============================================
# AGREGAR PRODUCTO AL CATALOGO (Mongo)
# ============================================
def agregar_producto(establecimiento):
    print(f"\nAGREGAR PRODUCTO AL CATALOGO\n")
    print("(Escribi '0' en cualquier campo para cancelar)\n")

    nombre = pedir_dato("Nombre del producto")
    if nombre is None: return

    while True:
        precio_str = pedir_dato("Precio")
        if precio_str is None: return
        try:
            precio = float(precio_str)
            break
        except ValueError:
            print("  El precio tiene que ser un numero")

    categoria = pedir_dato("Categoria (ej: rolls, entrada, bebida, postre, principal)")
    if categoria is None: return

    descripcion = pedir_dato("Descripcion", requerido=False)
    if descripcion is None: return

    # Atributos: ahora con menu guiado
    atributos = pedir_atributos(categoria)

    nuevo_producto = {
        "id_producto": f"prod_{uuid.uuid4().hex[:8]}",
        "nombre": nombre,
        "precio": precio,
        "categoria": categoria,
        "descripcion": descripcion,
        "disponible": True,
        "atributos": atributos
    }

    db = get_mongo()
    id_est = establecimiento["id"]

    existente = db.catalogo_establecimientos.find_one({"_id": id_est})

    if existente:
        db.catalogo_establecimientos.update_one(
            {"_id": id_est},
            {"$push": {"catalogo": nuevo_producto}}
        )
    else:
        db.catalogo_establecimientos.insert_one({
            "_id": id_est,
            "nombre": establecimiento["nombre"],
            "tipo": establecimiento.get("tipo", "restaurante"),
            "catalogo": [nuevo_producto]
        })

    r = get_redis()
    r.delete(f"catalogo:establecimiento:{id_est}")

    print(f"\nProducto agregado correctamente")
    print(f"ID del producto: {nuevo_producto['id_producto']}")
    if atributos:
        print(f"Atributos: {atributos}")
    input("\nPresione Enter para continuar...")


def pedir_atributos(categoria):
    """Pide atributos al usuario con un menu guiado segun la categoria."""
    respuesta = input("\n  Queres agregar atributos? (s/n): ").strip().lower()
    if respuesta != "s":
        return {}

    # Atributos sugeridos por categoria (se pueden agregar mas)
    sugerencias_por_categoria = {
        "rolls": [
            ("piezas", "Cantidad de piezas", "numero"),
            ("picante", "Es picante?", "si_no"),
            ("sin_tacc", "Es sin TACC?", "si_no"),
            ("vegetariano", "Es vegetariano?", "si_no"),
            ("ingredientes", "Ingredientes principales", "texto"),
        ],
        "entrada": [
            ("porciones", "Cantidad de porciones", "numero"),
            ("picante", "Es picante?", "si_no"),
            ("sin_tacc", "Es sin TACC?", "si_no"),
            ("vegetariano", "Es vegetariano?", "si_no"),
        ],
        "principal": [
            ("porciones", "Cantidad de porciones", "numero"),
            ("picante", "Es picante?", "si_no"),
            ("sin_tacc", "Es sin TACC?", "si_no"),
            ("vegetariano", "Es vegetariano?", "si_no"),
            ("ingredientes", "Ingredientes principales", "texto"),
        ],
        "postre": [
            ("porciones", "Cantidad de porciones", "numero"),
            ("sin_tacc", "Es sin TACC?", "si_no"),
            ("sin_azucar", "Es sin azucar?", "si_no"),
        ],
        "bebida": [
            ("ml", "Mililitros", "numero"),
            ("alcohol", "Contiene alcohol?", "si_no"),
            ("graduacion", "Graduacion alcoholica (si aplica)", "texto"),
        ],
    }

    # Atributos genericos para categorias no conocidas (ej: tienda, farmacia)
    sugerencias_genericas = [
        ("marca", "Marca", "texto"),
        ("unidad", "Unidad de venta (ej: caja, kg, unidad)", "texto"),
        ("contenido", "Contenido (ej: 500g, 1L)", "texto"),
    ]

    sugerencias = sugerencias_por_categoria.get(categoria.lower(), sugerencias_genericas)
    atributos = {}

    while True:
        print("\n  Atributos disponibles:")
        for i, (clave, label, _) in enumerate(sugerencias, 1):
            marca = " (ya agregado)" if clave in atributos else ""
            print(f"    {i}. {label}{marca}")
        print(f"    {len(sugerencias) + 1}. Otro (lo escribis vos)")
        print(f"    0. Terminar")

        opcion = input("\n  Elegi un atributo: ").strip()

        if opcion == "0":
            break

        if opcion == str(len(sugerencias) + 1):
            # Atributo custom
            clave_custom = input("  Nombre del atributo: ").strip()
            if not clave_custom:
                continue
            valor_custom = input(f"  Valor de '{clave_custom}': ").strip()
            if valor_custom:
                atributos[clave_custom] = valor_custom
            continue

        try:
            idx = int(opcion) - 1
            if idx < 0 or idx >= len(sugerencias):
                print("  Opcion invalida")
                continue
        except ValueError:
            print("  Opcion invalida")
            continue

        clave, label, tipo = sugerencias[idx]

        if tipo == "si_no":
            while True:
                v = input(f"  {label} (si/no): ").strip().lower()
                if v in ("si", "no"):
                    atributos[clave] = v
                    break
                print("  Respondé 'si' o 'no'")
        elif tipo == "numero":
            while True:
                v = input(f"  {label}: ").strip()
                if v.isdigit():
                    atributos[clave] = int(v)
                    break
                print("  Tiene que ser un numero entero")
        else:
            v = input(f"  {label}: ").strip()
            if v:
                atributos[clave] = v

    return atributos

# ============================================
# VER MI CATALOGO (Mongo)
# ============================================
def ver_mi_catalogo(establecimiento):
    print(f"\nMI CATALOGO\n")

    db = get_mongo()
    doc = db.catalogo_establecimientos.find_one({"_id": establecimiento["id"]})

    if not doc or not doc.get("catalogo"):
        print("Todavia no tenes productos en el catalogo")
        input("\nPresione Enter para continuar...")
        return

    print(f"Establecimiento: {doc['nombre']} ({doc['tipo']})")
    print(f"Productos: {len(doc['catalogo'])}\n")
    print("-" * 60)

    for prod in doc["catalogo"]:
        disp = "DISPONIBLE" if prod.get("disponible", True) else "NO DISPONIBLE"
        print(f"  [{prod['id_producto']}]  {prod['nombre']}  -  ${prod['precio']}  -  {disp}")
        print(f"      Categoria: {prod['categoria']}")
        if prod.get("descripcion"):
            print(f"      {prod['descripcion']}")
        if prod.get("atributos"):
            attrs = ", ".join(f"{k}={v}" for k, v in prod["atributos"].items())
            print(f"      Atributos: {attrs}")
        print()

    input("\nPresione Enter para continuar...")


# ============================================
# PLACEHOLDERS (lo demas viene despues)
# ============================================
def actualizar_producto(establecimiento):
    print("Actualizar producto - Aun no implementado")
    input("\nPresione Enter para continuar...")


def ver_pedidos_pendientes(establecimiento):
    print("\nPEDIDOS DE MI ESTABLECIMIENTO\n")

    # Postgres: traer todos los pedidos del establecimiento
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, c.nombre, c.apellido
        FROM pedido p
        JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_establecimiento = %s
        ORDER BY p.fecha_hora DESC
    """, (establecimiento["id"],))
    pedidos = cur.fetchall()
    cur.close()
    conn.close()

    if not pedidos:
        print("Todavia no recibiste pedidos")
        input("\nPresione Enter para continuar...")
        return

    # Cassandra: estado actual de cada pedido
    from connections import get_cassandra
    session = get_cassandra()

    print(f"Pedidos recibidos ({len(pedidos)}):\n")
    print("-" * 70)
    for id_pedido, fecha, total, nombre, apellido in pedidos:
        rows = list(session.execute("""
            SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1
        """, (id_pedido,)))
        estado = rows[0].estado.upper() if rows else "DESCONOCIDO"

        print(f"  Pedido #{id_pedido}  -  {fecha.strftime('%d/%m %H:%M')}")
        print(f"  Cliente: {nombre} {apellido}")
        print(f"  Total: ${total}")
        print(f"  Estado: {estado}")
        print("-" * 70)

    input("\nPresione Enter para continuar...")


def cambiar_estado_pedido(establecimiento):
    print("\nCAMBIAR ESTADO DE UN PEDIDO\n")

    # Postgres: traer pedidos del establecimiento
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, c.nombre, c.apellido
        FROM pedido p
        JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_establecimiento = %s
        ORDER BY p.fecha_hora DESC
    """, (establecimiento["id"],))
    pedidos = cur.fetchall()
    cur.close()
    conn.close()

    if not pedidos:
        print("No tenes pedidos para gestionar")
        input("\nPresione Enter para continuar...")
        return

    # Cassandra: estado actual
    from connections import get_cassandra
    session = get_cassandra()

    print("Tus pedidos:\n")
    pedidos_con_estado = []
    for id_pedido, fecha, nombre, apellido in pedidos:
        rows = list(session.execute("""
            SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1
        """, (id_pedido,)))
        estado = rows[0].estado if rows else "desconocido"
        pedidos_con_estado.append((id_pedido, fecha, nombre, apellido, estado))

    for i, (id_p, fecha, n, a, est) in enumerate(pedidos_con_estado, 1):
        print(f"  {i}. Pedido #{id_p}  -  {n} {a}  -  Estado: {est.upper()}")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi un pedido: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(pedidos_con_estado):
                id_pedido_sel, _, _, _, estado_actual = pedidos_con_estado[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    # Estados validos que puede setear el establecimiento
    estados_establecimiento = ["aceptado", "preparando", "listo_para_retirar", "cancelado"]

    print(f"\nEstado actual: {estado_actual.upper()}")
    print("\nNuevo estado:")
    for i, est in enumerate(estados_establecimiento, 1):
        print(f"  {i}. {est}")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi el nuevo estado: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(estados_establecimiento):
                nuevo_estado = estados_establecimiento[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    observacion = input("  Observacion (opcional, Enter para saltear): ").strip()

    # Cassandra: insertar nuevo estado con fecha actual
    from datetime import datetime
    ahora = datetime.utcnow()
    try:
        session.execute("""
            INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
            VALUES (%s, %s, %s, %s)
        """, (id_pedido_sel, ahora, nuevo_estado, observacion or None))

        # Redis: invalidar cache de estado del pedido (si despues lo cacheamos)
        r = get_redis()
        r.delete(f"estado:pedido:{id_pedido_sel}")

        print(f"\nEstado actualizado: pedido #{id_pedido_sel} -> {nuevo_estado.upper()}")
    except Exception as e:
        print(f"\nError: {e}")

    input("\nPresione Enter para continuar...")


def cambiar_estado_pedido(establecimiento):
    print("\nCAMBIAR ESTADO DE UN PEDIDO\n")

    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, c.nombre, c.apellido
        FROM pedido p
        JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_establecimiento = %s
        ORDER BY p.fecha_hora DESC
    """, (establecimiento["id"],))
    pedidos = cur.fetchall()
    cur.close()
    conn.close()

    if not pedidos:
        print("No tenes pedidos para gestionar")
        input("\nPresione Enter para continuar...")
        return

    from connections import get_cassandra
    session = get_cassandra()

    print("Tus pedidos:\n")
    pedidos_con_estado = []
    for id_pedido, fecha, nombre, apellido in pedidos:
        rows = list(session.execute("""
            SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1
        """, (id_pedido,)))
        estado = rows[0].estado if rows else "desconocido"
        pedidos_con_estado.append((id_pedido, fecha, nombre, apellido, estado))

    for i, (id_p, fecha, n, a, est) in enumerate(pedidos_con_estado, 1):
        print(f"  {i}. Pedido #{id_p}  -  {n} {a}  -  Estado: {est.upper()}")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi un pedido: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(pedidos_con_estado):
                id_pedido_sel, _, _, _, estado_actual = pedidos_con_estado[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    estados_establecimiento = ["aceptado", "preparando", "listo_para_retirar", "cancelado"]

    print(f"\nEstado actual: {estado_actual.upper()}")
    print("\nNuevo estado:")
    for i, est in enumerate(estados_establecimiento, 1):
        print(f"  {i}. {est}")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi el nuevo estado: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(estados_establecimiento):
                nuevo_estado = estados_establecimiento[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    observacion = input("  Observacion (opcional, Enter para saltear): ").strip()

    from datetime import datetime
    ahora = datetime.utcnow()
    try:
        session.execute("""
            INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
            VALUES (%s, %s, %s, %s)
        """, (id_pedido_sel, ahora, nuevo_estado, observacion or None))

        r = get_redis()
        r.delete(f"estado:pedido:{id_pedido_sel}")

        print(f"\nEstado actualizado: pedido #{id_pedido_sel} -> {nuevo_estado.upper()}")
    except Exception as e:
        print(f"\nError: {e}")

    input("\nPresione Enter para continuar...")

def ver_calificaciones(establecimiento):
    print("\nCALIFICACIONES RECIBIDAS\n")

    db = get_mongo()
    califs = list(db.calificaciones.find({"id_establecimiento": establecimiento["id"]}))

    if not califs:
        print("Todavia no recibiste calificaciones")
        input("\nPresione Enter para continuar...")
        return

    # Calcular promedio
    puntajes = [c["calificacion_establecimiento"]["puntaje"] for c in califs]
    promedio = sum(puntajes) / len(puntajes)

    print(f"Total de calificaciones: {len(califs)}")
    print(f"Promedio: {promedio:.2f} / 5\n")
    print("-" * 70)

    for c in califs:
        ce = c["calificacion_establecimiento"]
        print(f"  Pedido: {c['_id']}")
        print(f"  Puntaje: {ce['puntaje']} / 5")
        if ce.get("comentario"):
            print(f"  Comentario: {ce['comentario']}")
        if ce.get("respuesta_establecimiento"):
            print(f"  Tu respuesta: {ce['respuesta_establecimiento']}")
        else:
            print(f"  Tu respuesta: (sin responder)")
        print("-" * 70)

    input("\nPresione Enter para continuar...")


def responder_calificacion(establecimiento):
    print("\nRESPONDER A UNA CALIFICACION\n")

    db = get_mongo()
    # Solo las que no tienen respuesta todavia
    califs = list(db.calificaciones.find({
        "id_establecimiento": establecimiento["id"],
        "calificacion_establecimiento.respuesta_establecimiento": None
    }))

    if not califs:
        print("No hay calificaciones pendientes de responder")
        input("\nPresione Enter para continuar...")
        return

    print("Calificaciones sin responder:\n")
    for i, c in enumerate(califs, 1):
        ce = c["calificacion_establecimiento"]
        comentario = ce.get("comentario") or "(sin comentario)"
        print(f"  {i}. {c['_id']}  -  Puntaje: {ce['puntaje']}/5  -  \"{comentario}\"")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi una calificacion: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(califs):
                calif_sel = califs[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    respuesta = input("\n  Tu respuesta: ").strip()
    if not respuesta:
        print("\nNo se guardo (respuesta vacia)")
        input("\nPresione Enter para continuar...")
        return

    # Mongo: actualizar el campo respuesta_establecimiento
    db.calificaciones.update_one(
        {"_id": calif_sel["_id"]},
        {"$set": {"calificacion_establecimiento.respuesta_establecimiento": respuesta}}
    )

    print(f"\nRespuesta guardada en la calificacion {calif_sel['_id']}")
    input("\nPresione Enter para continuar...")


def crear_promocion(establecimiento):
    print("\nCREAR PROMOCION\n")
    print("(Escribi '0' en cualquier campo para cancelar)\n")

    codigo = pedir_dato("Codigo de la promocion (ej: VERANO20)")
    if codigo is None: return
    codigo = codigo.upper()

    descripcion = pedir_dato("Descripcion")
    if descripcion is None: return

    while True:
        descuento_str = pedir_dato("Descuento (% off, ej: 20)")
        if descuento_str is None: return
        try:
            descuento = float(descuento_str)
            if 0 < descuento <= 100:
                break
            print("  El descuento tiene que estar entre 1 y 100")
        except ValueError:
            print("  Tiene que ser un numero")

    while True:
        monto_min_str = pedir_dato("Monto minimo de compra (0 si no aplica)", requerido=False)
        if monto_min_str is None: return
        if not monto_min_str:
            monto_minimo = 0
            break
        try:
            monto_minimo = float(monto_min_str)
            break
        except ValueError:
            print("  Tiene que ser un numero")

    # Fechas
    from datetime import datetime, timedelta
    hoy = datetime.now().date()

    while True:
        dias_str = pedir_dato("Duracion en dias (ej: 30)")
        if dias_str is None: return
        try:
            dias = int(dias_str)
            if dias > 0:
                break
            print("  Tiene que ser mayor a 0")
        except ValueError:
            print("  Tiene que ser un numero entero")

    fecha_inicio = hoy
    fecha_fin = hoy + timedelta(days=dias)

    condiciones = pedir_dato("Condiciones (texto libre)", requerido=False)
    if condiciones is None: return

    conn = get_postgres()
    cur = conn.cursor()
    try:
        # Verificar que el codigo no exista
        cur.execute("SELECT id_promocion FROM promocion WHERE codigo = %s", (codigo,))
        if cur.fetchone():
            print(f"\nYa existe una promocion con el codigo {codigo}")
            input("\nPresione Enter para continuar...")
            return

        cur.execute("""
            INSERT INTO promocion (codigo, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo, condiciones, creada_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_promocion
        """, (codigo, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo, condiciones, establecimiento["nombre"]))
        id_promo = cur.fetchone()[0]
        conn.commit()

        # Redis: cachear la promocion con TTL hasta la fecha de fin
        import json
        r = get_redis()
        clave_cache = f"promo:{codigo}"
        promo_data = {
            "id_promocion": id_promo,
            "codigo": codigo,
            "descripcion": descripcion,
            "descuento": descuento,
            "fecha_inicio": str(fecha_inicio),
            "fecha_fin": str(fecha_fin),
            "monto_minimo": monto_minimo,
            "condiciones": condiciones
        }
        ttl_segundos = dias * 24 * 60 * 60
        r.set(clave_cache, json.dumps(promo_data), ex=ttl_segundos)

        print(f"\nPromocion creada correctamente")
        print(f"  Codigo: {codigo}")
        print(f"  Descuento: {descuento}%")
        print(f"  Valida hasta: {fecha_fin}")
        print(f"  Cacheada en Redis con TTL de {dias} dias")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
    finally:
        cur.close()
        conn.close()

    input("\nPresione Enter para continuar...")