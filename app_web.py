"""
RAPPI TP - Version Web con Streamlit
Frontend que reusa los mismos casos de uso que la app de consola.
"""
import streamlit as st
from use_cases import auth

# Configuracion de la pagina
st.set_page_config(
    page_title="Rappi TP",
    page_icon="🛵",
    layout="wide"
)


# ============================================
# ESTADO DE SESION (equivalente a Redis pero local)
# ============================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None


# ============================================
# FUNCIONES AUXILIARES (login/logout adaptadas para web)
# ============================================
def login_web(email, password, rol):
    """Version del login que no usa input() (para Streamlit)."""
    import bcrypt
    import json
    from connections import get_postgres, get_redis

    config = {
        "cliente": {
            "tabla": "cliente",
            "campos": "id_cliente, nombre, apellido, email, password"
        },
        "establecimiento": {
            "tabla": "establecimiento",
            "campos": "id_establecimiento, nombre, tipo, email, password"
        },
        "repartidor": {
            "tabla": "repartidor",
            "campos": "id_repartidor, nombre, apellido, email, password"
        }
    }

    cfg = config[rol]
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT {cfg['campos']} FROM {cfg['tabla']} WHERE email = %s",
            (email.lower(),)
        )
        row = cur.fetchone()

        if not row:
            return None, f"No existe ningun {rol} con ese email"

        pwd_hash = row[-1]
        if not bcrypt.checkpw(password.encode('utf-8'), pwd_hash.encode('utf-8')):
            return None, "Password incorrecta"

        usuario = {
            "id": row[0],
            "rol": rol,
            "nombre": row[1],
            "email": row[-2]
        }
        if rol == "establecimiento":
            usuario["tipo"] = row[2]

    finally:
        cur.close()
        conn.close()

    # Crear sesion en Redis con TTL de 10 minutos
    r = get_redis()
    clave_sesion = f"sesion:{rol}:{usuario['id']}"
    r.set(clave_sesion, json.dumps(usuario), ex=600)

    return usuario, None


def logout_web():
    if not st.session_state.usuario:
        return
    from connections import get_redis
    r = get_redis()
    u = st.session_state.usuario
    r.delete(f"sesion:{u['rol']}:{u['id']}")
    st.session_state.usuario = None


# ============================================
# PANTALLA DE LOGIN
# ============================================
def pantalla_login():
    st.title("🛵 Rappi TP")
    st.caption("Ingenieria de Datos II - UADE")

    st.markdown("---")
    st.subheader("Ingresar")

    rol = st.selectbox(
        "¿Como queres ingresar?",
        ["cliente", "establecimiento", "repartidor"],
        format_func=lambda x: {
            "cliente": "Soy Cliente",
            "establecimiento": "Soy Establecimiento (restaurante o tienda)",
            "repartidor": "Soy Repartidor"
        }[x]
    )

    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("Email", placeholder="tucorreo@ejemplo.com")
    with col2:
        password = st.text_input("Password", type="password")

    if st.button("Iniciar sesion", type="primary", use_container_width=True):
        if not email or not password:
            st.warning("Completá email y password")
        else:
            with st.spinner("Validando credenciales..."):
                usuario, error = login_web(email, password, rol)
            if error:
                st.error(error)
            else:
                st.session_state.usuario = usuario
                st.success(f"Bienvenido {usuario['nombre']}")
                st.rerun()

    with st.expander("Usuarios de prueba"):
        st.markdown("""
        **Password en todos:** `test123`

        - Clientes: `manu@test.com`, `fiona@test.com`, `lucho@test.com`
        - Establecimientos: `sushi@test.com`, `bk@test.com`, `farmacia@test.com`
        - Repartidores: `juan@test.com`, `maria@test.com`, `carlos@test.com`
        """)


