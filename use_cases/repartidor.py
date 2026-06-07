"""
Casos de uso del rol REPARTIDOR.
"""
from datetime import datetime
from connections import get_postgres, get_redis


def pedir_dato(label, requerido=True):
    while True:
        valor = input(f"  {label} (0 para cancelar): ").strip()
        if valor == "0":
            return None
        if valor or not requerido:
            return valor
        print("  Este campo es obligatorio")


# ============================================
# MARCAR COMO DISPONIBLE (Postgres + Redis Set)
# ============================================
def marcar_disponible(repartidor):
    print("\nMARCAR COMO DISPONIBLE\n")

    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE repartidor SET disponibilidad = true
            WHERE id_repartidor = %s
        """, (repartidor["id"],))
        conn.commit()
    finally:
        cur.close()
        conn.close()

    # Redis: mover al set de disponibles
    r = get_redis()
    r.smove("repartidores:ocupados", "repartidores:disponibles", str(repartidor["id"]))
    r.sadd("repartidores:disponibles", str(repartidor["id"]))

    print(f"Estado: DISPONIBLE")
    print("Ya estas listo para recibir pedidos")
    input("\nPresione Enter para continuar...")


# ============================================
# MARCAR COMO OCUPADO (Postgres + Redis Set)
# ============================================
def marcar_ocupado(repartidor):
    print("\nMARCAR COMO OCUPADO\n")

    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE repartidor SET disponibilidad = false
            WHERE id_repartidor = %s
        """, (repartidor["id"],))
        conn.commit()
    finally:
        cur.close()
        conn.close()

    r = get_redis()
    r.smove("repartidores:disponibles", "repartidores:ocupados", str(repartidor["id"]))
    r.sadd("repartidores:ocupados", str(repartidor["id"]))

    print(f"Estado: OCUPADO")
    print("No vas a recibir nuevos pedidos hasta que vuelvas a estar disponible")
    input("\nPresione Enter para continuar...")


# ============================================
# VER PEDIDOS ASIGNADOS / DISPONIBLES PARA TOMAR
# ============================================
def ver_pedidos_asignados(repartidor):
    print("\nMIS PEDIDOS Y PEDIDOS DISPONIBLES\n")

    from connections import get_cassandra
    session = get_cassandra()
    conn = get_postgres()
    cur = conn.cursor()

    # 1. Mis pedidos asignados
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre, c.nombre, c.apellido,
               d.calle, d.numero, d.ciudad
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        JOIN cliente c ON p.id_cliente = c.id_cliente
        JOIN direccion d ON d.id_cliente = p.id_cliente AND d.nro_direccion = p.id_cliente_dir
        WHERE p.id_repartidor = %s
        ORDER BY p.fecha_hora DESC
    """, (repartidor["id"],))
    mios = cur.fetchall()

    # 2. Pedidos disponibles para tomar (sin repartidor + estado listo_para_retirar)
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_repartidor IS NULL
        ORDER BY p.fecha_hora DESC
    """)
    todos_sin_repartidor = cur.fetchall()

    cur.close()
    conn.close()

    # Filtrar los que estan en estado listo_para_retirar (consultando Cassandra)
    disponibles = []
    for id_p, fecha, total, est in todos_sin_repartidor:
        rows = list(session.execute(
            "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1",
            (id_p,)
        ))
        if rows and rows[0]["estado"] == "listo_para_retirar":
            disponibles.append((id_p, fecha, total, est))

    # Mostrar mis pedidos
    if mios:
        print(f"MIS PEDIDOS ({len(mios)}):\n")
        for id_p, fecha, total, est_nombre, c_nom, c_ape, calle, num, ciudad in mios:
            rows = list(session.execute(
                "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1",
                (id_p,)
            ))
            estado = rows[0]["estado"].upper() if rows else "?"
            print(f"  Pedido #{id_p}  -  {est_nombre}  -  Estado: {estado}")
            print(f"    Cliente: {c_nom} {c_ape}")
            print(f"    Direccion entrega: {calle} {num}, {ciudad}")
            print(f"    Total: ${total}")
            print()
    else:
        print("No tenes pedidos asignados\n")

    # Mostrar pedidos disponibles para tomar
    if disponibles:
        print(f"\nPEDIDOS DISPONIBLES PARA TOMAR ({len(disponibles)}):\n")
        for i, (id_p, fecha, total, est) in enumerate(disponibles, 1):
            print(f"  {i}. Pedido #{id_p}  -  {est}  -  ${total}")
        print("  0. No tomar ninguno")

        opcion = input("\n  Tomar pedido numero: ").strip()
        if opcion == "0" or not opcion:
            input("\nPresione Enter para continuar...")
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(disponibles):
                tomar_pedido(repartidor, disponibles[idx][0])
                return
        except ValueError:
            pass
        print("  Opcion invalida")
    else:
        print("No hay pedidos disponibles para tomar en este momento")

    input("\nPresione Enter para continuar...")


