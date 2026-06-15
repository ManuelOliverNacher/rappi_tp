"""
RAPPI TP — Frontend Web
Diseño basado en el proyecto Stitch "Rappi Fullstack Academic Clone".
"""
import streamlit as st

st.set_page_config(
    page_title="Rappi TP",
    page_icon="🛵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;700;800&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Hanken Grotesk', sans-serif !important; }
h1 { font-weight: 800 !important; font-size: 2rem !important; color: #1A1A1A; }
h2 { font-weight: 700 !important; color: #1A1A1A; }
h3 { font-weight: 700 !important; color: #333; }

.stApp { background-color: #FFFFFF; }

[data-testid="stSidebar"] { background-color: #1A1A1A !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.6) !important; font-size: 0.9rem; }
[data-testid="stSidebar"] .stRadio [data-checked="true"] label,
[data-testid="stSidebar"] .stRadio [aria-checked="true"] + div { color: #FF441A !important; font-weight: 700 !important; }

.rappi-logo { font-family:'Hanken Grotesk',sans-serif; font-size:2rem; font-weight:800; color:#FF441A; letter-spacing:-1px; line-height:1; }
.rappi-tagline { color:rgba(255,255,255,0.4); font-size:0.72rem; margin-top:3px; }

[data-testid="stButton"] > button[kind="primary"] {
    background-color:#FF441A !important; border:none !important;
    border-radius:8px !important; font-weight:700 !important;
    font-size:0.95rem !important; color:white !important;
    transition: background 0.15s;
}
[data-testid="stButton"] > button[kind="primary"]:hover { background-color:#E53B14 !important; }

.price-tag { font-family:'Hanken Grotesk',sans-serif; font-size:1.25rem; font-weight:700; color:#FF441A; }
.card-title { font-family:'Hanken Grotesk',sans-serif; font-weight:700; font-size:1rem; color:#1A1A1A; }

.badge { display:inline-block; padding:3px 12px; border-radius:100px; font-size:0.75rem; font-weight:700; }
.badge-creado       { background:rgba(21,101,192,0.10); color:#1565C0; }
.badge-aceptado     { background:rgba(245,127,23,0.10); color:#E65100; }
.badge-preparando   { background:rgba(230,81,0,0.10);   color:#E65100; }
.badge-listo        { background:rgba(46,125,50,0.10);  color:#2E7D32; }
.badge-en_camino    { background:rgba(106,27,154,0.10); color:#6A1B9A; }
.badge-entregado    { background:rgba(27,94,32,0.10);   color:#1B5E20; }
.badge-cancelado    { background:rgba(183,28,28,0.10);  color:#B71C1C; }

[data-testid="stMetricValue"] { font-family:'Hanken Grotesk',sans-serif !important; font-weight:700 !important; color:#1A1A1A !important; }
</style>
""", unsafe_allow_html=True)

# ── SESIÓN ─────────────────────────────────────────────────────────────────────
for key in ("usuario", "seccion"):
    if key not in st.session_state:
        st.session_state[key] = None


# ── HELPERS ────────────────────────────────────────────────────────────────────
def badge(estado: str) -> str:
    cls = {
        "creado": "badge-creado", "aceptado": "badge-aceptado",
        "preparando": "badge-preparando", "listo_para_retirar": "badge-listo",
        "repartidor_asignado": "badge-en_camino", "en_camino": "badge-en_camino",
        "entregado": "badge-entregado", "cancelado": "badge-cancelado",
    }.get(estado.lower(), "badge-creado")
    return f'<span class="badge {cls}">{estado.upper().replace("_", " ")}</span>'


def estado_ultimo(session_cass, id_pedido):
    rows = list(session_cass.execute(
        "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1", (id_pedido,)
    ))
    if not rows:
        return None
    r0 = rows[0]
    return r0["estado"] if isinstance(r0, dict) else r0.estado


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════
def login_web(email: str, password: str, rol: str):
    import bcrypt, json
    from connections import get_postgres, get_redis

    if rol == "admin":
        if email == "admin" and password == "admin1234":
            u = {"id": 0, "rol": "admin", "nombre": "Admin", "email": "admin"}
            get_redis().set("sesion:admin:0", json.dumps(u), ex=600)
            return u, None
        return None, "Credenciales incorrectas"

    cfg = {
        "cliente":         ("cliente",        "id_cliente,         nombre, apellido, email, password"),
        "establecimiento": ("establecimiento", "id_establecimiento, nombre, tipo,    email, password"),
        "repartidor":      ("repartidor",      "id_repartidor,      nombre, apellido, email, password"),
    }
    tabla, campos = cfg[rol]
    conn = get_postgres(); cur = conn.cursor()
    try:
        cur.execute(f"SELECT {campos} FROM {tabla} WHERE email = %s", (email.lower(),))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not row:
        return None, f"No existe ningún {rol} con ese email"
    if not bcrypt.checkpw(password.encode(), row[-1].encode()):
        return None, "Password incorrecta"

    u = {"id": row[0], "rol": rol, "nombre": row[1], "email": row[-2]}
    if rol == "establecimiento":
        u["tipo"] = row[2]
    get_redis().set(f"sesion:{rol}:{u['id']}", json.dumps(u), ex=600)
    return u, None


def registrar_web(rol: str, datos: dict):
    import bcrypt
    from connections import get_postgres

    conn = get_postgres(); cur = conn.cursor()
    try:
        pwd_hash = bcrypt.hashpw(datos["password"].encode(), bcrypt.gensalt()).decode()

        if rol == "cliente":
            cur.execute("SELECT id_cliente FROM cliente WHERE email=%s", (datos["email"],))
            if cur.fetchone():
                return None, "Ya existe una cuenta con ese email"
            cur.execute(
                "INSERT INTO cliente (nombre,apellido,email,telefono,password) VALUES (%s,%s,%s,%s,%s) RETURNING id_cliente",
                (datos["nombre"], datos["apellido"], datos["email"].lower(), datos.get("telefono") or None, pwd_hash)
            )
            id_nuevo = cur.fetchone()[0]
            conn.commit()
            return {"id": id_nuevo, "rol": "cliente", "nombre": datos["nombre"], "email": datos["email"].lower()}, None

        elif rol == "establecimiento":
            cur.execute("SELECT id_establecimiento FROM establecimiento WHERE email=%s", (datos["email"],))
            if cur.fetchone():
                return None, "Ya existe una cuenta con ese email"
            cur.execute(
                "INSERT INTO establecimiento (nombre,direccion,telefono,horario,tipo,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_establecimiento",
                (datos["nombre"], datos.get("direccion") or "", datos.get("telefono") or None,
                 datos.get("horario") or None, datos["tipo"], datos["email"].lower(), pwd_hash)
            )
            id_nuevo = cur.fetchone()[0]
            extra = datos.get("extra", "")
            if datos["tipo"] == "restaurante":
                cur.execute("INSERT INTO restaurante (id_establecimiento,especialidad_culinaria) VALUES (%s,%s)", (id_nuevo, extra))
            else:
                cur.execute("INSERT INTO tienda (id_establecimiento,rubro) VALUES (%s,%s)", (id_nuevo, extra))
            conn.commit()
            return {"id": id_nuevo, "rol": "establecimiento", "nombre": datos["nombre"],
                    "email": datos["email"].lower(), "tipo": datos["tipo"]}, None

        elif rol == "repartidor":
            cur.execute("SELECT id_repartidor FROM repartidor WHERE email=%s", (datos["email"],))
            if cur.fetchone():
                return None, "Ya existe una cuenta con ese email"
            cur.execute(
                "INSERT INTO repartidor (nombre,apellido,vehiculo,disponibilidad,telefono,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_repartidor",
                (datos["nombre"], datos["apellido"], datos.get("vehiculo") or "moto",
                 True, datos.get("telefono") or None, datos["email"].lower(), pwd_hash)
            )
            id_nuevo = cur.fetchone()[0]
            conn.commit()
            return {"id": id_nuevo, "rol": "repartidor", "nombre": datos["nombre"], "email": datos["email"].lower()}, None

    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        cur.close(); conn.close()

    return None, "Error desconocido"


def logout():
    u = st.session_state.usuario
    if u:
        from connections import get_redis
        get_redis().delete(f"sesion:{u['rol']}:{u['id']}")
    st.session_state.usuario = None


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA LOGIN / REGISTRO
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_login():
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown('<div class="rappi-logo" style="color:#FF441A;">rappi</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#888;font-size:0.75rem;margin-bottom:1.5rem;">Ingeniería de Datos II — UADE</div>', unsafe_allow_html=True)

        tab_in, tab_reg = st.tabs(["Iniciar sesión", "Registrarse"])

        # ── LOGIN ──
        with tab_in:
            rol = st.selectbox("Rol", ["cliente", "establecimiento", "repartidor", "admin"],
                               format_func=lambda x: {"cliente":"🛒 Cliente","establecimiento":"🍽️ Establecimiento",
                                                       "repartidor":"🛵 Repartidor","admin":"🔧 Admin"}[x],
                               key="login_rol")
            email = st.text_input("Usuario" if rol == "admin" else "Email", key="login_email",
                                  placeholder="admin" if rol == "admin" else "correo@ejemplo.com")
            password = st.text_input("Password", type="password", key="login_pwd")

            if st.button("Entrar", type="primary", use_container_width=True):
                if not email or not password:
                    st.warning("Completá todos los campos.")
                else:
                    with st.spinner("Validando..."):
                        u, err = login_web(email, password, rol)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.usuario = u
                        st.rerun()

            with st.expander("Usuarios de prueba (password: test123)"):
                st.markdown("""
| Rol | Email |
|---|---|
| Cliente | `manu@test.com` · `fiona@test.com` · `lucho@test.com` |
| Establecimiento | `sushi@test.com` · `bk@test.com` · `farmacia@test.com` |
| Repartidor | `juan@test.com` · `maria@test.com` · `carlos@test.com` |
| Admin | usuario: `admin` / password: `admin1234` |

Promos: **VERANO20** · **ENVIOGRATIS**
""")

        # ── REGISTRO ──
        with tab_reg:
            rol_reg = st.selectbox("Quiero registrarme como", ["cliente", "establecimiento", "repartidor"],
                                   format_func=lambda x: {"cliente":"🛒 Cliente","establecimiento":"🍽️ Establecimiento","repartidor":"🛵 Repartidor"}[x],
                                   key="reg_rol")

            with st.form("form_registro"):
                c1, c2 = st.columns(2)
                nombre = c1.text_input("Nombre *")
                apellido = c2.text_input("Apellido *") if rol_reg != "establecimiento" else None
                email_r = st.text_input("Email *")
                tel = st.text_input("Teléfono")

                if rol_reg == "establecimiento":
                    c3, c4 = st.columns(2)
                    tipo_est = c3.selectbox("Tipo", ["restaurante", "tienda"])
                    extra_est = c4.text_input("Especialidad / Rubro *", placeholder="Italiana, Farmacia…")
                    dir_est = st.text_input("Dirección")
                    horario_est = st.text_input("Horario", placeholder="Lun-Vie 10-22")
                elif rol_reg == "repartidor":
                    vehiculo = st.selectbox("Vehículo", ["moto", "auto", "bici"])

                pwd_r  = st.text_input("Password *", type="password")
                pwd_r2 = st.text_input("Repetir password *", type="password")
                submitted = st.form_submit_button("Crear cuenta", type="primary", use_container_width=True)

            if submitted:
                if not nombre or not email_r or not pwd_r:
                    st.error("Completá los campos obligatorios (*).")
                elif pwd_r != pwd_r2:
                    st.error("Las passwords no coinciden.")
                else:
                    datos = {"nombre": nombre, "email": email_r, "password": pwd_r, "telefono": tel}
                    if rol_reg == "cliente":
                        datos["apellido"] = apellido or ""
                    elif rol_reg == "establecimiento":
                        datos.update({"tipo": tipo_est, "extra": extra_est, "direccion": dir_est, "horario": horario_est})
                    elif rol_reg == "repartidor":
                        datos.update({"apellido": "", "vehiculo": vehiculo})

                    with st.spinner("Registrando..."):
                        u, err = registrar_web(rol_reg, datos)
                    if err:
                        st.error(err)
                    else:
                        import json
                        from connections import get_redis
                        get_redis().set(f"sesion:{rol_reg}:{u['id']}", json.dumps(u), ex=600)
                        st.session_state.usuario = u
                        st.success(f"¡Bienvenido, {u['nombre']}!")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
MENUS = {
    "cliente": [
        ("🏪", "Catálogos"),
        ("🛒", "Mi carrito"),
        ("✅", "Confirmar pedido"),
        ("📦", "Mis pedidos"),
        ("⭐", "Calificar pedido"),
        ("📋", "Historial"),
    ],
    "establecimiento": [
        ("🍽️", "Mi catálogo"),
        ("➕", "Agregar producto"),
        ("✏️", "Actualizar producto"),
        ("📋", "Pedidos recibidos"),
        ("🔄", "Cambiar estado"),
        ("⭐", "Calificaciones"),
        ("💬", "Responder reseñas"),
        ("🏷️", "Crear promoción"),
    ],
    "repartidor": [
        ("🟢", "Disponibilidad"),
        ("📦", "Pedidos disponibles"),
        ("🚀", "Actualizar entrega"),
        ("⭐", "Mis calificaciones"),
    ],
    "admin": [
        ("🔌", "Verificar conexiones"),
        ("🌱", "Cargar datos de prueba"),
        ("🗑️", "Limpiar bases"),
        ("📊", "Pedidos por ciudad"),
        ("🏆", "Productos más pedidos"),
        ("🏅", "Locales populares"),
        ("📅", "Categorías fines de semana"),
        ("⚡", "Pedidos rápidos y caros"),
        ("💎", "Top productos"),
    ],
}


def render_sidebar() -> str:
    u = st.session_state.usuario
    with st.sidebar:
        st.markdown('<div class="rappi-logo">rappi</div>', unsafe_allow_html=True)
        st.markdown('<div class="rappi-tagline">Ingeniería de Datos II</div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"<span style='font-weight:700;font-family:Hanken Grotesk,sans-serif'>{u['nombre']}</span>", unsafe_allow_html=True)
        st.caption(f"{u['rol'].capitalize()}  ·  {u['email']}")
        st.markdown("---")

        opciones = MENUS[u["rol"]]
        labels = [f"{ico}  {txt}" for ico, txt in opciones]
        default_idx = 0
        if st.session_state.seccion:
            for i, (_, t) in enumerate(opciones):
                if t == st.session_state.seccion:
                    default_idx = i; break

        seleccion = st.radio("", labels, index=default_idx, label_visibility="collapsed")
        st.session_state.seccion = opciones[labels.index(seleccion)][1]

        st.markdown("---")
        if st.button("Cerrar sesión", use_container_width=True):
            logout(); st.rerun()

    return st.session_state.seccion


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE — CATÁLOGOS
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_catalogos():
    from connections import get_postgres, get_mongo, get_redis
    import json

    st.title("🏪 Catálogos")
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("SELECT id_establecimiento, nombre, tipo, direccion FROM establecimiento ORDER BY nombre")
    establecimientos = cur.fetchall()
    cur.close(); conn.close()

    if not establecimientos:
        st.info("No hay establecimientos registrados."); return

    nombres = {f"{e[1]}  ({e[2]})": e[0] for e in establecimientos}
    seleccion = st.selectbox("Elegí un establecimiento", list(nombres.keys()))
    id_est = nombres[seleccion]

    r = get_redis()
    cache = r.get(f"catalogo:establecimiento:{id_est}")
    if cache:
        doc = json.loads(cache)
        st.caption("📦 Desde caché Redis")
    else:
        db = get_mongo()
        doc = db.catalogo_establecimientos.find_one({"_id": id_est})
        if doc:
            doc["_id"] = str(doc["_id"])
            r.set(f"catalogo:establecimiento:{id_est}", json.dumps(doc), ex=300)
            st.caption("🍃 Desde MongoDB → guardado en Redis (TTL 5 min)")

    if not doc or not doc.get("catalogo"):
        st.info("Este establecimiento no tiene productos."); return

    disponibles = [p for p in doc["catalogo"] if p.get("disponible", True)]
    if not disponibles:
        st.warning("Sin productos disponibles en este momento."); return

    cols = st.columns(3)
    for i, prod in enumerate(disponibles):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f'<div class="card-title">{prod["nombre"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="price-tag">${prod["precio"]:,.0f}</div>', unsafe_allow_html=True)
                st.caption(f"🏷️ {prod['categoria']}")
                if prod.get("descripcion"):
                    st.write(prod["descripcion"])
                if prod.get("atributos"):
                    st.caption("  ·  ".join(f"{k}: {v}" for k, v in prod["atributos"].items()))
                cantidad = st.number_input("Cantidad", 1, 20, 1, key=f"cant_{prod['id_producto']}")
                if st.button("🛒 Agregar al carrito", key=f"add_{prod['id_producto']}", use_container_width=True):
                    _agregar_al_carrito(id_est, doc["nombre"], prod, cantidad)


def _agregar_al_carrito(id_est, nombre_est, producto, cantidad):
    from connections import get_redis
    import json
    u = st.session_state.usuario
    r = get_redis()
    clave = f"carrito:cliente:{u['id']}"
    est_actual = r.hget(clave, "_establecimiento_id")
    if est_actual and int(est_actual) != id_est:
        st.error("Tu carrito ya tiene productos de otro establecimiento. Confirmalo o vacialo primero.")
        return
    r.hset(clave, "_establecimiento_id", id_est)
    r.hset(clave, "_establecimiento_nombre", nombre_est)
    existente = r.hget(clave, producto["id_producto"])
    if existente:
        item = json.loads(existente)
        item["cantidad"] += cantidad
    else:
        item = {"id_producto": producto["id_producto"], "nombre": producto["nombre"],
                "precio": producto["precio"], "cantidad": cantidad}
    r.hset(clave, producto["id_producto"], json.dumps(item))
    r.expire(clave, 86400)
    st.success(f"✅ {cantidad} × **{producto['nombre']}** agregado")
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE — CARRITO
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_carrito():
    from connections import get_redis
    from datetime import datetime
    import json

    st.title("🛒 Mi carrito")
    u = st.session_state.usuario
    r = get_redis()
    clave = f"carrito:cliente:{u['id']}"
    carrito = r.hgetall(clave)

    if not carrito:
        st.info("Tu carrito está vacío. Andá a Catálogos y agregá productos."); return

    st.markdown(f"### 📍 {carrito.get('_establecimiento_nombre', '')}")
    total = 0
    items = []
    for key, val in carrito.items():
        if key.startswith("_"): continue
        item = json.loads(val)
        items.append(item)
        total += item["precio"] * item["cantidad"]

    for item in items:
        c1, c2, c3, c4, c5 = st.columns([4, 2, 1, 2, 1])
        c1.write(f"**{item['nombre']}**")
        c2.write(f"${item['precio']:,.0f} c/u")
        c3.write(f"×{item['cantidad']}")
        c4.markdown(f'<span class="price-tag">${item["precio"]*item["cantidad"]:,.0f}</span>', unsafe_allow_html=True)
        with c5:
            if st.button("🗑️", key=f"del_{item['id_producto']}"):
                r.hdel(clave, item["id_producto"])
                if not any(not k.startswith("_") for k in r.hkeys(clave)):
                    r.delete(clave)
                st.rerun()

    st.markdown("---")
    codigo_promo = carrito.get("_promo_codigo")
    descuento = float(carrito.get("_promo_descuento_monto", 0))

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Subtotal", f"${total:,.0f}")
    with c2:
        if codigo_promo:
            st.metric("Total con descuento", f"${total - descuento:,.2f}", delta=f"-${descuento:,.2f}")

    if codigo_promo:
        st.success(f"🏷️ Promo **{codigo_promo}** aplicada ({carrito.get('_promo_descuento', '?')}% off)")
        if st.button("❌ Quitar promoción"):
            for k in ["_promo_codigo", "_promo_id", "_promo_descuento", "_promo_descuento_monto"]:
                r.hdel(clave, k)
            st.rerun()
    else:
        with st.expander("🏷️ Tenés un código de promo?"):
            codigo = st.text_input("Código", placeholder="Ej: VERANO20").upper().strip()
            if st.button("Aplicar", type="primary"):
                _aplicar_promo(codigo, total); st.rerun()

    ttl = r.ttl(clave)
    if ttl > 0:
        st.caption(f"⏱️ Carrito expira en {ttl // 3600}h {(ttl % 3600) // 60}min (Redis TTL)")

    st.markdown("---")
    ca, cb = st.columns(2)
    with ca:
        if st.button("🗑️ Vaciar carrito"):
            r.delete(clave); st.rerun()
    with cb:
        if st.button("➡️ Confirmar pedido", type="primary"):
            st.session_state.seccion = "Confirmar pedido"; st.rerun()


def _aplicar_promo(codigo, total_carrito):
    from connections import get_postgres, get_redis
    from datetime import datetime
    import json

    if not codigo:
        st.warning("Ingresá un código."); return
    r = get_redis()
    cache = r.get(f"promo:{codigo}")
    if cache:
        promo = json.loads(cache)
    else:
        conn = get_postgres(); cur = conn.cursor()
        cur.execute("""
            SELECT id_promocion, codigo, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo
            FROM promocion WHERE codigo = %s
        """, (codigo,))
        row = cur.fetchone(); cur.close(); conn.close()
        if not row:
            st.error(f"La promoción '{codigo}' no existe."); return
        promo = {"id_promocion": row[0], "codigo": row[1], "descripcion": row[2],
                 "descuento": float(row[3]), "fecha_inicio": str(row[4]),
                 "fecha_fin": str(row[5]), "monto_minimo": float(row[6])}

    hoy = datetime.now().date()
    if hoy < datetime.fromisoformat(promo["fecha_inicio"]).date() or hoy > datetime.fromisoformat(promo["fecha_fin"]).date():
        st.error("La promoción no está vigente."); return
    if total_carrito < promo["monto_minimo"]:
        st.error(f"Monto mínimo requerido: ${promo['monto_minimo']:,.0f}. Tu carrito: ${total_carrito:,.0f}."); return

    monto_desc = total_carrito * promo["descuento"] / 100
    u = st.session_state.usuario
    c = f"carrito:cliente:{u['id']}"
    r.hset(c, "_promo_codigo", codigo)
    r.hset(c, "_promo_id", str(promo["id_promocion"]))
    r.hset(c, "_promo_descuento", str(promo["descuento"]))
    r.hset(c, "_promo_descuento_monto", str(monto_desc))
    st.success(f"Promoción **{codigo}** aplicada: {promo['descuento']}% off (-${monto_desc:,.2f})")


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE — CONFIRMAR PEDIDO
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_confirmar():
    from connections import get_postgres, get_redis, get_cassandra, get_neo4j
    from datetime import datetime
    import json

    st.title("✅ Confirmar pedido")
    u = st.session_state.usuario
    r = get_redis()
    clave_carrito = f"carrito:cliente:{u['id']}"
    carrito = r.hgetall(clave_carrito)

    if not carrito:
        st.info("Tu carrito está vacío."); return

    id_est = int(carrito["_establecimiento_id"])
    nombre_est = carrito.get("_establecimiento_nombre", "")
    items, total = [], 0
    for k, v in carrito.items():
        if k.startswith("_"): continue
        item = json.loads(v)
        items.append(item)
        total += item["precio"] * item["cantidad"]

    codigo_promo = carrito.get("_promo_codigo")
    id_promo = carrito.get("_promo_id")
    descuento = float(carrito.get("_promo_descuento_monto", 0))
    total_final = total - descuento

    st.markdown(f"### 🍽️ {nombre_est}")
    for item in items:
        st.write(f"  • {item['cantidad']} × {item['nombre']}  —  ${item['precio'] * item['cantidad']:,.0f}")
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.metric("Subtotal", f"${total:,.0f}")
    if codigo_promo:
        c2.metric("Total final", f"${total_final:,.2f}", delta=f"-${descuento:,.2f}")
    else:
        c2.metric("Total", f"${total:,.0f}")

    st.markdown("---")
    st.subheader("📍 Dirección de entrega")
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("SELECT nro_direccion, calle, numero, ciudad, alias FROM direccion WHERE id_cliente=%s ORDER BY nro_direccion", (u["id"],))
    direcciones = cur.fetchall(); cur.close(); conn.close()

    with st.expander("➕ Agregar nueva dirección", expanded=not bool(direcciones)):
        with st.form("nueva_dir"):
            dc1, dc2 = st.columns(2)
            calle  = dc1.text_input("Calle")
            numero = dc2.text_input("Número")
            dc3, dc4, dc5 = st.columns(3)
            ciudad = dc3.text_input("Ciudad")
            cp     = dc4.text_input("Código Postal")
            alias  = dc5.text_input("Alias (Casa, Trabajo…)")
            if st.form_submit_button("Guardar dirección"):
                if calle and ciudad:
                    conn2 = get_postgres(); cur2 = conn2.cursor()
                    cur2.execute("SELECT COALESCE(MAX(nro_direccion),0)+1 FROM direccion WHERE id_cliente=%s", (u["id"],))
                    nro = cur2.fetchone()[0]
                    cur2.execute("INSERT INTO direccion (id_cliente,nro_direccion,calle,numero,ciudad,cp,alias) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                                 (u["id"], nro, calle, numero or None, ciudad, cp or None, alias or None))
                    conn2.commit(); cur2.close(); conn2.close()
                    st.success("Dirección guardada."); st.rerun()
                else:
                    st.warning("Calle y ciudad son obligatorias.")

    conn = get_postgres(); cur = conn.cursor()
    cur.execute("SELECT nro_direccion, calle, numero, ciudad, alias FROM direccion WHERE id_cliente=%s ORDER BY nro_direccion", (u["id"],))
    direcciones = cur.fetchall(); cur.close(); conn.close()

    if not direcciones:
        st.error("Necesitás al menos una dirección registrada."); return

    dir_opts = {f"{d[1]} {d[2] or ''}, {d[3]}  ({d[4] or 'sin alias'})": d[0] for d in direcciones}
    nro_dir = dir_opts[st.selectbox("Seleccioná tu dirección", list(dir_opts.keys()))]
    metodo_pago = st.selectbox("💳 Método de pago", ["efectivo", "tarjeta_credito", "tarjeta_debito"])
    st.markdown("---")

    if st.button("🛵  CONFIRMAR PEDIDO", type="primary", use_container_width=True):
        clave_lock = f"lock:checkout:cliente:{u['id']}"
        if not r.set(clave_lock, "1", nx=True, ex=10):
            st.warning("Ya estás procesando un pedido. Esperá un momento."); return
        try:
            with st.spinner("Registrando en las 5 bases de datos..."):
                conn = get_postgres(); cur = conn.cursor()
                cur.execute("INSERT INTO pedido (total,id_cliente,id_establecimiento,id_cliente_dir) VALUES (%s,%s,%s,%s) RETURNING id_pedido, fecha_hora",
                            (total_final, u["id"], id_est, nro_dir))
                id_pedido, fecha_hora = cur.fetchone()
                for item in items:
                    subtotal = item["precio"] * item["cantidad"]
                    cur.execute("INSERT INTO detalle_pedido (id_pedido,id_producto,cantidad,precio_unitario,subtotal) VALUES (%s,%s,%s,%s,%s)",
                                (id_pedido, item["id_producto"], item["cantidad"], item["precio"], subtotal))
                cur.execute("INSERT INTO pago (id_pedido,monto,metodo,estado) VALUES (%s,%s,%s,%s)",
                            (id_pedido, total_final, metodo_pago, "pendiente"))
                if id_promo:
                    cur.execute("INSERT INTO promocion_pedido (id_promocion,id_pedido,descuento_aplicado) VALUES (%s,%s,%s)",
                                (int(id_promo), id_pedido, descuento))
                conn.commit(); cur.close(); conn.close()

                session = get_cassandra()
                session.execute("INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
                                (id_pedido, fecha_hora, "creado", "Pedido creado por el cliente"))

                driver = get_neo4j()
                with driver.session() as ses:
                    ses.run("MERGE (c:Cliente {id:$id}) SET c.nombre=$n", id=u["id"], n=u["nombre"])
                    ses.run("MERGE (e:Establecimiento {id:$id}) SET e.nombre=$n", id=id_est, n=nombre_est)
                    ses.run("MERGE (p:Pedido {id:$id}) SET p.fecha=$f, p.total=$t", id=id_pedido, f=str(fecha_hora), t=total_final)
                    ses.run("MATCH (c:Cliente {id:$c}),(p:Pedido {id:$p}) MERGE (c)-[:REALIZO]->(p)", c=u["id"], p=id_pedido)
                    for item in items:
                        ses.run("MERGE (pr:Producto {id:$i}) SET pr.nombre=$n, pr.precio=$pr", i=item["id_producto"], n=item["nombre"], pr=item["precio"])
                        ses.run("MATCH (p:Pedido {id:$p}),(pr:Producto {id:$pr}) MERGE (p)-[r:CONTIENE]->(pr) SET r.cantidad=$c", p=id_pedido, pr=item["id_producto"], c=item["cantidad"])
                        ses.run("MATCH (pr:Producto {id:$pr}),(e:Establecimiento {id:$e}) MERGE (pr)-[:OFRECIDO_POR]->(e)", pr=item["id_producto"], e=id_est)
                driver.close()
                r.delete(clave_carrito)

            st.success(f"🎉 Pedido **#{id_pedido}** confirmado")
            st.balloons()
            with st.expander("¿Qué pasó en cada base?"):
                st.markdown(f"""
- **PostgreSQL** → pedido + detalle + pago{' + promocion_pedido' if id_promo else ''}
- **Cassandra** → estado inicial "creado"
- **Neo4j** → nodos y relaciones (Cliente → Pedido → Productos → Establecimiento)
- **Redis** → carrito eliminado + lock liberado
""")
        finally:
            r.delete(clave_lock)


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE — MIS PEDIDOS
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_mis_pedidos():
    from connections import get_postgres, get_cassandra

    st.title("📦 Mis pedidos")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre
        FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_cliente = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    pedidos = cur.fetchall(); cur.close(); conn.close()

    if not pedidos:
        st.info("Todavía no hiciste ningún pedido."); return

    session = get_cassandra()
    for id_p, fecha, total, est in pedidos:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.markdown(f'<div class="card-title">Pedido #{id_p}</div>', unsafe_allow_html=True)
                st.caption(f"{fecha.strftime('%d/%m/%Y %H:%M')}  ·  {est}")
            with c2:
                st.metric("Total", f"${total:,.2f}")
            with c3:
                est_actual = estado_ultimo(session, id_p)
                if est_actual:
                    st.markdown(badge(est_actual), unsafe_allow_html=True)
                else:
                    st.caption("Sin estado")

            with st.expander("Ver historial de estados"):
                rows = list(session.execute("SELECT estado, fecha_hora, observacion FROM estado_pedido WHERE id_pedido = %s", (id_p,)))
                def _g(r, k): return r[k] if isinstance(r, dict) else getattr(r, k)
                def _ts(v):
                    from datetime import datetime as _dt
                    return _dt.fromisoformat(v) if isinstance(v, str) else v
                rows.sort(key=lambda r: _ts(_g(r, "fecha_hora")))
                for row in rows:
                    fh = _ts(_g(row, "fecha_hora"))
                    obs = f" — {_g(row, 'observacion')}" if _g(row, 'observacion') else ""
                    st.write(f"`{fh.strftime('%d/%m %H:%M')}` → {badge(_g(row, 'estado'))}{obs}", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE — CALIFICAR
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_calificar():
    from connections import get_postgres, get_cassandra, get_mongo, get_neo4j
    from datetime import datetime

    st.title("⭐ Calificar pedido")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, e.id_establecimiento, e.nombre,
               r.id_repartidor, r.nombre, r.apellido
        FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        LEFT JOIN repartidor r ON p.id_repartidor = r.id_repartidor
        WHERE p.id_cliente = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    pedidos = cur.fetchall(); cur.close(); conn.close()

    if not pedidos:
        st.info("Todavía no hiciste ningún pedido."); return

    session = get_cassandra()
    entregados = [p for p in pedidos if estado_ultimo(session, p[0]) == "entregado"]
    if not entregados:
        st.info("No tenés pedidos entregados para calificar."); return

    db = get_mongo()
    sin_calif = [p for p in entregados if not db.calificaciones.find_one({"_id": f"pedido_{p[0]}"})]
    if not sin_calif:
        st.success("¡Ya calificaste todos tus pedidos entregados! 🎉"); return

    opts = {f"Pedido #{p[0]} — {p[3]}": p for p in sin_calif}
    pedido_sel = opts[st.selectbox("Elegí un pedido", list(opts.keys()))]
    id_pedido, fecha, id_est, est_nombre, id_rep, rep_n, rep_a = pedido_sel

    st.markdown(f"### 🍽️ {est_nombre}")
    puntaje_est = st.slider("Puntaje del establecimiento", 1, 5, 5, format="%d ⭐", key="pe")
    comentario_est = st.text_area("Comentario (opcional)", key="ce", height=80)

    puntaje_rep = None
    if id_rep:
        st.markdown(f"### 🛵 {rep_n} {rep_a or ''}")
        puntaje_rep = st.slider("Puntaje del repartidor", 1, 5, 5, format="%d ⭐", key="pr")
        comentario_rep = st.text_area("Comentario (opcional)", key="cr", height=80)

    if st.button("💾 Guardar calificación", type="primary"):
        doc = {
            "_id": f"pedido_{id_pedido}", "id_cliente": u["id"],
            "id_establecimiento": id_est, "id_repartidor": id_rep,
            "fecha": datetime.utcnow().isoformat(),
            "calificacion_establecimiento": {"puntaje": puntaje_est, "comentario": comentario_est or None, "respuesta_establecimiento": None}
        }
        if puntaje_rep is not None:
            doc["calificacion_repartidor"] = {"puntaje": puntaje_rep, "comentario": comentario_rep or None}
        db.calificaciones.insert_one(doc)
        try:
            driver = get_neo4j()
            with driver.session() as ses:
                ses.run("MATCH (c:Cliente {id:$c}),(e:Establecimiento {id:$e}) MERGE (c)-[r:CALIFICO]->(e) SET r.puntaje=$p", c=u["id"], e=id_est, p=puntaje_est)
                if id_rep and puntaje_rep:
                    ses.run("MATCH (c:Cliente {id:$c}),(r:Repartidor {id:$r}) MERGE (c)-[rel:CALIFICO]->(r) SET rel.puntaje=$p", c=u["id"], r=id_rep, p=puntaje_rep)
            driver.close()
        except Exception as e:
            st.warning(f"Neo4j: {e}")
        st.success("✅ Calificación guardada en MongoDB + Neo4j"); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE — HISTORIAL
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_historial():
    from connections import get_postgres, get_mongo, get_redis
    import json

    st.title("📋 Historial de pedidos")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre, e.tipo
        FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_cliente = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    pedidos = cur.fetchall()
    if not pedidos:
        cur.close(); conn.close(); st.info("Todavía no hiciste ningún pedido."); return

    db = get_mongo()
    for id_pedido, fecha, total, est_nombre, est_tipo in pedidos:
        cur.execute("SELECT id_producto, cantidad, precio_unitario, subtotal FROM detalle_pedido WHERE id_pedido = %s", (id_pedido,))
        detalle = cur.fetchall()
        productos_info = []
        for id_prod, cant, precio, subtotal in detalle:
            doc = db.catalogo_establecimientos.find_one({"catalogo.id_producto": id_prod}, {"catalogo.$": 1})
            nombre_prod = doc["catalogo"][0]["nombre"] if (doc and doc.get("catalogo")) else str(id_prod)
            productos_info.append((nombre_prod, cant, precio, subtotal))

        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.markdown(f'<div class="card-title">Pedido #{id_pedido}  —  {est_nombre}</div>', unsafe_allow_html=True)
                st.caption(fecha.strftime("%d/%m/%Y %H:%M"))
            with c2:
                st.metric("Total", f"${total:,.2f}")
            with c3:
                r = get_redis()
                if r.hget(f"carrito:cliente:{u['id']}", "_establecimiento_id"):
                    st.caption("Carrito activo, confirmalo primero")
                else:
                    if st.button("🔁 Volver a pedir", key=f"repedir_{id_pedido}"):
                        _rearmar_carrito(u, id_pedido, db, r); st.rerun()
            with st.expander("Ver detalle"):
                for nombre, cant, precio, subtotal in productos_info:
                    st.write(f"  • {cant} × {nombre}  —  ${precio:,.0f} c/u = **${subtotal:,.0f}**")
    cur.close(); conn.close()


def _rearmar_carrito(u, id_pedido, db, r):
    from connections import get_postgres
    import json
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("SELECT p.id_establecimiento, e.nombre FROM pedido p JOIN establecimiento e ON p.id_establecimiento=e.id_establecimiento WHERE p.id_pedido=%s", (id_pedido,))
    cab = cur.fetchone()
    if not cab: cur.close(); conn.close(); return
    id_est, nombre_est = cab
    cur.execute("SELECT id_producto, cantidad FROM detalle_pedido WHERE id_pedido=%s", (id_pedido,))
    items = cur.fetchall(); cur.close(); conn.close()
    clave = f"carrito:cliente:{u['id']}"
    r.hset(clave, "_establecimiento_id", id_est)
    r.hset(clave, "_establecimiento_nombre", nombre_est)
    for id_prod, cant in items:
        doc = db.catalogo_establecimientos.find_one({"catalogo.id_producto": id_prod}, {"catalogo.$": 1})
        if doc and doc.get("catalogo"):
            prod = doc["catalogo"][0]
            if prod.get("disponible", True):
                r.hset(clave, id_prod, json.dumps({"id_producto": id_prod, "nombre": prod["nombre"], "precio": prod["precio"], "cantidad": cant}))
    r.expire(clave, 86400)
    st.success(f"🛒 Carrito armado desde el pedido #{id_pedido}")


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — MI CATÁLOGO
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_mi_catalogo():
    from connections import get_mongo, get_redis

    st.title("🍽️ Mi catálogo")
    u = st.session_state.usuario
    db = get_mongo()
    doc = db.catalogo_establecimientos.find_one({"_id": u["id"]})

    if not doc or not doc.get("catalogo"):
        st.info("Todavía no tenés productos. Andá a 'Agregar producto'."); return

    st.caption(f"**{doc['nombre']}** ({doc['tipo']}) — {len(doc['catalogo'])} productos")
    r = get_redis()

    for prod in doc["catalogo"]:
        disp = prod.get("disponible", True)
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            with c1:
                st.markdown(f'<div class="card-title">{prod["nombre"]}</div>', unsafe_allow_html=True)
                st.caption(prod.get("categoria", ""))
            with c2:
                if prod.get("descripcion"): st.caption(prod["descripcion"])
                if prod.get("atributos"): st.caption("  ·  ".join(f"{k}: {v}" for k, v in prod["atributos"].items()))
            with c3:
                st.markdown(f'<div class="price-tag">${prod["precio"]:,.0f}</div>', unsafe_allow_html=True)
            with c4:
                nuevo_disp = st.toggle("Disponible", value=disp, key=f"disp_{prod['id_producto']}")
                if nuevo_disp != disp:
                    db.catalogo_establecimientos.update_one(
                        {"_id": u["id"], "catalogo.id_producto": prod["id_producto"]},
                        {"$set": {"catalogo.$.disponible": nuevo_disp}}
                    )
                    r.delete(f"catalogo:establecimiento:{u['id']}")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — AGREGAR PRODUCTO
# ══════════════════════════════════════════════════════════════════════════════
ATRIBUTOS_POR_CATEGORIA = {
    "rolls":    [("piezas","Piezas","num"),("picante","Picante","bool"),("sin_tacc","Sin TACC","bool"),("vegetariano","Vegetariano","bool"),("ingredientes","Ingredientes","txt")],
    "entrada":  [("porciones","Porciones","num"),("picante","Picante","bool"),("sin_tacc","Sin TACC","bool"),("vegetariano","Vegetariano","bool")],
    "principal":[("porciones","Porciones","num"),("picante","Picante","bool"),("sin_tacc","Sin TACC","bool"),("vegetariano","Vegetariano","bool"),("ingredientes","Ingredientes","txt")],
    "postre":   [("porciones","Porciones","num"),("sin_tacc","Sin TACC","bool"),("sin_azucar","Sin azúcar","bool")],
    "bebida":   [("ml","Mililitros","num"),("alcohol","Contiene alcohol","bool"),("graduacion","Graduación","txt")],
}
ATRIBUTOS_GENERICOS = [("marca","Marca","txt"),("unidad","Unidad","txt"),("contenido","Contenido","txt")]


def pantalla_agregar_producto():
    from connections import get_mongo, get_redis
    import uuid

    st.title("➕ Agregar producto")
    u = st.session_state.usuario

    with st.form("nuevo_producto"):
        c1, c2 = st.columns(2)
        nombre    = c1.text_input("Nombre *")
        precio    = c2.number_input("Precio *", min_value=0.0, step=100.0)
        c3, c4 = st.columns(2)
        categoria = c3.text_input("Categoría *", placeholder="rolls, entrada, principal, postre, bebida…")
        descripcion = c4.text_input("Descripción")

        sugerencias = ATRIBUTOS_POR_CATEGORIA.get(categoria.lower(), ATRIBUTOS_GENERICOS) if categoria else []
        atributos = {}
        if sugerencias:
            st.markdown("**Atributos**")
            for clave, label, tipo in sugerencias:
                a1, a2 = st.columns([2, 3])
                a1.caption(label)
                with a2:
                    if tipo == "bool":
                        val = st.selectbox("", ["—","si","no"], key=f"attr_{clave}")
                        if val != "—": atributos[clave] = val
                    elif tipo == "num":
                        val = st.number_input("", min_value=0, step=1, key=f"attr_{clave}")
                        if val: atributos[clave] = int(val)
                    else:
                        val = st.text_input("", key=f"attr_{clave}")
                        if val: atributos[clave] = val

        submitted = st.form_submit_button("Guardar producto", type="primary")

    if submitted:
        if not nombre or not categoria:
            st.error("Nombre y categoría son obligatorios."); return
        nuevo = {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": nombre,
                 "precio": precio, "categoria": categoria, "descripcion": descripcion or "",
                 "disponible": True, "atributos": atributos}
        db = get_mongo()
        existente = db.catalogo_establecimientos.find_one({"_id": u["id"]})
        if existente:
            db.catalogo_establecimientos.update_one({"_id": u["id"]}, {"$push": {"catalogo": nuevo}})
        else:
            db.catalogo_establecimientos.insert_one({"_id": u["id"], "nombre": u["nombre"], "tipo": u.get("tipo","restaurante"), "catalogo": [nuevo]})
        get_redis().delete(f"catalogo:establecimiento:{u['id']}")
        st.success(f"✅ **{nombre}** agregado al catálogo. ID: `{nuevo['id_producto']}`")


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — ACTUALIZAR PRODUCTO
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_actualizar_producto():
    from connections import get_mongo, get_redis

    st.title("✏️ Actualizar producto")
    u = st.session_state.usuario
    db = get_mongo()
    doc = db.catalogo_establecimientos.find_one({"_id": u["id"]})

    if not doc or not doc.get("catalogo"):
        st.info("Todavía no tenés productos. Andá a 'Agregar producto'."); return

    opciones = {f"{p['nombre']} — ${p['precio']:,.0f} ({p['id_producto']})": p for p in doc["catalogo"]}
    seleccion = st.selectbox("Seleccioná el producto a editar", list(opciones.keys()))
    prod = opciones[seleccion]

    with st.form("editar_producto"):
        c1, c2 = st.columns(2)
        nombre      = c1.text_input("Nombre *", value=prod["nombre"])
        precio      = c2.number_input("Precio *", min_value=0.0, step=100.0, value=float(prod["precio"]))
        c3, c4 = st.columns(2)
        categoria   = c3.text_input("Categoría *", value=prod.get("categoria", ""))
        descripcion = c4.text_input("Descripción", value=prod.get("descripcion", ""))
        disponible  = st.checkbox("Disponible", value=prod.get("disponible", True))
        submitted   = st.form_submit_button("Guardar cambios", type="primary")

    if submitted:
        if not nombre or not categoria:
            st.error("Nombre y categoría son obligatorios."); return
        db.catalogo_establecimientos.update_one(
            {"_id": u["id"], "catalogo.id_producto": prod["id_producto"]},
            {"$set": {
                "catalogo.$.nombre":      nombre,
                "catalogo.$.precio":      precio,
                "catalogo.$.categoria":   categoria,
                "catalogo.$.descripcion": descripcion,
                "catalogo.$.disponible":  disponible,
            }}
        )
        get_redis().delete(f"catalogo:establecimiento:{u['id']}")
        st.success(f"✅ **{nombre}** actualizado correctamente.")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — PEDIDOS RECIBIDOS
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_pedidos_recibidos():
    from connections import get_postgres, get_cassandra

    st.title("📋 Pedidos recibidos")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, c.nombre, c.apellido
        FROM pedido p JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_establecimiento = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    pedidos = cur.fetchall(); cur.close(); conn.close()

    if not pedidos:
        st.info("Todavía no recibiste pedidos."); return

    session = get_cassandra()
    for id_p, fecha, total, nombre, apellido in pedidos:
        estado = estado_ultimo(session, id_p) or "desconocido"
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.markdown(f'<div class="card-title">Pedido #{id_p}  —  {nombre} {apellido}</div>', unsafe_allow_html=True)
                st.caption(fecha.strftime("%d/%m/%Y %H:%M"))
            c2.metric("Total", f"${total:,.2f}")
            with c3:
                st.markdown(badge(estado), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — CAMBIAR ESTADO
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_cambiar_estado():
    from connections import get_postgres, get_cassandra, get_redis
    from datetime import datetime

    st.title("🔄 Cambiar estado de pedido")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, c.nombre, c.apellido
        FROM pedido p JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_establecimiento = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    pedidos = cur.fetchall(); cur.close(); conn.close()

    if not pedidos:
        st.info("No tenés pedidos para gestionar."); return

    session = get_cassandra()
    pedidos_estado = [(id_p, fecha, n, a, estado_ultimo(session, id_p) or "desconocido") for id_p, fecha, n, a in pedidos]
    opts = {f"#{p[0]} — {p[2]} {p[3]}  [{p[4].upper()}]": p for p in pedidos_estado}
    pedido_sel = opts[st.selectbox("Elegí un pedido", list(opts.keys()))]
    id_pedido_sel, _, _, _, estado_actual = pedido_sel

    st.markdown(f"Estado actual: {badge(estado_actual)}", unsafe_allow_html=True)
    st.markdown("---")
    nuevo_estado = st.selectbox("Nuevo estado", ["aceptado","preparando","listo_para_retirar","cancelado"],
                                format_func=lambda x: x.upper().replace("_"," "))
    observacion = st.text_input("Observación (opcional)")

    if st.button("Actualizar estado", type="primary"):
        session.execute("INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
                        (id_pedido_sel, datetime.utcnow(), nuevo_estado, observacion or None))
        get_redis().delete(f"estado:pedido:{id_pedido_sel}")
        st.success(f"✅ Pedido #{id_pedido_sel} → **{nuevo_estado.upper()}**"); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — CALIFICACIONES
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_calificaciones_establecimiento():
    from connections import get_mongo

    st.title("⭐ Mis calificaciones")
    u = st.session_state.usuario
    db = get_mongo()
    califs = list(db.calificaciones.find({"id_establecimiento": u["id"]}))

    if not califs:
        st.info("Todavía no recibiste calificaciones."); return

    puntajes = [c["calificacion_establecimiento"]["puntaje"] for c in califs]
    c1, c2 = st.columns(2)
    c1.metric("Total calificaciones", len(califs))
    c2.metric("Promedio", f"{sum(puntajes)/len(puntajes):.2f} / 5")
    st.markdown("---")

    for c in califs:
        ce = c["calificacion_establecimiento"]
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{c['_id']}**")
                if ce.get("comentario"): st.write(f'"{ce["comentario"]}"')
                if ce.get("respuesta_establecimiento"): st.success(f"Tu respuesta: {ce['respuesta_establecimiento']}")
            with col2:
                st.markdown(f"{'⭐' * ce['puntaje']}")


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — RESPONDER RESEÑAS
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_responder_resenias():
    from connections import get_mongo

    st.title("💬 Responder reseñas")
    u = st.session_state.usuario
    db = get_mongo()
    califs = list(db.calificaciones.find({"id_establecimiento": u["id"], "calificacion_establecimiento.respuesta_establecimiento": None}))

    if not califs:
        st.success("No hay reseñas pendientes 🎉"); return

    for c in califs:
        ce = c["calificacion_establecimiento"]
        with st.container(border=True):
            st.markdown(f"**{c['_id']}**  {'⭐' * ce['puntaje']}")
            if ce.get("comentario"): st.write(f'"{ce["comentario"]}"')
            resp = st.text_input("Tu respuesta", key=f"resp_{c['_id']}")
            if st.button("Enviar", key=f"btn_{c['_id']}"):
                if resp.strip():
                    db.calificaciones.update_one({"_id": c["_id"]}, {"$set": {"calificacion_establecimiento.respuesta_establecimiento": resp.strip()}})
                    st.success("Respuesta guardada en MongoDB"); st.rerun()
                else:
                    st.warning("La respuesta no puede estar vacía.")


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO — CREAR PROMOCIÓN
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_crear_promocion():
    from connections import get_postgres, get_redis
    from datetime import datetime, timedelta
    import json

    st.title("🏷️ Crear promoción")
    u = st.session_state.usuario

    with st.form("nueva_promo"):
        c1, c2 = st.columns(2)
        codigo      = c1.text_input("Código *", placeholder="VERANO20").upper().strip()
        descripcion = c2.text_input("Descripción *")
        c3, c4, c5 = st.columns(3)
        descuento   = c3.number_input("Descuento (%)", 1.0, 100.0, 20.0, step=5.0)
        monto_min   = c4.number_input("Monto mínimo ($)", 0.0, step=100.0)
        dias        = c5.number_input("Duración (días)", 1, 365, 30)
        condiciones = st.text_area("Condiciones (opcional)", height=80)
        submitted   = st.form_submit_button("Crear promoción", type="primary")

    if submitted:
        if not codigo or not descripcion:
            st.error("Código y descripción son obligatorios."); return
        hoy = datetime.now().date()
        fecha_fin = hoy + timedelta(days=int(dias))
        conn = get_postgres(); cur = conn.cursor()
        cur.execute("SELECT id_promocion FROM promocion WHERE codigo=%s", (codigo,))
        if cur.fetchone():
            st.error(f"Ya existe una promoción con el código **{codigo}**."); cur.close(); conn.close(); return
        cur.execute("INSERT INTO promocion (codigo,descripcion,descuento,fecha_inicio,fecha_fin,monto_minimo,condiciones,creada_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_promocion",
                    (codigo, descripcion, descuento, hoy, fecha_fin, monto_min, condiciones or None, u["nombre"]))
        id_promo = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
        r = get_redis()
        r.set(f"promo:{codigo}", json.dumps({"id_promocion": id_promo, "codigo": codigo, "descripcion": descripcion,
                                              "descuento": descuento, "fecha_inicio": str(hoy), "fecha_fin": str(fecha_fin),
                                              "monto_minimo": monto_min}), ex=int(dias) * 86400)
        st.success(f"✅ Promoción **{codigo}** creada (hasta {fecha_fin}) y cacheada en Redis.")


# ══════════════════════════════════════════════════════════════════════════════
# REPARTIDOR — DISPONIBILIDAD
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_disponibilidad():
    from connections import get_postgres, get_redis

    st.title("🟢 Mi disponibilidad")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("SELECT disponibilidad FROM repartidor WHERE id_repartidor=%s", (u["id"],))
    row = cur.fetchone(); cur.close(); conn.close()
    disponible = row[0] if row else False
    r = get_redis()

    st.markdown(f"Estado actual: {'🟢 **DISPONIBLE**' if disponible else '🔴 **OCUPADO / NO DISPONIBLE**'}")
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🟢 Marcarme disponible", type="primary", disabled=disponible):
            conn = get_postgres(); cur = conn.cursor()
            cur.execute("UPDATE repartidor SET disponibilidad=true WHERE id_repartidor=%s", (u["id"],))
            conn.commit(); cur.close(); conn.close()
            r.smove("repartidores:ocupados", "repartidores:disponibles", str(u["id"]))
            r.sadd("repartidores:disponibles", str(u["id"]))
            st.success("Ahora estás disponible."); st.rerun()
    with c2:
        if st.button("🔴 Marcarme no disponible", disabled=not disponible):
            conn = get_postgres(); cur = conn.cursor()
            cur.execute("UPDATE repartidor SET disponibilidad=false WHERE id_repartidor=%s", (u["id"],))
            conn.commit(); cur.close(); conn.close()
            r.smove("repartidores:disponibles", "repartidores:ocupados", str(u["id"]))
            r.sadd("repartidores:ocupados", str(u["id"]))
            st.success("Marcado como no disponible."); st.rerun()

    st.markdown("---")
    ca, cb = st.columns(2)
    ca.metric("Disponibles (Redis)", len(r.smembers("repartidores:disponibles")))
    cb.metric("Ocupados (Redis)", len(r.smembers("repartidores:ocupados")))


# ══════════════════════════════════════════════════════════════════════════════
# REPARTIDOR — PEDIDOS DISPONIBLES
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_pedidos_asignados():
    from connections import get_postgres, get_cassandra, get_redis
    from datetime import datetime

    st.title("📦 Mis pedidos y disponibles")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre, c.nombre, c.apellido,
               d.calle, d.numero, d.ciudad
        FROM pedido p
        JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        JOIN cliente c ON p.id_cliente = c.id_cliente
        LEFT JOIN direccion d ON d.id_cliente = p.id_cliente AND d.nro_direccion = p.id_cliente_dir
        WHERE p.id_repartidor = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    mios = cur.fetchall()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre
        FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        WHERE p.id_repartidor IS NULL ORDER BY p.fecha_hora DESC
    """)
    sin_rep = cur.fetchall(); cur.close(); conn.close()

    session = get_cassandra()
    disponibles = [(id_p, fecha, total, est) for id_p, fecha, total, est in sin_rep
                   if estado_ultimo(session, id_p) == "listo_para_retirar"]

    st.subheader("Mis pedidos asignados")
    if mios:
        for id_p, fecha, total, est, cn, ca, calle, num, ciudad in mios:
            estado = estado_ultimo(session, id_p) or "?"
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.markdown(f'<div class="card-title">Pedido #{id_p}  —  {est}</div>', unsafe_allow_html=True)
                    st.caption(f"Cliente: {cn} {ca}")
                    if calle: st.caption(f"📍 {calle} {num or ''}, {ciudad}")
                c2.metric("Total", f"${total:,.2f}")
                with c3: st.markdown(badge(estado), unsafe_allow_html=True)
    else:
        st.info("No tenés pedidos asignados.")

    st.markdown("---")
    st.subheader(f"Pedidos listos para retirar ({len(disponibles)})")
    if disponibles:
        r = get_redis()
        for id_p, fecha, total, est in disponibles:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.markdown(f'<div class="card-title">Pedido #{id_p}  —  {est}</div>', unsafe_allow_html=True)
                    st.caption(fecha.strftime("%d/%m/%Y %H:%M"))
                c2.metric("Total", f"${total:,.2f}")
                with c3:
                    if st.button(f"🛵 Tomar pedido", key=f"tomar_{id_p}"):
                        lock = f"lock:repartidor:asignacion:{id_p}"
                        if not r.set(lock, u["id"], nx=True, ex=5):
                            st.error("Otro repartidor ya lo está tomando."); return
                        try:
                            conn = get_postgres(); cur = conn.cursor()
                            cur.execute("SELECT id_repartidor FROM pedido WHERE id_pedido=%s", (id_p,))
                            actual = cur.fetchone()
                            if actual and actual[0] is not None:
                                st.error("Ya fue tomado por otro repartidor.")
                            else:
                                cur.execute("UPDATE pedido SET id_repartidor=%s WHERE id_pedido=%s", (u["id"], id_p))
                                conn.commit()
                                session.execute("INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
                                                (id_p, datetime.utcnow(), "repartidor_asignado", f"Tomado por {u['nombre']}"))
                                r.smove("repartidores:disponibles", "repartidores:ocupados", str(u["id"]))
                                st.success(f"✅ Pedido #{id_p} asignado a vos.")
                            cur.close(); conn.close()
                        finally:
                            r.delete(lock)
                        st.rerun()
    else:
        st.info("No hay pedidos disponibles para tomar.")


# ══════════════════════════════════════════════════════════════════════════════
# REPARTIDOR — ACTUALIZAR ENTREGA
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_actualizar_entrega():
    from connections import get_postgres, get_cassandra, get_neo4j, get_redis
    from datetime import datetime

    st.title("🚀 Actualizar entrega")
    u = st.session_state.usuario
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.fecha_hora, e.nombre, c.nombre, c.apellido
        FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
        JOIN cliente c ON p.id_cliente = c.id_cliente
        WHERE p.id_repartidor = %s ORDER BY p.fecha_hora DESC
    """, (u["id"],))
    pedidos = cur.fetchall(); cur.close(); conn.close()

    if not pedidos:
        st.info("No tenés pedidos asignados."); return

    session = get_cassandra()
    pedidos_estado = [(id_p, fecha, est, cn, ca, estado_ultimo(session, id_p) or "?") for id_p, fecha, est, cn, ca in pedidos]
    opts = {f"#{p[0]} — {p[2]}  [{p[5].upper()}]": p for p in pedidos_estado}
    pedido_sel = opts[st.selectbox("Elegí un pedido", list(opts.keys()))]
    id_pedido_sel, _, _, _, _, estado_actual = pedido_sel

    st.markdown(f"Estado actual: {badge(estado_actual)}", unsafe_allow_html=True)
    nuevo_estado = st.selectbox("Nuevo estado", ["en_camino", "entregado"], format_func=lambda x: x.upper().replace("_"," "))
    observacion = st.text_input("Observación (opcional)")

    if st.button("Actualizar estado", type="primary"):
        session.execute("INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
                        (id_pedido_sel, datetime.utcnow(), nuevo_estado, observacion or None))
        if nuevo_estado == "entregado":
            try:
                driver = get_neo4j()
                with driver.session() as ses:
                    ses.run("MERGE (r:Repartidor {id:$id}) SET r.nombre=$n", id=u["id"], n=u["nombre"])
                    ses.run("MATCH (r:Repartidor {id:$r}),(p:Pedido {id:$p}) MERGE (r)-[:ENTREGO]->(p)", r=u["id"], p=id_pedido_sel)
                driver.close()
                r = get_redis()
                r.smove("repartidores:ocupados", "repartidores:disponibles", str(u["id"]))
                st.info("Neo4j: relación ENTREGO creada. Repartidor disponible nuevamente.")
            except Exception as e:
                st.warning(f"Neo4j: {e}")
        st.success(f"✅ Pedido #{id_pedido_sel} → **{nuevo_estado.upper()}**"); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# REPARTIDOR — MIS CALIFICACIONES
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_calificaciones_repartidor():
    from connections import get_mongo

    st.title("⭐ Mis calificaciones")
    u = st.session_state.usuario
    db = get_mongo()
    califs = list(db.calificaciones.find({"id_repartidor": u["id"], "calificacion_repartidor": {"$exists": True}}))

    if not califs:
        st.info("Todavía no tenés calificaciones."); return

    puntajes = [c["calificacion_repartidor"]["puntaje"] for c in califs]
    ca, cb = st.columns(2)
    ca.metric("Total calificaciones", len(califs))
    cb.metric("Promedio", f"{sum(puntajes)/len(puntajes):.2f} / 5")
    st.markdown("---")
    for c in califs:
        cr = c["calificacion_repartidor"]
        with st.container(border=True):
            st.markdown(f"**{c['_id']}**  {'⭐' * cr['puntaje']}")
            if cr.get("comentario"): st.write(f'"{cr["comentario"]}"')


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_verificar_conexiones():
    from connections import get_postgres, get_mongo, get_cassandra, get_neo4j, get_redis

    st.title("🔌 Verificar conexiones")
    if st.button("🔄 Verificar ahora", type="primary"):
        resultados = {}
        with st.spinner("Verificando PostgreSQL..."):
            try:
                conn = get_postgres(); cur = conn.cursor()
                cur.execute("SELECT version()"); v = cur.fetchone()[0][:50]
                cur.close(); conn.close(); resultados["PostgreSQL"] = ("✅", v)
            except Exception as e: resultados["PostgreSQL"] = ("❌", str(e)[:80])

        with st.spinner("Verificando MongoDB..."):
            try:
                get_mongo().command("ping"); resultados["MongoDB"] = ("✅", "ping OK")
            except Exception as e: resultados["MongoDB"] = ("❌", str(e)[:80])

        with st.spinner("Verificando Cassandra..."):
            try:
                get_cassandra().execute("SELECT release_version FROM system.local")
                resultados["Cassandra"] = ("✅", "REST API OK")
            except Exception as e: resultados["Cassandra"] = ("❌", str(e)[:80])

        with st.spinner("Verificando Neo4j..."):
            try:
                driver = get_neo4j(); driver.verify_connectivity(); driver.close()
                resultados["Neo4j"] = ("✅", "connectivity OK")
            except Exception as e: resultados["Neo4j"] = ("❌", str(e)[:80])

        with st.spinner("Verificando Redis..."):
            try:
                get_redis().ping(); resultados["Redis"] = ("✅", "pong")
            except Exception as e: resultados["Redis"] = ("❌", str(e)[:80])

        st.markdown("---")
        for db_name, (icon, msg) in resultados.items():
            color = "#2E7D32" if icon == "✅" else "#B71C1C"
            st.markdown(f'<span style="font-family:Hanken Grotesk,sans-serif;font-weight:700;color:{color}">{icon} {db_name}</span> — {msg}', unsafe_allow_html=True)


def pantalla_cargar_datos():
    st.title("🌱 Cargar datos de prueba")
    st.warning("⚠️ Esto inserta clientes, establecimientos, repartidores, pedidos y calificaciones. Limpiá las bases primero si ya tenés datos.")
    with st.expander("¿Qué se carga?"):
        st.markdown("""
- 3 clientes: `manu@test.com`, `fiona@test.com`, `lucho@test.com` (pwd: `test123`)
- 3 establecimientos: `sushi@test.com`, `bk@test.com`, `farmacia@test.com` (pwd: `test123`)
- 3 repartidores: `juan@test.com`, `maria@test.com`, `carlos@test.com` (pwd: `test123`)
- 12 pedidos en distintos estados
- Calificaciones en pedidos entregados
- Promos: **VERANO20** (20% off, mínimo $1000) · **ENVIOGRATIS** (100% off, mínimo $500)
""")
    if st.button("🌱 Cargar datos de prueba", type="primary"):
        import io, sys
        buf = io.StringIO(); sys.stdout = buf
        try:
            with st.spinner("Cargando en las 5 bases..."):
                _cargar_datos_directo()
        except Exception as e:
            sys.stdout = sys.__stdout__; st.error(f"Error: {e}"); return
        finally:
            sys.stdout = sys.__stdout__
        out = buf.getvalue()
        if out:
            with st.expander("Log"): st.code(out)
        st.success("✅ Datos de prueba cargados correctamente.")


def _cargar_datos_directo():
    import bcrypt, uuid
    from datetime import datetime, timedelta
    from connections import get_postgres, get_mongo, get_cassandra, get_neo4j, get_redis

    def hp(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    conn = get_postgres(); cur = conn.cursor()

    clientes_data = [
        ("Manuel","Oliver","manu@test.com","1162822101",hp("test123")),
        ("Fiona","Garcia","fiona@test.com","1145678901",hp("test123")),
        ("Lucho","Perez","lucho@test.com","1198765432",hp("test123")),
    ]
    ids_clientes = []
    for c in clientes_data:
        cur.execute("INSERT INTO cliente (nombre,apellido,email,telefono,password) VALUES (%s,%s,%s,%s,%s) RETURNING id_cliente", c)
        ids_clientes.append(cur.fetchone()[0])

    dirs = [
        (ids_clientes[0],1,"Cotagaita","1690","Ramos Mejia","1704","Casa"),
        (ids_clientes[0],2,"Av. Corrientes","1234","CABA","1043","Trabajo"),
        (ids_clientes[1],1,"Belgrano","5678","CABA","1067","Casa"),
        (ids_clientes[2],1,"Mitre","234","La Plata","1900","Casa"),
        (ids_clientes[2],2,"9 de Julio","789","CABA","1058","Oficina"),
    ]
    for d in dirs:
        cur.execute("INSERT INTO direccion (id_cliente,nro_direccion,calle,numero,ciudad,cp,alias) VALUES (%s,%s,%s,%s,%s,%s,%s)", d)

    estabs = [
        ("Sushi Club","Lima 123","1123435678","Lun-Vie 13-23","restaurante","sushi@test.com",hp("test123"),"Japonesa"),
        ("Burger King","Av. Cabildo 4000","1144556677","Todos los dias 11-23","restaurante","bk@test.com",hp("test123"),"Hamburguesas"),
        ("Farmacia Doc","Santa Fe 2500","1155667788","24hs","tienda","farmacia@test.com",hp("test123"),"Farmacia"),
    ]
    ids_estab, nombres_estab, tipos_estab = [], [], []
    for nombre,dir_,tel,hor,tipo,email,pwd,extra in estabs:
        cur.execute("INSERT INTO establecimiento (nombre,direccion,telefono,horario,tipo,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_establecimiento",
                    (nombre,dir_,tel,hor,tipo,email,pwd))
        id_e = cur.fetchone()[0]; ids_estab.append(id_e); nombres_estab.append(nombre); tipos_estab.append(tipo)
        if tipo == "restaurante":
            cur.execute("INSERT INTO restaurante (id_establecimiento,especialidad_culinaria) VALUES (%s,%s)", (id_e,extra))
        else:
            cur.execute("INSERT INTO tienda (id_establecimiento,rubro) VALUES (%s,%s)", (id_e,extra))

    reps = [
        ("Juan","Lopez","moto",True,"1166778899","juan@test.com",hp("test123")),
        ("Maria","Gomez","bici",True,"1177889900","maria@test.com",hp("test123")),
        ("Carlos","Diaz","auto",True,"1188990011","carlos@test.com",hp("test123")),
    ]
    ids_rep, nombres_rep = [], []
    for rd in reps:
        cur.execute("INSERT INTO repartidor (nombre,apellido,vehiculo,disponibilidad,telefono,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_repartidor", rd)
        ids_rep.append(cur.fetchone()[0]); nombres_rep.append(rd[0])

    hoy = datetime.now().date()
    for p_data in [
        ("VERANO20","20% off en restaurantes",20.0,hoy-timedelta(10),hoy+timedelta(30),1000.0,"Solo restaurantes","admin"),
        ("ENVIOGRATIS","Envio gratis",100.0,hoy-timedelta(5),hoy+timedelta(60),500.0,"Cualquier categoria","admin"),
    ]:
        cur.execute("INSERT INTO promocion (codigo,descripcion,descuento,fecha_inicio,fecha_fin,monto_minimo,condiciones,creada_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", p_data)
    conn.commit()

    db = get_mongo()
    p_sushi = [
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Roll California","precio":4500,"categoria":"rolls","descripcion":"Palta, kanikama, queso","disponible":True,"atributos":{"piezas":8,"picante":"no","sin_tacc":"si"}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Roll Salmon","precio":5200,"categoria":"rolls","descripcion":"Salmon, palta, queso","disponible":True,"atributos":{"piezas":8,"picante":"no","sin_tacc":"si"}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Gyoza","precio":3200,"categoria":"entrada","descripcion":"Empanaditas japonesas","disponible":True,"atributos":{"porciones":6,"vegetariano":"no"}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Coca Cola","precio":1800,"categoria":"bebida","descripcion":"Botella 500ml","disponible":True,"atributos":{"ml":500,"alcohol":"no"}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Mochi de chocolate","precio":2500,"categoria":"postre","descripcion":"3 unidades","disponible":True,"atributos":{"porciones":3,"sin_azucar":"no"}},
    ]
    p_bk = [
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Whopper","precio":6500,"categoria":"principal","descripcion":"Hamburguesa clasica","disponible":True,"atributos":{"porciones":1}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Doble Whopper","precio":8500,"categoria":"principal","descripcion":"Doble carne","disponible":True,"atributos":{"porciones":1}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Papas medianas","precio":2800,"categoria":"entrada","descripcion":"Papas fritas","disponible":True,"atributos":{"porciones":1}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Pepsi","precio":1500,"categoria":"bebida","descripcion":"Lata 354ml","disponible":True,"atributos":{"ml":354,"alcohol":"no"}},
    ]
    p_farma = [
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Ibuprofeno 400mg","precio":2200,"categoria":"medicamento","descripcion":"10 comprimidos","disponible":True,"atributos":{"marca":"Actron"}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Alcohol en gel","precio":1500,"categoria":"higiene","descripcion":"250ml","disponible":True,"atributos":{"marca":"Algabo","contenido":"250ml"}},
        {"id_producto":f"prod_{uuid.uuid4().hex[:8]}","nombre":"Vitamina C","precio":3500,"categoria":"suplemento","descripcion":"30 comprimidos","disponible":True,"atributos":{"marca":"Bayer"}},
    ]
    db.catalogo_establecimientos.insert_many([
        {"_id":ids_estab[0],"nombre":nombres_estab[0],"tipo":tipos_estab[0],"catalogo":p_sushi},
        {"_id":ids_estab[1],"nombre":nombres_estab[1],"tipo":tipos_estab[1],"catalogo":p_bk},
        {"_id":ids_estab[2],"nombre":nombres_estab[2],"tipo":tipos_estab[2],"catalogo":p_farma},
    ])

    session = get_cassandra(); driver = get_neo4j()
    catalogos = [p_sushi, p_bk, p_farma]
    pedidos_cfg = [
        (0,1,0,[(0,2),(3,1)],7,"entregado"),(1,1,1,[(0,1),(2,1),(3,2)],6,"entregado"),
        (0,1,1,[(1,1)],5,"entregado"),(2,1,0,[(0,1),(4,2)],5,"entregado"),
        (1,1,2,[(0,1),(1,1)],4,"entregado"),(0,2,0,[(1,2),(4,1)],3,"entregado"),
        (2,2,1,[(0,1),(3,1)],2,"en_camino"),(1,1,0,[(2,2)],1,"listo_para_retirar"),
        (0,1,2,[(0,1)],0,"preparando"),(2,1,1,[(0,1),(2,1)],0,"creado"),
        (1,1,1,[(1,1),(2,1),(3,1)],0,"entregado"),(0,1,0,[(0,1)],0,"creado"),
    ]
    estados_int = {
        "creado":["creado"],"preparando":["creado","aceptado","preparando"],
        "listo_para_retirar":["creado","aceptado","preparando","listo_para_retirar"],
        "en_camino":["creado","aceptado","preparando","listo_para_retirar","repartidor_asignado","en_camino"],
        "entregado":["creado","aceptado","preparando","listo_para_retirar","repartidor_asignado","en_camino","entregado"],
    }
    obs_map = {"creado":"Pedido creado","aceptado":"Pedido recibido","preparando":"En elaboracion",
               "listo_para_retirar":"Listo para retirar","en_camino":"Saliendo del local","entregado":"Pedido entregado"}

    for idx_p,(idx_cli,nro_dir,idx_est,prods,dias_atras,estado_final) in enumerate(pedidos_cfg):
        id_cli=ids_clientes[idx_cli]; id_est=ids_estab[idx_est]; catalogo=catalogos[idx_est]
        items=[]; total=0
        for idx_prod,cant in prods:
            p=catalogo[idx_prod]; sub=p["precio"]*cant; total+=sub
            items.append({"prod":p,"cant":cant,"subtotal":sub})
        fecha_p=datetime.now()-timedelta(days=dias_atras,hours=2)
        id_rep=ids_rep[idx_p%len(ids_rep)] if estado_final in ("en_camino","entregado") else None
        cur.execute("INSERT INTO pedido (fecha_hora,total,id_cliente,id_establecimiento,id_repartidor,id_cliente_dir) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id_pedido",
                    (fecha_p,total,id_cli,id_est,id_rep,nro_dir))
        id_pedido=cur.fetchone()[0]
        for item in items:
            cur.execute("INSERT INTO detalle_pedido (id_pedido,id_producto,cantidad,precio_unitario,subtotal) VALUES (%s,%s,%s,%s,%s)",
                        (id_pedido,item["prod"]["id_producto"],item["cant"],item["prod"]["precio"],item["subtotal"]))
        cur.execute("INSERT INTO pago (id_pedido,monto,fecha,metodo,estado) VALUES (%s,%s,%s,%s,%s)",
                    (id_pedido,total,fecha_p,"efectivo","completado" if estado_final=="entregado" else "pendiente"))
        timeline=estados_int[estado_final]; delta=30/max(len(timeline)-1,1)
        for i,estado in enumerate(timeline):
            f_est=fecha_p+timedelta(minutes=delta*i)
            obs=obs_map.get(estado)
            if estado=="repartidor_asignado" and id_rep:
                obs=f"Tomado por {nombres_rep[idx_p%len(ids_rep)]}"
            session.execute("INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)", (id_pedido,f_est,estado,obs))
        with driver.session() as ses:
            ses.run("MERGE (c:Cliente {id:$id}) SET c.nombre=$n", id=id_cli, n=clientes_data[idx_cli][0])
            ses.run("MERGE (e:Establecimiento {id:$id}) SET e.nombre=$n, e.tipo=$t", id=id_est, n=nombres_estab[idx_est], t=tipos_estab[idx_est])
            ses.run("MERGE (p:Pedido {id:$id}) SET p.fecha=$f, p.total=$t", id=id_pedido, f=str(fecha_p), t=total)
            ses.run("MATCH (c:Cliente {id:$c}),(p:Pedido {id:$p}) MERGE (c)-[:REALIZO]->(p)", c=id_cli, p=id_pedido)
            for item in items:
                ses.run("MERGE (pr:Producto {id:$id}) SET pr.nombre=$n, pr.precio=$pr, pr.categoria=$cat",
                        id=item["prod"]["id_producto"], n=item["prod"]["nombre"], pr=item["prod"]["precio"], cat=item["prod"]["categoria"])
                ses.run("MATCH (p:Pedido {id:$p}),(pr:Producto {id:$pr}) MERGE (p)-[r:CONTIENE]->(pr) SET r.cantidad=$c", p=id_pedido, pr=item["prod"]["id_producto"], c=item["cant"])
                ses.run("MATCH (pr:Producto {id:$pr}),(e:Establecimiento {id:$e}) MERGE (pr)-[:OFRECIDO_POR]->(e)", pr=item["prod"]["id_producto"], e=id_est)
            if id_rep and estado_final=="entregado":
                ses.run("MERGE (r:Repartidor {id:$id}) SET r.nombre=$n", id=id_rep, n=nombres_rep[idx_p%len(ids_rep)])
                ses.run("MATCH (r:Repartidor {id:$r}),(p:Pedido {id:$p}) MERGE (r)-[:ENTREGO]->(p)", r=id_rep, p=id_pedido)
        if estado_final=="entregado" and idx_p%2==0:
            pq_e=5 if idx_p%3==0 else 4; pq_r=5 if idx_p%4==0 else 4
            db.calificaciones.insert_one({
                "_id":f"pedido_{id_pedido}","id_cliente":id_cli,"id_establecimiento":id_est,"id_repartidor":id_rep,
                "fecha":fecha_p.isoformat(),
                "calificacion_establecimiento":{"puntaje":pq_e,"comentario":"Todo excelente" if pq_e==5 else "Estuvo bien","respuesta_establecimiento":"Gracias!" if pq_e==5 else None},
                "calificacion_repartidor":{"puntaje":pq_r,"comentario":"Rapido y amable" if pq_r==5 else "OK"},
            })
            with driver.session() as ses:
                ses.run("MATCH (c:Cliente {id:$c}),(e:Establecimiento {id:$e}) MERGE (c)-[r:CALIFICO]->(e) SET r.puntaje=$p", c=id_cli, e=id_est, p=pq_e)
                if id_rep:
                    ses.run("MATCH (c:Cliente {id:$c}),(r:Repartidor {id:$r}) MERGE (c)-[rel:CALIFICO]->(r) SET rel.puntaje=$p", c=id_cli, r=id_rep, p=pq_r)
    conn.commit(); cur.close(); conn.close(); driver.close()
    r_redis = get_redis()
    for id_r in ids_rep:
        r_redis.sadd("repartidores:disponibles", str(id_r))


def pantalla_limpiar_bases():
    from connections import get_postgres, get_mongo, get_cassandra, get_neo4j, get_redis
    import os

    st.title("🗑️ Limpiar todas las bases")
    st.error("⛔ Esta operación **borra TODOS los datos** de las 5 bases de datos.")
    confirmacion = st.text_input("Escribí **BORRAR TODO** para confirmar")

    if st.button("🗑️ Ejecutar limpieza", type="primary"):
        if confirmacion != "BORRAR TODO":
            st.warning("Escribí exactamente 'BORRAR TODO' para confirmar."); return
        resultados = {}
        with st.spinner("Limpiando PostgreSQL..."):
            try:
                schema_path = os.path.join(os.path.dirname(__file__), "schema", "postgres_init.sql")
                with open(schema_path) as f: sql = f.read()
                conn = get_postgres(); cur = conn.cursor()
                cur.execute(sql); conn.commit(); cur.close(); conn.close()
                resultados["PostgreSQL"] = "✅ Limpiado y recreado"
            except Exception as e: resultados["PostgreSQL"] = f"❌ {e}"

        with st.spinner("Limpiando MongoDB..."):
            try:
                db = get_mongo()
                for col in ["catalogo_establecimientos","calificaciones","historial_pedidos"]:
                    if col in db.list_collection_names(): db[col].drop()
                resultados["MongoDB"] = "✅ Colecciones eliminadas"
            except Exception as e: resultados["MongoDB"] = f"❌ {e}"

        with st.spinner("Limpiando Cassandra..."):
            try:
                get_cassandra().execute("TRUNCATE estado_pedido")
                resultados["Cassandra"] = "✅ Tabla truncada"
            except Exception as e: resultados["Cassandra"] = f"❌ {e}"

        with st.spinner("Limpiando Neo4j..."):
            try:
                driver = get_neo4j()
                with driver.session() as ses: ses.run("MATCH (n) DETACH DELETE n")
                driver.close(); resultados["Neo4j"] = "✅ Todos los nodos eliminados"
            except Exception as e: resultados["Neo4j"] = f"❌ {e}"

        with st.spinner("Limpiando Redis..."):
            try:
                get_redis().flushdb(); resultados["Redis"] = "✅ flushdb ejecutado"
            except Exception as e: resultados["Redis"] = f"❌ {e}"

        st.markdown("---")
        for db_name, msg in resultados.items():
            st.write(f"**{db_name}**: {msg}")


def _render_df(rows, columns):
    import pandas as pd
    if not rows: st.info("Sin datos."); return
    st.dataframe(pd.DataFrame(rows, columns=columns), use_container_width=True)


def pantalla_reporte_ciudad():
    from connections import get_postgres
    st.title("📊 Pedidos por ciudad")
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT d.ciudad, DATE(p.fecha_hora) as fecha, COUNT(*) as pedidos, SUM(p.total) as facturacion
        FROM pedido p JOIN direccion d ON d.id_cliente=p.id_cliente AND d.nro_direccion=p.id_cliente_dir
        GROUP BY d.ciudad, DATE(p.fecha_hora) ORDER BY fecha DESC, pedidos DESC
    """)
    rows = cur.fetchall(); cur.close(); conn.close()
    st.caption("Fuente: **PostgreSQL** (JOIN pedido + dirección)")
    _render_df(rows, ["Ciudad","Fecha","Pedidos","Facturación ($)"])


def pantalla_reporte_productos():
    from connections import get_neo4j
    st.title("🏆 Productos más pedidos")
    driver = get_neo4j()
    with driver.session() as ses:
        result = ses.run("""
            MATCH (p:Pedido)-[c:CONTIENE]->(pr:Producto)
            RETURN pr.nombre AS Producto, SUM(c.cantidad) AS Unidades, COUNT(DISTINCT p) AS Pedidos
            ORDER BY Unidades DESC LIMIT 10
        """)
        rows = [(r["Producto"], r["Unidades"], r["Pedidos"]) for r in result]
    driver.close()
    st.caption("Fuente: **Neo4j** (relaciones CONTIENE)")
    _render_df(rows, ["Producto","Unidades pedidas","Pedidos distintos"])


def pantalla_reporte_populares():
    from connections import get_neo4j
    st.title("🏅 Locales más populares")
    driver = get_neo4j()
    with driver.session() as ses:
        result = ses.run("""
            MATCH (p:Pedido)-[:CONTIENE]->(pr:Producto)-[:OFRECIDO_POR]->(e:Establecimiento)
            WITH e, COUNT(DISTINCT p) AS pedidos
            OPTIONAL MATCH (c:Cliente)-[r:CALIFICO]->(e)
            RETURN e.nombre AS Establecimiento, pedidos AS Pedidos, AVG(r.puntaje) AS Promedio
            ORDER BY pedidos DESC LIMIT 10
        """)
        rows = [(r["Establecimiento"], r["Pedidos"], f"{r['Promedio']:.2f}" if r["Promedio"] else "—") for r in result]
    driver.close()
    st.caption("Fuente: **Neo4j** (grafo) + calificaciones")
    _render_df(rows, ["Establecimiento","Pedidos","Calif. promedio"])


def pantalla_reporte_finde():
    from connections import get_postgres, get_mongo
    st.title("📅 Categorías en fines de semana")
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT dp.id_producto, SUM(dp.cantidad) as total FROM detalle_pedido dp
        JOIN pedido p ON dp.id_pedido=p.id_pedido
        WHERE EXTRACT(DOW FROM p.fecha_hora) IN (0,6) GROUP BY dp.id_producto
    """)
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows: st.info("No hay pedidos en fines de semana todavía."); return
    db = get_mongo(); cats = {}
    for id_prod, cant in rows:
        doc = db.catalogo_establecimientos.find_one({"catalogo.id_producto": id_prod}, {"catalogo.$": 1})
        cat = doc["catalogo"][0].get("categoria","?") if (doc and doc.get("catalogo")) else "?"
        cats[cat] = cats.get(cat, 0) + int(cant)
    st.caption("Fuente: **PostgreSQL** (filtra días) + **MongoDB** (categoría)")
    _render_df(sorted(cats.items(), key=lambda x: x[1], reverse=True), ["Categoría","Unidades pedidas"])


def pantalla_reporte_rapidos():
    from connections import get_postgres, get_cassandra
    from datetime import datetime as _dt
    st.title("⚡ Pedidos rápidos y caros (> $50 en < 30 min)")
    conn = get_postgres(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id_pedido, p.total, e.nombre, c.nombre, c.apellido
        FROM pedido p JOIN establecimiento e ON p.id_establecimiento=e.id_establecimiento
        JOIN cliente c ON p.id_cliente=c.id_cliente WHERE p.total > 50 ORDER BY p.total DESC
    """)
    candidatos = cur.fetchall(); cur.close(); conn.close()
    if not candidatos: st.info("No hay pedidos con total > $50."); return
    session = get_cassandra(); rapidos = []
    for id_p, total, est, cn, ca in candidatos:
        rows = list(session.execute("SELECT estado, fecha_hora FROM estado_pedido WHERE id_pedido=%s", (id_p,)))
        def _g(r, k): return r[k] if isinstance(r, dict) else getattr(r, k)
        def _ts(v): return _dt.fromisoformat(v) if isinstance(v, str) else v
        creado = next((_ts(_g(r,"fecha_hora")) for r in rows if _g(r,"estado")=="creado"), None)
        entregado = next((_ts(_g(r,"fecha_hora")) for r in rows if _g(r,"estado")=="entregado"), None)
        if creado and entregado:
            dur = (entregado - creado).total_seconds() / 60
            if dur < 30:
                rapidos.append((f"#{id_p}", est, f"{cn} {ca}", f"${total:,.0f}", f"{dur:.1f} min"))
    st.caption(f"Fuente: **PostgreSQL** + **Cassandra**. Candidatos evaluados: {len(candidatos)}")
    _render_df(rapidos, ["Pedido","Establecimiento","Cliente","Total","Duración"])


def pantalla_reporte_top_productos():
    from connections import get_neo4j, get_mongo
    st.title("💎 Top productos (>100 pedidos o establecimiento calif. >4.5)")
    driver = get_neo4j()
    with driver.session() as ses:
        result = ses.run("""
            MATCH (p:Pedido)-[c:CONTIENE]->(pr:Producto)-[:OFRECIDO_POR]->(e:Establecimiento)
            RETURN pr.id AS id_producto, pr.nombre AS nombre, e.id AS id_est, e.nombre AS est, SUM(c.cantidad) AS unidades
            ORDER BY unidades DESC
        """)
        productos = list(result)
    driver.close()
    db = get_mongo()
    pipeline = list(db.calificaciones.aggregate([{"$group":{"_id":"$id_establecimiento","promedio":{"$avg":"$calificacion_establecimiento.puntaje"}}}]))
    promedios = {c["_id"]: c["promedio"] for c in pipeline}
    seleccionados = []
    for p in productos:
        prom = promedios.get(p["id_est"], 0)
        if p["unidades"] > 100 or (prom and prom > 4.5):
            seleccionados.append((p["nombre"], p["est"], p["unidades"], f"{prom:.2f}" if prom else "—"))
    st.caption("Fuente: **Neo4j** + **MongoDB**")
    _render_df(seleccionados, ["Producto","Establecimiento","Unidades","Calif. prom. establecimiento"])
    if not seleccionados:
        st.info("Ningún producto cumple los criterios todavía (>100 pedidos del mismo producto o establecimiento con calif >4.5).")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
ROUTES = {
    "Catálogos":                  pantalla_catalogos,
    "Mi carrito":                 pantalla_carrito,
    "Confirmar pedido":           pantalla_confirmar,
    "Mis pedidos":                pantalla_mis_pedidos,
    "Calificar pedido":           pantalla_calificar,
    "Historial":                  pantalla_historial,
    "Mi catálogo":                pantalla_mi_catalogo,
    "Agregar producto":           pantalla_agregar_producto,
    "Actualizar producto":        pantalla_actualizar_producto,
    "Pedidos recibidos":          pantalla_pedidos_recibidos,
    "Cambiar estado":             pantalla_cambiar_estado,
    "Calificaciones":             pantalla_calificaciones_establecimiento,
    "Responder reseñas":          pantalla_responder_resenias,
    "Crear promoción":            pantalla_crear_promocion,
    "Disponibilidad":             pantalla_disponibilidad,
    "Pedidos disponibles":        pantalla_pedidos_asignados,
    "Actualizar entrega":         pantalla_actualizar_entrega,
    "Mis calificaciones":         pantalla_calificaciones_repartidor,
    "Verificar conexiones":       pantalla_verificar_conexiones,
    "Cargar datos de prueba":     pantalla_cargar_datos,
    "Limpiar bases":              pantalla_limpiar_bases,
    "Pedidos por ciudad":         pantalla_reporte_ciudad,
    "Productos más pedidos":      pantalla_reporte_productos,
    "Locales populares":          pantalla_reporte_populares,
    "Categorías fines de semana": pantalla_reporte_finde,
    "Pedidos rápidos y caros":    pantalla_reporte_rapidos,
    "Top productos":              pantalla_reporte_top_productos,
}


def main():
    if st.session_state.usuario is None:
        pantalla_login()
    else:
        seccion = render_sidebar()
        fn = ROUTES.get(seccion)
        if fn:
            fn()
        else:
            st.write(f"Sección desconocida: {seccion}")


if __name__ == "__main__":
    main()