# ============================================
# DASHBOARD SEGUN ROL
# ============================================
def pantalla_dashboard():
    u = st.session_state.usuario

    # Sidebar con navegacion
    with st.sidebar:
        st.markdown(f"### {u['nombre']}")
        st.caption(f"Rol: {u['rol'].capitalize()}")
        st.caption(f"Email: {u['email']}")
        st.markdown("---")

        if u["rol"] == "cliente":
            seccion = st.radio(
                "Menu",
                ["Catalogos", "Mi carrito", "Confirmar pedido", "Mis pedidos", "Calificar pedido", "Historial"],
                label_visibility="collapsed"
            )
        elif u["rol"] == "establecimiento":
            seccion = st.radio(
                "Menu",
                ["Mi catalogo", "Pedidos recibidos", "Calificaciones", "Promociones"],
                label_visibility="collapsed"
            )
        elif u["rol"] == "repartidor":
            seccion = st.radio(
                "Menu",
                ["Disponibilidad", "Pedidos asignados", "Mis calificaciones"],
                label_visibility="collapsed"
            )

        st.markdown("---")
        if st.button("Cerrar sesion", use_container_width=True):
            logout_web()
            st.rerun()

    # Contenido principal segun rol y seccion
    if u["rol"] == "cliente":
        if seccion == "Catalogos":
            pantalla_catalogos()
        elif seccion == "Mi carrito":
            pantalla_carrito()
        elif seccion == "Confirmar pedido":
            pantalla_confirmar()
        elif seccion == "Mis pedidos":
            pantalla_mis_pedidos()
        elif seccion == "Calificar pedido":
            pantalla_calificar()
        elif seccion == "Historial":
            pantalla_historial()
    elif u["rol"] == "establecimiento":
        st.info(f"Seccion '{seccion}' - Proximamente")
    elif u["rol"] == "repartidor":
        st.info(f"Seccion '{seccion}' - Proximamente")