def tomar_pedido(repartidor, id_pedido):
    """Asigna un pedido al repartidor. Lock + update + estado en Cassandra."""
    r = get_redis()

    # Lock anti-concurrencia: que dos repartidores no tomen el mismo pedido
    lock_key = f"lock:repartidor:asignacion:{id_pedido}"
    if not r.set(lock_key, repartidor["id"], nx=True, ex=5):
        print("\nOtro repartidor ya esta tomando este pedido")
        input("\nPresione Enter para continuar...")
        return

    try:
        conn = get_postgres()
        cur = conn.cursor()
        try:
            # Verificar que el pedido siga sin repartidor (alguien puede haberlo tomado entre que lo viste y lo confirmaste)
            cur.execute("SELECT id_repartidor FROM pedido WHERE id_pedido = %s", (id_pedido,))
            actual = cur.fetchone()
            if actual is None:
                print("\nEse pedido no existe")
                return
            if actual[0] is not None:
                print("\nEse pedido ya fue tomado por otro repartidor")
                return

            cur.execute("""
                UPDATE pedido SET id_repartidor = %s WHERE id_pedido = %s
            """, (repartidor["id"], id_pedido))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"\nError: {e}")
            return
        finally:
            cur.close()
            conn.close()

        # Cassandra: registrar estado
        from connections import get_cassandra
        session = get_cassandra()
        session.execute("""
            INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
            VALUES (%s, %s, %s, %s)
        """, (id_pedido, datetime.utcnow(), "repartidor_asignado",
              f"Tomado por {repartidor['nombre']}"))

        # Redis: marcar repartidor como ocupado
        r.smove("repartidores:disponibles", "repartidores:ocupados", str(repartidor["id"]))

        # Neo4j: relacion ENTREGO (la creamos cuando entregue, no ahora)

        print(f"\nPedido #{id_pedido} asignado a vos")
    finally:
        r.delete(lock_key)

    input("\nPresione Enter para continuar...")


# ============================================
# ACTUALIZAR ESTADO DE ENTREGA
# ============================================
def actualizar_estado_entrega(repartidor):
    print("\nACTUALIZAR ESTADO DE ENTREGA\n")

    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, e.nombre, c.nombre, c.apellido
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_repartidor = %s
        ORDER BY p.fecha_hora DESC
    """, (repartidor["id"],))
    pedidos = cur.fetchall()
    cur.close()
    conn.close()

    if not pedidos:
        print("No tenes pedidos asignados")
        input("\nPresione Enter para continuar...")
        return

    from connections import get_cassandra
    session = get_cassandra()

    print("Tus pedidos:\n")
    pedidos_con_estado = []
    for id_p, fecha, est, cn, ca in pedidos:
        rows = list(session.execute(
            "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1",
            (id_p,)
        ))
        estado = rows[0]["estado"] if rows else "?"
        pedidos_con_estado.append((id_p, fecha, est, cn, ca, estado))

    for i, (id_p, _, est, cn, ca, estado) in enumerate(pedidos_con_estado, 1):
        print(f"  {i}. Pedido #{id_p}  -  {est}  -  {cn} {ca}  -  Estado: {estado.upper()}")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi un pedido: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(pedidos_con_estado):
                id_pedido_sel = pedidos_con_estado[idx][0]
                estado_actual = pedidos_con_estado[idx][5]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    estados_repartidor = ["en_camino", "entregado"]
    print(f"\nEstado actual: {estado_actual.upper()}")
    print("\nNuevo estado:")
    for i, est in enumerate(estados_repartidor, 1):
        print(f"  {i}. {est}")
    print("  0. Cancelar")

    while True:
        opcion = input("\n  Elegi el nuevo estado: ").strip()
        if opcion == "0":
            return
        try:
            idx = int(opcion) - 1
            if 0 <= idx < len(estados_repartidor):
                nuevo_estado = estados_repartidor[idx]
                break
        except ValueError:
            pass
        print("  Opcion invalida")

    observacion = input("  Observacion (opcional): ").strip()

    # Cassandra: insertar estado
    session.execute("""
        INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
        VALUES (%s, %s, %s, %s)
    """, (id_pedido_sel, datetime.utcnow(), nuevo_estado, observacion or None))

    # Si entrego, crear relacion en Neo4j y liberar al repartidor
    if nuevo_estado == "entregado":
        try:
            from connections import get_neo4j
            driver = get_neo4j()
            with driver.session() as ses:
                ses.run("""
                    MERGE (r:Repartidor {id: $id_r})
                    SET r.nombre = $nombre
                """, id_r=repartidor["id"], nombre=repartidor["nombre"])

                ses.run("""
                    MATCH (r:Repartidor {id: $id_r}), (p:Pedido {id: $id_p})
                    MERGE (r)-[:ENTREGO]->(p)
                """, id_r=repartidor["id"], id_p=id_pedido_sel)
            driver.close()

            # Liberar al repartidor (vuelve a disponibles)
            r_conn = get_redis()
            r_conn.smove("repartidores:ocupados", "repartidores:disponibles", str(repartidor["id"]))
        except Exception as e:
            print(f"\n(Aviso: {e})")

    print(f"\nEstado actualizado: pedido #{id_pedido_sel} -> {nuevo_estado.upper()}")
    input("\nPresione Enter para continuar...")


# ============================================
# VER MIS CALIFICACIONES (placeholder)
# ============================================
def ver_mis_calificaciones(repartidor):
    print("\nMIS CALIFICACIONES\n")

    from connections import get_mongo
    db = get_mongo()
    califs = list(db.calificaciones.find({
        "id_repartidor": repartidor["id"],
        "calificacion_repartidor": {"$exists": True}
    }))

    if not califs:
        print("Todavia no tenes calificaciones")
        input("\nPresione Enter para continuar...")
        return

    puntajes = [c["calificacion_repartidor"]["puntaje"] for c in califs]
    promedio = sum(puntajes) / len(puntajes)

    print(f"Total: {len(califs)} calificaciones")
    print(f"Promedio: {promedio:.2f} / 5\n")
    print("-" * 70)

    for c in califs:
        cr = c["calificacion_repartidor"]
        print(f"  Pedido: {c['_id']}")
        print(f"  Puntaje: {cr['puntaje']} / 5")
        if cr.get("comentario"):
            print(f"  Comentario: {cr['comentario']}")
        print("-" * 70)

    input("\nPresione Enter para continuar...")