# ============================================
# PANTALLAS DEL CLIENTE
# ============================================
def pantalla_catalogos():
    from connections import get_postgres, get_mongo, get_redis
    import json

    st.title("Catalogos de establecimientos")

    # Listar establecimientos
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT id_establecimiento, nombre, tipo, direccion
        FROM establecimiento ORDER BY nombre
    """)
    establecimientos = cur.fetchall()
    cur.close()
    conn.close()

    if not establecimientos:
        st.warning("No hay establecimientos registrados todavia")
        return

    # Selector de establecimiento
    nombres = {f"{e[1]} ({e[2]})": e[0] for e in establecimientos}
    seleccion = st.selectbox("Elegi un establecimiento", list(nombres.keys()))
    id_est = nombres[seleccion]

    st.markdown("---")

    # Cargar catalogo (con cache de Redis)
    r = get_redis()
    clave_cache = f"catalogo:establecimiento:{id_est}"
    cache = r.get(clave_cache)
    if cache:
        st.caption("Catalogo cargado desde cache Redis")
        doc = json.loads(cache)
    else:
        db = get_mongo()
        doc = db.catalogo_establecimientos.find_one({"_id": id_est})
        if doc:
            doc["_id"] = str(doc["_id"])
            r.set(clave_cache, json.dumps(doc), ex=300)
            st.caption("Catalogo cargado desde Mongo y guardado en cache")

    if not doc or not doc.get("catalogo"):
        st.info("Este establecimiento todavia no tiene productos")
        return

    # Mostrar productos en cards
    disponibles = [p for p in doc["catalogo"] if p.get("disponible", True)]
    cols = st.columns(3)
    for i, prod in enumerate(disponibles):
        with cols[i % 3]:
            with st.container(border=True):
                st.subheader(prod["nombre"])
                st.markdown(f"**${prod['precio']}**")
                st.caption(f"{prod['categoria']}")
                if prod.get("descripcion"):
                    st.write(prod["descripcion"])
                if prod.get("atributos"):
                    attrs = ", ".join(f"{k}={v}" for k, v in prod["atributos"].items())
                    st.caption(f"_{attrs}_")

                cantidad = st.number_input(
                    "Cantidad", min_value=1, max_value=20, value=1,
                    key=f"cant_{prod['id_producto']}"
                )
                if st.button("Agregar al carrito", key=f"add_{prod['id_producto']}", use_container_width=True):
                    agregar_al_carrito_web(id_est, doc["nombre"], prod, cantidad)
                    st.success(f"Agregado: {cantidad} x {prod['nombre']}")
                    st.rerun()


def agregar_al_carrito_web(id_est, nombre_est, producto, cantidad):
    from connections import get_redis
    import json

    u = st.session_state.usuario
    r = get_redis()
    clave = f"carrito:cliente:{u['id']}"

    # Validar que el carrito sea del mismo establecimiento
    est_actual = r.hget(clave, "_establecimiento_id")
    if est_actual and int(est_actual) != id_est:
        st.error("Tu carrito tiene productos de otro establecimiento. Confirmá ese pedido o vaciá el carrito primero.")
        return

    r.hset(clave, "_establecimiento_id", id_est)
    r.hset(clave, "_establecimiento_nombre", nombre_est)

    item_key = producto["id_producto"]
    existente = r.hget(clave, item_key)
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
    r.hset(clave, item_key, json.dumps(item))
    r.expire(clave, 60 * 60 * 24)


def pantalla_carrito():
    from connections import get_redis
    import json

    st.title("Mi carrito")

    u = st.session_state.usuario
    r = get_redis()
    clave = f"carrito:cliente:{u['id']}"
    carrito = r.hgetall(clave)

    if not carrito:
        st.info("Tu carrito esta vacio. Andá a Catalogos y agregá productos.")
        return

    est_nombre = carrito.get("_establecimiento_nombre", "Desconocido")
    st.subheader(f"Establecimiento: {est_nombre}")

    total = 0
    items = []
    for key, valor in carrito.items():
        if key.startswith("_"):
            continue
        item = json.loads(valor)
        items.append(item)
        total += item["precio"] * item["cantidad"]

    # Tabla de productos
    for item in items:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            st.write(f"**{item['nombre']}**")
        with col2:
            st.write(f"${item['precio']}")
        with col3:
            st.write(f"x {item['cantidad']}")
        with col4:
            st.write(f"**${item['precio'] * item['cantidad']}**")

    st.markdown("---")

    # Promo aplicada (si hay)
    codigo_promo = carrito.get("_promo_codigo")
    if codigo_promo:
        descuento = float(carrito.get("_promo_descuento_monto", 0))
        st.success(f"Promocion aplicada: **{codigo_promo}** (-${descuento:.2f})")
        st.metric("Total con descuento", f"${total - descuento:.2f}", delta=f"-${descuento:.2f}")
    else:
        st.metric("Total", f"${total}")

    # Aplicar promocion
    if not codigo_promo:
        with st.expander("Aplicar codigo de promocion"):
            codigo = st.text_input("Codigo", placeholder="Ej: SUSHI20")
            if st.button("Aplicar"):
                aplicar_promo_web(codigo, total)
                st.rerun()

    # TTL del carrito
    ttl = r.ttl(clave)
    if ttl > 0:
        h = ttl // 3600
        m = (ttl % 3600) // 60
        st.caption(f"El carrito expira en {h}h {m}min (Redis TTL)")

    # Vaciar carrito
    if st.button("Vaciar carrito", type="secondary"):
        r.delete(clave)
        st.rerun()


def aplicar_promo_web(codigo, total_carrito):
    from connections import get_postgres, get_redis
    from datetime import datetime
    import json

    if not codigo:
        return

    codigo = codigo.upper().strip()
    r = get_redis()

    # Buscar en cache primero, despues en Postgres
    cache = r.get(f"promo:{codigo}")
    if cache:
        promo = json.loads(cache)
    else:
        conn = get_postgres()
        cur = conn.cursor()
        cur.execute("""
            SELECT id_promocion, codigo, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo
            FROM promocion WHERE codigo = %s
        """, (codigo,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            st.error(f"La promocion '{codigo}' no existe")
            return

        promo = {
            "id_promocion": row[0],
            "codigo": row[1],
            "descripcion": row[2],
            "descuento": float(row[3]),
            "fecha_inicio": str(row[4]),
            "fecha_fin": str(row[5]),
            "monto_minimo": float(row[6])
        }

    # Validar fechas
    hoy = datetime.now().date()
    fi = datetime.fromisoformat(promo["fecha_inicio"]).date()
    ff = datetime.fromisoformat(promo["fecha_fin"]).date()
    if hoy < fi or hoy > ff:
        st.error("La promocion no esta vigente")
        return

    # Validar monto minimo
    if total_carrito < promo["monto_minimo"]:
        st.error(f"Se necesita un monto minimo de ${promo['monto_minimo']}")
        return

    descuento_monto = total_carrito * promo["descuento"] / 100
    u = st.session_state.usuario
    clave_carrito = f"carrito:cliente:{u['id']}"
    r.hset(clave_carrito, "_promo_codigo", codigo)
    r.hset(clave_carrito, "_promo_id", str(promo["id_promocion"]))
    r.hset(clave_carrito, "_promo_descuento", str(promo["descuento"]))
    r.hset(clave_carrito, "_promo_descuento_monto", str(descuento_monto))
    st.success(f"Promocion aplicada: {codigo} ({promo['descuento']}% de descuento)")


def pantalla_confirmar():
    from connections import get_postgres, get_mongo, get_redis, get_cassandra, get_neo4j
    import json
    from datetime import datetime

    st.title("Confirmar pedido")

    u = st.session_state.usuario
    r = get_redis()
    clave_carrito = f"carrito:cliente:{u['id']}"
    carrito = r.hgetall(clave_carrito)

    if not carrito:
        st.info("Tu carrito esta vacio. Andá a Catalogos primero.")
        return

    # Resumen
    id_est = int(carrito["_establecimiento_id"])
    nombre_est = carrito.get("_establecimiento_nombre")
    items = []
    total = 0
    for key, valor in carrito.items():
        if key.startswith("_"):
            continue
        item = json.loads(valor)
        items.append(item)
        total += item["precio"] * item["cantidad"]

    codigo_promo = carrito.get("_promo_codigo")
    id_promo = carrito.get("_promo_id")
    descuento = float(carrito.get("_promo_descuento_monto", 0))
    total_final = total - descuento

    st.subheader(f"Pedido a {nombre_est}")
    for item in items:
        st.write(f"  {item['cantidad']} x {item['nombre']} - ${item['precio'] * item['cantidad']}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Subtotal", f"${total}")
    with col2:
        if codigo_promo:
            st.metric("Total con descuento", f"${total_final:.2f}", delta=f"-${descuento:.2f}")
        else:
            st.metric("Total", f"${total}")

    st.markdown("---")

    # Direcciones del cliente
    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT nro_direccion, calle, numero, ciudad, alias
        FROM direccion WHERE id_cliente = %s ORDER BY nro_direccion
    """, (u["id"],))
    direcciones = cur.fetchall()
    cur.close()
    conn.close()

    if not direcciones:
        st.error("Necesitás registrar al menos una direccion. (Por ahora hacelo desde la app de consola)")
        return

    dir_opts = {f"{d[1]} {d[2]}, {d[3]} ({d[4] or 'sin alias'})": d[0] for d in direcciones}
    dir_seleccionada = st.selectbox("Direccion de entrega", list(dir_opts.keys()))
    nro_direccion = dir_opts[dir_seleccionada]

    st.markdown("---")

    if st.button("CONFIRMAR PEDIDO", type="primary", use_container_width=True):
        # Lock anti-doble-click
        clave_lock = f"lock:checkout:cliente:{u['id']}"
        if not r.set(clave_lock, "1", nx=True, ex=10):
            st.warning("Ya estas procesando un pedido")
            return

        try:
            with st.spinner("Creando pedido en las 5 bases..."):
                total = total_final

                # Postgres
                conn = get_postgres()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO pedido (total, id_cliente, id_establecimiento, id_cliente_dir)
                    VALUES (%s, %s, %s, %s) RETURNING id_pedido, fecha_hora
                """, (total, u["id"], id_est, nro_direccion))
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

                if id_promo:
                    cur.execute("""
                        INSERT INTO promocion_pedido (id_promocion, id_pedido, descuento_aplicado)
                        VALUES (%s, %s, %s)
                    """, (int(id_promo), id_pedido, descuento))

                conn.commit()
                cur.close()
                conn.close()

                # Cassandra
                session = get_cassandra()
                session.execute("""
                    INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
                    VALUES (%s, %s, %s, %s)
                """, (id_pedido, fecha_hora, "creado", "Pedido creado por el cliente"))

                # Neo4j
                driver = get_neo4j()
                with driver.session() as ses:
                    ses.run("MERGE (c:Cliente {id: $id}) SET c.nombre = $n",
                            id=u["id"], n=u["nombre"])
                    ses.run("MERGE (e:Establecimiento {id: $id}) SET e.nombre = $n",
                            id=id_est, n=nombre_est)
                    ses.run("MERGE (p:Pedido {id: $id}) SET p.fecha = $f, p.total = $t",
                            id=id_pedido, f=str(fecha_hora), t=total)
                    ses.run("""
                        MATCH (c:Cliente {id: $c}), (p:Pedido {id: $p})
                        MERGE (c)-[:REALIZO]->(p)
                    """, c=u["id"], p=id_pedido)
                    for item in items:
                        ses.run("MERGE (pr:Producto {id: $i}) SET pr.nombre = $n, pr.precio = $pr",
                                i=item["id_producto"], n=item["nombre"], pr=item["precio"])
                        ses.run("""
                            MATCH (p:Pedido {id: $p}), (pr:Producto {id: $pr})
                            MERGE (p)-[r:CONTIENE]->(pr) SET r.cantidad = $c
                        """, p=id_pedido, pr=item["id_producto"], c=item["cantidad"])
                        ses.run("""
                            MATCH (pr:Producto {id: $pr}), (e:Establecimiento {id: $e})
                            MERGE (pr)-[:OFRECIDO_POR]->(e)
                        """, pr=item["id_producto"], e=id_est)
                driver.close()

                # Redis: vaciar carrito
                r.delete(clave_carrito)

            st.success(f"Pedido #{id_pedido} creado correctamente")
            st.balloons()

            with st.expander("Ver detalles de lo que paso en cada base"):
                st.markdown(f"""
                - **Postgres**: insertó pedido, detalle, pago{', y promocion_pedido' if id_promo else ''}
                - **Cassandra**: insertó estado inicial "creado"
                - **Neo4j**: creó nodos y relaciones (Cliente → Pedido → Productos → Establecimiento)
                - **Redis**: vació el carrito y liberó el lock anti-doble-click
                """)
        finally:
            r.delete(clave_lock)


def pantalla_mis_pedidos():
    from connections import get_postgres, get_cassandra

    st.title("Mis pedidos")
    u = st.session_state.usuario

    conn = get_postgres()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_cliente = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    pedidos = cur.fetchall()
    cur.close()
    conn.close()

    if not pedidos:
        st.info("Todavia no hiciste ningun pedido")
        return

    session = get_cassandra()
    for id_p, fecha, total, est in pedidos:
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Pedido #{id_p}**")
                st.caption(fecha.strftime('%d/%m/%Y %H:%M'))
            with col2:
                st.write(est)
                st.metric("Total", f"${total}")
            with col3:
                rows = list(session.execute(
                    "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1",
                    (id_p,)
                ))
                estado = rows[0].estado.upper() if rows else "?"
                st.metric("Estado", estado)

            # Timeline desde Cassandra
            with st.expander("Ver historial completo"):
                rows = list(session.execute(
                    "SELECT estado, fecha_hora, observacion FROM estado_pedido WHERE id_pedido = %s",
                    (id_p,)
                ))
                rows.sort(key=lambda r: r.fecha_hora)
                for r in rows:
                    obs = f" - {r.observacion}" if r.observacion else ""
                    st.write(f"  `{r.fecha_hora.strftime('%d/%m %H:%M:%S')}` → **{r.estado.upper()}**{obs}")


def pantalla_calificar():
    st.title("Calificar pedido")
    st.info("Proximamente - usa la app de consola por ahora")


def pantalla_historial():
    st.title("Historial de pedidos")
    st.info("Proximamente - usa la app de consola por ahora")


# ============================================
# ROUTING PRINCIPAL
# ============================================
def main():
    if st.session_state.usuario is None:
        pantalla_login()
    else:
        pantalla_dashboard()


if __name__ == "__main__":
    main()