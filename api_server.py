"""
RAPPI TP — FastAPI Backend
Expone la logica de negocio como endpoints REST JSON.
"""
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from connections import get_postgres, get_mongo, get_redis, get_cassandra, get_neo4j

app = FastAPI(title="Rappi TP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── AUTH DEPENDENCY ────────────────────────────────────────────────────────────

def get_current_user(x_session_token: Optional[str] = Header(None)):
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Token requerido")
    parts = x_session_token.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Token invalido")
    rol, uid = parts[0], parts[1]
    r = get_redis()
    session_key = f"sesion:{rol}:{uid}"
    data = r.get(session_key)
    if not data:
        raise HTTPException(status_code=401, detail="Sesion expirada o invalida")
    user = json.loads(data)
    r.expire(session_key, 600)
    return user


def require_role(role: str):
    def dependency(user=Depends(get_current_user)):
        if user.get("rol") != role:
            raise HTTPException(status_code=403, detail=f"Se requiere rol: {role}")
        return user
    return dependency


# ── MODELS ────────────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    email: str
    password: str
    rol: str

class RegisterClienteBody(BaseModel):
    nombre: str
    apellido: str
    email: str
    telefono: Optional[str] = None
    password: str

class RegisterEstablecimientoBody(BaseModel):
    nombre: str
    direccion: Optional[str] = ""
    telefono: Optional[str] = None
    horario: Optional[str] = None
    tipo: str
    extra: Optional[str] = ""
    email: str
    password: str

class RegisterRepartidorBody(BaseModel):
    nombre: str
    apellido: str
    vehiculo: Optional[str] = "moto"
    telefono: Optional[str] = None
    email: str
    password: str

class AgregarCarritoBody(BaseModel):
    id_establecimiento: int
    nombre_establecimiento: str
    id_producto: str
    nombre: str
    precio: float
    cantidad: int

class AplicarPromoBody(BaseModel):
    codigo: str

class DireccionBody(BaseModel):
    calle: str
    numero: Optional[str] = None
    ciudad: str
    cp: Optional[str] = None
    alias: Optional[str] = None

class ConfirmarPedidoBody(BaseModel):
    nro_direccion: int
    metodo_pago: str

class CalificarBody(BaseModel):
    id_pedido: int
    puntaje_establecimiento: int
    comentario_est: Optional[str] = None
    puntaje_repartidor: Optional[int] = None
    comentario_rep: Optional[str] = None

class ProductoBody(BaseModel):
    nombre: str
    precio: float
    categoria: str
    descripcion: Optional[str] = ""
    atributos: Optional[dict] = {}

class DisponibilidadBody(BaseModel):
    disponible: bool

class EstadoBody(BaseModel):
    estado: str
    observacion: Optional[str] = None

class PromocionBody(BaseModel):
    codigo: str
    descripcion: str
    descuento: float
    monto_minimo: Optional[float] = 0.0
    dias: Optional[int] = 30
    condiciones: Optional[str] = None

class ResponderBody(BaseModel):
    respuesta: str


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/login")
def login(body: LoginBody):
    rol = body.rol
    r = get_redis()

    if rol == "admin":
        if body.email == "admin" and body.password == "admin1234":
            u = {"id": 0, "rol": "admin", "nombre": "Admin", "email": "admin"}
            r.set("sesion:admin:0", json.dumps(u), ex=600)
            return {"token": "admin:0", "user": u}
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    cfg = {
        "cliente":         ("cliente",        "id_cliente, nombre, apellido, email, password"),
        "establecimiento": ("establecimiento", "id_establecimiento, nombre, tipo, email, password"),
        "repartidor":      ("repartidor",      "id_repartidor, nombre, apellido, email, password"),
    }
    if rol not in cfg:
        raise HTTPException(status_code=400, detail="Rol invalido")

    tabla, campos = cfg[rol]
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT {campos} FROM {tabla} WHERE email = %s", (body.email.lower(),))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        raise HTTPException(status_code=401, detail=f"No existe ningun {rol} con ese email")
    if not bcrypt.checkpw(body.password.encode(), row[-1].encode()):
        raise HTTPException(status_code=401, detail="Password incorrecta")

    u = {"id": row[0], "rol": rol, "nombre": row[1], "email": row[-2]}
    if rol == "establecimiento":
        u["tipo"] = row[2]
    r.set(f"sesion:{rol}:{u['id']}", json.dumps(u), ex=600)
    return {"token": f"{rol}:{u['id']}", "user": u}


@app.post("/api/auth/logout")
def logout(user=Depends(get_current_user)):
    r = get_redis()
    r.delete(f"sesion:{user['rol']}:{user['id']}")
    return {"ok": True}


@app.post("/api/auth/register/cliente")
def register_cliente(body: RegisterClienteBody):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_cliente FROM cliente WHERE email=%s", (body.email.lower(),))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")
        pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO cliente (nombre,apellido,email,telefono,password) VALUES (%s,%s,%s,%s,%s) RETURNING id_cliente",
            (body.nombre, body.apellido, body.email.lower(), body.telefono, pwd_hash)
        )
        id_nuevo = cur.fetchone()[0]
        conn.commit()
        u = {"id": id_nuevo, "rol": "cliente", "nombre": body.nombre, "email": body.email.lower()}
        get_redis().set(f"sesion:cliente:{id_nuevo}", json.dumps(u), ex=600)
        return {"token": f"cliente:{id_nuevo}", "user": u}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/api/auth/register/establecimiento")
def register_establecimiento(body: RegisterEstablecimientoBody):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_establecimiento FROM establecimiento WHERE email=%s", (body.email.lower(),))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")
        pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO establecimiento (nombre,direccion,telefono,horario,tipo,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_establecimiento",
            (body.nombre, body.direccion or "", body.telefono, body.horario, body.tipo, body.email.lower(), pwd_hash)
        )
        id_nuevo = cur.fetchone()[0]
        extra = body.extra or ""
        if body.tipo == "restaurante":
            cur.execute("INSERT INTO restaurante (id_establecimiento,especialidad_culinaria) VALUES (%s,%s)", (id_nuevo, extra))
        else:
            cur.execute("INSERT INTO tienda (id_establecimiento,rubro) VALUES (%s,%s)", (id_nuevo, extra))
        conn.commit()
        u = {"id": id_nuevo, "rol": "establecimiento", "nombre": body.nombre, "email": body.email.lower(), "tipo": body.tipo}
        get_redis().set(f"sesion:establecimiento:{id_nuevo}", json.dumps(u), ex=600)
        return {"token": f"establecimiento:{id_nuevo}", "user": u}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/api/auth/register/repartidor")
def register_repartidor(body: RegisterRepartidorBody):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_repartidor FROM repartidor WHERE email=%s", (body.email.lower(),))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")
        pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO repartidor (nombre,apellido,vehiculo,disponibilidad,telefono,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_repartidor",
            (body.nombre, body.apellido, body.vehiculo or "moto", True, body.telefono, body.email.lower(), pwd_hash)
        )
        id_nuevo = cur.fetchone()[0]
        conn.commit()
        u = {"id": id_nuevo, "rol": "repartidor", "nombre": body.nombre, "email": body.email.lower()}
        get_redis().set(f"sesion:repartidor:{id_nuevo}", json.dumps(u), ex=600)
        return {"token": f"repartidor:{id_nuevo}", "user": u}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE
# ══════════════════════════════════════════════════════════════════════════════

def _cliente_user(user=Depends(get_current_user)):
    if user.get("rol") != "cliente":
        raise HTTPException(status_code=403, detail="Se requiere rol cliente")
    return user


@app.get("/api/cliente/establecimientos")
def get_establecimientos(user=Depends(_cliente_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_establecimiento, nombre, tipo, direccion FROM establecimiento ORDER BY nombre")
        rows = cur.fetchall()
        return [{"id": r[0], "nombre": r[1], "tipo": r[2], "direccion": r[3]} for r in rows]
    finally:
        cur.close()
        conn.close()


@app.get("/api/cliente/catalogo/{id_establecimiento}")
def get_catalogo(id_establecimiento: int, user=Depends(_cliente_user)):
    r = get_redis()
    cache_key = f"catalogo:establecimiento:{id_establecimiento}"
    cached = r.get(cache_key)
    if cached:
        doc = json.loads(cached)
        doc["_from_cache"] = True
        return doc
    db = get_mongo()
    doc = db.catalogo_establecimientos.find_one({"_id": id_establecimiento})
    if not doc:
        return {"catalogo": [], "_from_cache": False}
    doc["_id"] = str(doc["_id"])
    doc["_from_cache"] = False
    r.set(cache_key, json.dumps(doc), ex=300)
    return doc


@app.get("/api/cliente/carrito")
def get_carrito(user=Depends(_cliente_user)):
    r = get_redis()
    clave = f"carrito:cliente:{user['id']}"
    carrito = r.hgetall(clave)
    ttl = r.ttl(clave)
    items = []
    for k, v in carrito.items():
        if k.startswith("_"):
            continue
        items.append(json.loads(v))
    return {
        "items": items,
        "establecimiento_id": carrito.get("_establecimiento_id"),
        "establecimiento_nombre": carrito.get("_establecimiento_nombre"),
        "promo_codigo": carrito.get("_promo_codigo"),
        "promo_descuento": carrito.get("_promo_descuento"),
        "promo_descuento_monto": carrito.get("_promo_descuento_monto"),
        "ttl": ttl,
    }


@app.post("/api/cliente/carrito/agregar")
def agregar_carrito(body: AgregarCarritoBody, user=Depends(_cliente_user)):
    r = get_redis()
    clave = f"carrito:cliente:{user['id']}"
    est_actual = r.hget(clave, "_establecimiento_id")
    if est_actual and int(est_actual) != body.id_establecimiento:
        raise HTTPException(status_code=400, detail="El carrito ya tiene productos de otro establecimiento")
    r.hset(clave, "_establecimiento_id", body.id_establecimiento)
    r.hset(clave, "_establecimiento_nombre", body.nombre_establecimiento)
    existente = r.hget(clave, body.id_producto)
    if existente:
        item = json.loads(existente)
        item["cantidad"] += body.cantidad
    else:
        item = {
            "id_producto": body.id_producto,
            "nombre": body.nombre,
            "precio": body.precio,
            "cantidad": body.cantidad,
        }
    r.hset(clave, body.id_producto, json.dumps(item))
    r.expire(clave, 86400)
    return {"ok": True, "item": item}


@app.delete("/api/cliente/carrito")
def vaciar_carrito(user=Depends(_cliente_user)):
    r = get_redis()
    r.delete(f"carrito:cliente:{user['id']}")
    return {"ok": True}


@app.delete("/api/cliente/carrito/item/{id_producto}")
def quitar_item_carrito(id_producto: str, user=Depends(_cliente_user)):
    r = get_redis()
    clave = f"carrito:cliente:{user['id']}"
    r.hdel(clave, id_producto)
    keys = r.hkeys(clave)
    if not any(not k.startswith("_") for k in keys):
        r.delete(clave)
    return {"ok": True}


@app.post("/api/cliente/promocion/aplicar")
def aplicar_promo(body: AplicarPromoBody, user=Depends(_cliente_user)):
    codigo = body.codigo.upper().strip()
    r = get_redis()
    clave_carrito = f"carrito:cliente:{user['id']}"
    carrito = r.hgetall(clave_carrito)
    if not carrito:
        raise HTTPException(status_code=400, detail="El carrito esta vacio")

    total = sum(
        json.loads(v)["precio"] * json.loads(v)["cantidad"]
        for k, v in carrito.items() if not k.startswith("_")
    )

    cache = r.get(f"promo:{codigo}")
    if cache:
        promo = json.loads(cache)
    else:
        conn = get_postgres()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id_promocion, codigo, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo FROM promocion WHERE codigo = %s",
                (codigo,)
            )
            row = cur.fetchone()
        finally:
            cur.close()
            conn.close()
        if not row:
            raise HTTPException(status_code=404, detail=f"La promocion '{codigo}' no existe")
        promo = {
            "id_promocion": row[0], "codigo": row[1], "descripcion": row[2],
            "descuento": float(row[3]), "fecha_inicio": str(row[4]),
            "fecha_fin": str(row[5]), "monto_minimo": float(row[6])
        }

    hoy = datetime.now().date()
    fi = datetime.fromisoformat(promo["fecha_inicio"]).date()
    ff = datetime.fromisoformat(promo["fecha_fin"]).date()
    if hoy < fi or hoy > ff:
        raise HTTPException(status_code=400, detail="La promocion no esta vigente")
    if total < promo["monto_minimo"]:
        raise HTTPException(status_code=400, detail=f"Monto minimo requerido: ${promo['monto_minimo']:,.0f}")

    monto_desc = total * promo["descuento"] / 100
    r.hset(clave_carrito, "_promo_codigo", codigo)
    r.hset(clave_carrito, "_promo_id", str(promo["id_promocion"]))
    r.hset(clave_carrito, "_promo_descuento", str(promo["descuento"]))
    r.hset(clave_carrito, "_promo_descuento_monto", str(monto_desc))
    return {"ok": True, "descuento": promo["descuento"], "monto_descuento": monto_desc}


@app.get("/api/cliente/direcciones")
def get_direcciones(user=Depends(_cliente_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT nro_direccion, calle, numero, ciudad, cp, alias FROM direccion WHERE id_cliente=%s ORDER BY nro_direccion",
            (user["id"],)
        )
        rows = cur.fetchall()
        return [{"nro_direccion": r[0], "calle": r[1], "numero": r[2], "ciudad": r[3], "cp": r[4], "alias": r[5]} for r in rows]
    finally:
        cur.close()
        conn.close()


@app.post("/api/cliente/direcciones")
def agregar_direccion(body: DireccionBody, user=Depends(_cliente_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(MAX(nro_direccion),0)+1 FROM direccion WHERE id_cliente=%s", (user["id"],))
        nro = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO direccion (id_cliente,nro_direccion,calle,numero,ciudad,cp,alias) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (user["id"], nro, body.calle, body.numero, body.ciudad, body.cp, body.alias)
        )
        conn.commit()
        return {"ok": True, "nro_direccion": nro}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/api/cliente/pedido/confirmar")
def confirmar_pedido(body: ConfirmarPedidoBody, user=Depends(_cliente_user)):
    r = get_redis()
    clave_carrito = f"carrito:cliente:{user['id']}"
    carrito = r.hgetall(clave_carrito)
    if not carrito:
        raise HTTPException(status_code=400, detail="El carrito esta vacio")

    clave_lock = f"lock:checkout:cliente:{user['id']}"
    if not r.set(clave_lock, "1", nx=True, ex=10):
        raise HTTPException(status_code=429, detail="Ya estas procesando un pedido")

    try:
        id_est = int(carrito["_establecimiento_id"])
        nombre_est = carrito.get("_establecimiento_nombre", "")
        items = []
        total = 0
        for k, v in carrito.items():
            if k.startswith("_"):
                continue
            item = json.loads(v)
            items.append(item)
            total += item["precio"] * item["cantidad"]

        id_promo = carrito.get("_promo_id")
        descuento = float(carrito.get("_promo_descuento_monto", 0))
        total_final = total - descuento

        conn = get_postgres()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO pedido (total,id_cliente,id_establecimiento,id_cliente_dir) VALUES (%s,%s,%s,%s) RETURNING id_pedido, fecha_hora",
                (total_final, user["id"], id_est, body.nro_direccion)
            )
            id_pedido, fecha_hora = cur.fetchone()
            for item in items:
                subtotal = item["precio"] * item["cantidad"]
                cur.execute(
                    "INSERT INTO detalle_pedido (id_pedido,id_producto,cantidad,precio_unitario,subtotal) VALUES (%s,%s,%s,%s,%s)",
                    (id_pedido, item["id_producto"], item["cantidad"], item["precio"], subtotal)
                )
            cur.execute(
                "INSERT INTO pago (id_pedido,monto,metodo,estado) VALUES (%s,%s,%s,%s)",
                (id_pedido, total_final, body.metodo_pago, "pendiente")
            )
            if id_promo:
                cur.execute(
                    "INSERT INTO promocion_pedido (id_promocion,id_pedido,descuento_aplicado) VALUES (%s,%s,%s)",
                    (int(id_promo), id_pedido, descuento)
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"PostgreSQL: {e}")
        finally:
            cur.close()
            conn.close()

        try:
            session = get_cassandra()
            session.execute(
                "INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
                (id_pedido, fecha_hora, "creado", "Pedido creado por el cliente")
            )
        except Exception:
            pass

        try:
            driver = get_neo4j()
            with driver.session() as ses:
                ses.run("MERGE (c:Cliente {id:$id}) SET c.nombre=$n", id=user["id"], n=user["nombre"])
                ses.run("MERGE (e:Establecimiento {id:$id}) SET e.nombre=$n", id=id_est, n=nombre_est)
                ses.run("MERGE (p:Pedido {id:$id}) SET p.fecha=$f, p.total=$t", id=id_pedido, f=str(fecha_hora), t=total_final)
                ses.run("MATCH (c:Cliente {id:$c}),(p:Pedido {id:$p}) MERGE (c)-[:REALIZO]->(p)", c=user["id"], p=id_pedido)
                for item in items:
                    ses.run("MERGE (pr:Producto {id:$i}) SET pr.nombre=$n, pr.precio=$pr", i=item["id_producto"], n=item["nombre"], pr=item["precio"])
                    ses.run("MATCH (p:Pedido {id:$p}),(pr:Producto {id:$pr}) MERGE (p)-[r:CONTIENE]->(pr) SET r.cantidad=$c", p=id_pedido, pr=item["id_producto"], c=item["cantidad"])
                    ses.run("MATCH (pr:Producto {id:$pr}),(e:Establecimiento {id:$e}) MERGE (pr)-[:OFRECIDO_POR]->(e)", pr=item["id_producto"], e=id_est)
            driver.close()
        except Exception:
            pass

        r.delete(clave_carrito)
        return {"ok": True, "id_pedido": id_pedido, "total": total_final}
    finally:
        r.delete(clave_lock)


def _get_estado_ultimo(session_cass, id_pedido):
    rows = list(session_cass.execute(
        "SELECT estado FROM estado_pedido WHERE id_pedido = %s LIMIT 1", (id_pedido,)
    ))
    if not rows:
        return None
    r0 = rows[0]
    return r0["estado"] if isinstance(r0, dict) else r0.estado


@app.get("/api/cliente/pedidos")
def get_mis_pedidos(user=Depends(_cliente_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre, e.id_establecimiento
            FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
            WHERE p.id_cliente = %s ORDER BY p.fecha_hora DESC
        """, (user["id"],))
        pedidos = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    session = get_cassandra()
    result = []
    for id_p, fecha, total, est_nombre, id_est in pedidos:
        estado = _get_estado_ultimo(session, id_p)
        result.append({
            "id_pedido": id_p,
            "fecha_hora": fecha.isoformat(),
            "total": float(total),
            "establecimiento": est_nombre,
            "id_establecimiento": id_est,
            "estado": estado or "desconocido",
        })
    return result


@app.get("/api/cliente/pedido/{id_pedido}/estados")
def get_estados_pedido(id_pedido: int, user=Depends(_cliente_user)):
    session = get_cassandra()
    rows = list(session.execute("SELECT estado, fecha_hora, observacion FROM estado_pedido WHERE id_pedido = %s", (id_pedido,)))

    def _g(r, k):
        return r[k] if isinstance(r, dict) else getattr(r, k)

    def _ts(v):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    result = []
    for row in rows:
        fh = _ts(_g(row, "fecha_hora"))
        obs = None
        try:
            obs = _g(row, "observacion")
        except Exception:
            pass
        result.append({
            "estado": _g(row, "estado"),
            "fecha_hora": fh.isoformat() if fh else None,
            "observacion": obs,
        })
    result.sort(key=lambda x: x["fecha_hora"] or "")
    return result


@app.get("/api/cliente/pedidos/calificar")
def get_pedidos_calificar(user=Depends(_cliente_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id_pedido, p.fecha_hora, e.id_establecimiento, e.nombre,
                   r.id_repartidor, r.nombre, r.apellido
            FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
            LEFT JOIN repartidor r ON p.id_repartidor = r.id_repartidor
            WHERE p.id_cliente = %s ORDER BY p.fecha_hora DESC
        """, (user["id"],))
        pedidos = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    session = get_cassandra()
    db = get_mongo()
    result = []
    for id_p, fecha, id_est, est_nombre, id_rep, rep_n, rep_a in pedidos:
        estado = _get_estado_ultimo(session, id_p)
        if estado != "entregado":
            continue
        ya_calif = db.calificaciones.find_one({"_id": f"pedido_{id_p}"})
        if ya_calif:
            continue
        result.append({
            "id_pedido": id_p,
            "fecha_hora": fecha.isoformat(),
            "id_establecimiento": id_est,
            "establecimiento": est_nombre,
            "id_repartidor": id_rep,
            "repartidor": f"{rep_n} {rep_a or ''}".strip() if rep_n else None,
        })
    return result


@app.post("/api/cliente/pedido/calificar")
def calificar_pedido(body: CalificarBody, user=Depends(_cliente_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id_establecimiento, p.id_repartidor
            FROM pedido p WHERE p.id_pedido=%s AND p.id_cliente=%s
        """, (body.id_pedido, user["id"]))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    id_est, id_rep = row
    db = get_mongo()
    if db.calificaciones.find_one({"_id": f"pedido_{body.id_pedido}"}):
        raise HTTPException(status_code=409, detail="Ya calificaste este pedido")

    doc = {
        "_id": f"pedido_{body.id_pedido}",
        "id_cliente": user["id"],
        "id_establecimiento": id_est,
        "id_repartidor": id_rep,
        "fecha": datetime.utcnow().isoformat(),
        "calificacion_establecimiento": {
            "puntaje": body.puntaje_establecimiento,
            "comentario": body.comentario_est or None,
            "respuesta_establecimiento": None,
        }
    }
    if body.puntaje_repartidor is not None:
        doc["calificacion_repartidor"] = {
            "puntaje": body.puntaje_repartidor,
            "comentario": body.comentario_rep or None,
        }
    db.calificaciones.insert_one(doc)

    try:
        driver = get_neo4j()
        with driver.session() as ses:
            ses.run(
                "MATCH (c:Cliente {id:$c}),(e:Establecimiento {id:$e}) MERGE (c)-[r:CALIFICO]->(e) SET r.puntaje=$p",
                c=user["id"], e=id_est, p=body.puntaje_establecimiento
            )
            if id_rep and body.puntaje_repartidor:
                ses.run(
                    "MATCH (c:Cliente {id:$c}),(r:Repartidor {id:$r}) MERGE (c)-[rel:CALIFICO]->(r) SET rel.puntaje=$p",
                    c=user["id"], r=id_rep, p=body.puntaje_repartidor
                )
        driver.close()
    except Exception:
        pass

    return {"ok": True}


@app.get("/api/cliente/historial")
def get_historial(user=Depends(_cliente_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre
            FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
            WHERE p.id_cliente = %s ORDER BY p.fecha_hora DESC
        """, (user["id"],))
        pedidos = cur.fetchall()
        result = []
        db = get_mongo()
        for id_p, fecha, total, est_nombre in pedidos:
            cur.execute(
                "SELECT id_producto, cantidad, precio_unitario, subtotal FROM detalle_pedido WHERE id_pedido=%s",
                (id_p,)
            )
            detalles = cur.fetchall()
            items = []
            for id_prod, cant, precio, subtotal in detalles:
                doc = db.catalogo_establecimientos.find_one({"catalogo.id_producto": id_prod}, {"catalogo.$": 1})
                nombre_prod = doc["catalogo"][0]["nombre"] if (doc and doc.get("catalogo")) else str(id_prod)
                items.append({"id_producto": id_prod, "nombre": nombre_prod, "cantidad": cant, "precio_unitario": float(precio), "subtotal": float(subtotal)})
            result.append({
                "id_pedido": id_p,
                "fecha_hora": fecha.isoformat(),
                "total": float(total),
                "establecimiento": est_nombre,
                "items": items,
            })
        return result
    finally:
        cur.close()
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ESTABLECIMIENTO
# ══════════════════════════════════════════════════════════════════════════════

def _est_user(user=Depends(get_current_user)):
    if user.get("rol") != "establecimiento":
        raise HTTPException(status_code=403, detail="Se requiere rol establecimiento")
    return user


@app.get("/api/establecimiento/catalogo")
def get_catalogo_est(user=Depends(_est_user)):
    db = get_mongo()
    doc = db.catalogo_establecimientos.find_one({"_id": user["id"]})
    if not doc:
        return {"catalogo": []}
    doc["_id"] = str(doc["_id"])
    return doc


@app.post("/api/establecimiento/producto")
def agregar_producto(body: ProductoBody, user=Depends(_est_user)):
    id_prod = f"prod_{uuid.uuid4().hex[:8]}"
    nuevo = {
        "id_producto": id_prod,
        "nombre": body.nombre,
        "precio": body.precio,
        "categoria": body.categoria,
        "descripcion": body.descripcion or "",
        "disponible": True,
        "atributos": body.atributos or {},
    }
    db = get_mongo()
    existente = db.catalogo_establecimientos.find_one({"_id": user["id"]})
    if existente:
        db.catalogo_establecimientos.update_one({"_id": user["id"]}, {"$push": {"catalogo": nuevo}})
    else:
        db.catalogo_establecimientos.insert_one({
            "_id": user["id"],
            "nombre": user["nombre"],
            "tipo": user.get("tipo", "restaurante"),
            "catalogo": [nuevo],
        })
    get_redis().delete(f"catalogo:establecimiento:{user['id']}")
    return {"ok": True, "id_producto": id_prod}


@app.put("/api/establecimiento/producto/{id_producto}/disponibilidad")
def toggle_disponibilidad(id_producto: str, body: DisponibilidadBody, user=Depends(_est_user)):
    db = get_mongo()
    db.catalogo_establecimientos.update_one(
        {"_id": user["id"], "catalogo.id_producto": id_producto},
        {"$set": {"catalogo.$.disponible": body.disponible}}
    )
    get_redis().delete(f"catalogo:establecimiento:{user['id']}")
    return {"ok": True}


@app.get("/api/establecimiento/pedidos")
def get_pedidos_est(user=Depends(_est_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id_pedido, p.fecha_hora, p.total, c.nombre, c.apellido
            FROM pedido p JOIN cliente c ON p.id_cliente = c.id_cliente
            WHERE p.id_establecimiento = %s ORDER BY p.fecha_hora DESC
        """, (user["id"],))
        pedidos = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    session = get_cassandra()
    result = []
    for id_p, fecha, total, nombre, apellido in pedidos:
        estado = _get_estado_ultimo(session, id_p) or "desconocido"
        result.append({
            "id_pedido": id_p,
            "fecha_hora": fecha.isoformat(),
            "total": float(total),
            "cliente": f"{nombre} {apellido or ''}".strip(),
            "estado": estado,
        })
    return result


@app.put("/api/establecimiento/pedido/{id_pedido}/estado")
def cambiar_estado_pedido(id_pedido: int, body: EstadoBody, user=Depends(_est_user)):
    session = get_cassandra()
    session.execute(
        "INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
        (id_pedido, datetime.utcnow(), body.estado, body.observacion or None)
    )
    get_redis().delete(f"estado:pedido:{id_pedido}")
    return {"ok": True}


@app.get("/api/establecimiento/calificaciones")
def get_calificaciones_est(user=Depends(_est_user)):
    db = get_mongo()
    califs = list(db.calificaciones.find({"id_establecimiento": user["id"]}))
    result = []
    for c in califs:
        ce = c.get("calificacion_establecimiento", {})
        result.append({
            "id": str(c["_id"]),
            "id_cliente": c.get("id_cliente"),
            "fecha": c.get("fecha"),
            "puntaje": ce.get("puntaje"),
            "comentario": ce.get("comentario"),
            "respuesta": ce.get("respuesta_establecimiento"),
        })
    return result


@app.post("/api/establecimiento/calificacion/{id_calificacion}/responder")
def responder_calificacion(id_calificacion: str, body: ResponderBody, user=Depends(_est_user)):
    db = get_mongo()
    db.calificaciones.update_one(
        {"_id": id_calificacion},
        {"$set": {"calificacion_establecimiento.respuesta_establecimiento": body.respuesta.strip()}}
    )
    return {"ok": True}


@app.post("/api/establecimiento/promocion")
def crear_promocion(body: PromocionBody, user=Depends(_est_user)):
    hoy = datetime.now().date()
    fecha_fin = hoy + timedelta(days=int(body.dias or 30))
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_promocion FROM promocion WHERE codigo=%s", (body.codigo.upper(),))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Ya existe una promocion con el codigo {body.codigo}")
        cur.execute(
            "INSERT INTO promocion (codigo,descripcion,descuento,fecha_inicio,fecha_fin,monto_minimo,condiciones,creada_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_promocion",
            (body.codigo.upper(), body.descripcion, body.descuento, hoy, fecha_fin, body.monto_minimo or 0, body.condiciones, user["nombre"])
        )
        id_promo = cur.fetchone()[0]
        conn.commit()
        r = get_redis()
        r.set(f"promo:{body.codigo.upper()}", json.dumps({
            "id_promocion": id_promo, "codigo": body.codigo.upper(),
            "descripcion": body.descripcion, "descuento": body.descuento,
            "fecha_inicio": str(hoy), "fecha_fin": str(fecha_fin),
            "monto_minimo": body.monto_minimo or 0
        }), ex=int(body.dias or 30) * 86400)
        return {"ok": True, "id_promocion": id_promo}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# REPARTIDOR
# ══════════════════════════════════════════════════════════════════════════════

def _rep_user(user=Depends(get_current_user)):
    if user.get("rol") != "repartidor":
        raise HTTPException(status_code=403, detail="Se requiere rol repartidor")
    return user


@app.get("/api/repartidor/estado")
def get_estado_repartidor(user=Depends(_rep_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT disponibilidad FROM repartidor WHERE id_repartidor=%s", (user["id"],))
        row = cur.fetchone()
        disponible = row[0] if row else False
    finally:
        cur.close()
        conn.close()
    r = get_redis()
    disponibles = len(r.smembers("repartidores:disponibles"))
    ocupados = len(r.smembers("repartidores:ocupados"))
    return {"disponible": disponible, "disponibles_redis": disponibles, "ocupados_redis": ocupados}


@app.post("/api/repartidor/disponible")
def marcar_disponible(user=Depends(_rep_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE repartidor SET disponibilidad=true WHERE id_repartidor=%s", (user["id"],))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    r = get_redis()
    r.smove("repartidores:ocupados", "repartidores:disponibles", str(user["id"]))
    r.sadd("repartidores:disponibles", str(user["id"]))
    return {"ok": True}


@app.post("/api/repartidor/ocupado")
def marcar_ocupado(user=Depends(_rep_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE repartidor SET disponibilidad=false WHERE id_repartidor=%s", (user["id"],))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    r = get_redis()
    r.smove("repartidores:disponibles", "repartidores:ocupados", str(user["id"]))
    r.sadd("repartidores:ocupados", str(user["id"]))
    return {"ok": True}


@app.get("/api/repartidor/pedidos")
def get_pedidos_repartidor(user=Depends(_rep_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre,
                   c.nombre, c.apellido, d.calle, d.numero, d.ciudad
            FROM pedido p
            JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
            JOIN cliente c ON p.id_cliente = c.id_cliente
            LEFT JOIN direccion d ON d.id_cliente = p.id_cliente AND d.nro_direccion = p.id_cliente_dir
            WHERE p.id_repartidor = %s ORDER BY p.fecha_hora DESC
        """, (user["id"],))
        mios = cur.fetchall()
        cur.execute("""
            SELECT p.id_pedido, p.fecha_hora, p.total, e.nombre
            FROM pedido p JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
            WHERE p.id_repartidor IS NULL ORDER BY p.fecha_hora DESC
        """)
        sin_rep = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    session = get_cassandra()
    asignados = []
    for id_p, fecha, total, est, cn, ca, calle, num, ciudad in mios:
        estado = _get_estado_ultimo(session, id_p) or "?"
        asignados.append({
            "id_pedido": id_p, "fecha_hora": fecha.isoformat(), "total": float(total),
            "establecimiento": est, "cliente": f"{cn} {ca or ''}".strip(),
            "direccion": f"{calle or ''} {num or ''}, {ciudad or ''}".strip(", "),
            "estado": estado,
        })

    disponibles = []
    for id_p, fecha, total, est in sin_rep:
        estado = _get_estado_ultimo(session, id_p)
        if estado == "listo_para_retirar":
            disponibles.append({
                "id_pedido": id_p, "fecha_hora": fecha.isoformat(),
                "total": float(total), "establecimiento": est, "estado": estado,
            })

    return {"asignados": asignados, "disponibles": disponibles}


@app.post("/api/repartidor/pedido/{id_pedido}/tomar")
def tomar_pedido(id_pedido: int, user=Depends(_rep_user)):
    r = get_redis()
    lock = f"lock:repartidor:asignacion:{id_pedido}"
    if not r.set(lock, user["id"], nx=True, ex=5):
        raise HTTPException(status_code=409, detail="Otro repartidor ya lo esta tomando")
    try:
        conn = get_postgres()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id_repartidor FROM pedido WHERE id_pedido=%s", (id_pedido,))
            actual = cur.fetchone()
            if actual and actual[0] is not None:
                raise HTTPException(status_code=409, detail="Ya fue tomado por otro repartidor")
            cur.execute("UPDATE pedido SET id_repartidor=%s WHERE id_pedido=%s", (user["id"], id_pedido))
            conn.commit()
        finally:
            cur.close()
            conn.close()
        session = get_cassandra()
        session.execute(
            "INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
            (id_pedido, datetime.utcnow(), "repartidor_asignado", f"Tomado por {user['nombre']}")
        )
        r.smove("repartidores:disponibles", "repartidores:ocupados", str(user["id"]))
        return {"ok": True}
    finally:
        r.delete(lock)


@app.put("/api/repartidor/pedido/{id_pedido}/estado")
def actualizar_estado_entrega(id_pedido: int, body: EstadoBody, user=Depends(_rep_user)):
    session = get_cassandra()
    session.execute(
        "INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)",
        (id_pedido, datetime.utcnow(), body.estado, body.observacion or None)
    )
    if body.estado == "entregado":
        try:
            driver = get_neo4j()
            r = get_redis()
            with driver.session() as ses:
                ses.run("MERGE (r:Repartidor {id:$id}) SET r.nombre=$n", id=user["id"], n=user["nombre"])
                ses.run("MATCH (r:Repartidor {id:$r}),(p:Pedido {id:$p}) MERGE (r)-[:ENTREGO]->(p)", r=user["id"], p=id_pedido)
            driver.close()
            r.smove("repartidores:ocupados", "repartidores:disponibles", str(user["id"]))
        except Exception:
            pass
    return {"ok": True}


@app.get("/api/repartidor/calificaciones")
def get_calificaciones_rep(user=Depends(_rep_user)):
    db = get_mongo()
    califs = list(db.calificaciones.find({"id_repartidor": user["id"], "calificacion_repartidor": {"$exists": True}}))
    result = []
    for c in califs:
        cr = c.get("calificacion_repartidor", {})
        result.append({
            "id": str(c["_id"]),
            "fecha": c.get("fecha"),
            "puntaje": cr.get("puntaje"),
            "comentario": cr.get("comentario"),
        })
    return result


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════════════════════

def _admin_user(user=Depends(get_current_user)):
    if user.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Se requiere rol admin")
    return user


@app.get("/api/admin/conexiones")
def verificar_conexiones(user=Depends(_admin_user)):
    result = {}
    try:
        conn = get_postgres()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        cur.fetchone()
        cur.close()
        conn.close()
        result["postgresql"] = "ok"
    except Exception as e:
        result["postgresql"] = f"error: {str(e)[:80]}"

    try:
        get_mongo().command("ping")
        result["mongodb"] = "ok"
    except Exception as e:
        result["mongodb"] = f"error: {str(e)[:80]}"

    try:
        get_cassandra().execute("SELECT release_version FROM system.local")
        result["cassandra"] = "ok"
    except Exception as e:
        result["cassandra"] = f"error: {str(e)[:80]}"

    try:
        driver = get_neo4j()
        driver.verify_connectivity()
        driver.close()
        result["neo4j"] = "ok"
    except Exception as e:
        result["neo4j"] = f"error: {str(e)[:80]}"

    try:
        get_redis().ping()
        result["redis"] = "ok"
    except Exception as e:
        result["redis"] = f"error: {str(e)[:80]}"

    return result


@app.post("/api/admin/seed")
def cargar_seed(user=Depends(_admin_user)):
    try:
        _cargar_datos_directo()
        return {"ok": True, "mensaje": "Datos de prueba cargados correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/bases")
def limpiar_bases(user=Depends(_admin_user)):
    resultados = {}
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "schema", "postgres_init.sql")
        with open(schema_path) as f:
            sql = f.read()
        conn = get_postgres()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()
        resultados["postgresql"] = "ok"
    except Exception as e:
        resultados["postgresql"] = f"error: {str(e)[:80]}"

    try:
        db = get_mongo()
        for col in ["catalogo_establecimientos", "calificaciones", "historial_pedidos"]:
            if col in db.list_collection_names():
                db[col].drop()
        resultados["mongodb"] = "ok"
    except Exception as e:
        resultados["mongodb"] = f"error: {str(e)[:80]}"

    try:
        get_cassandra().execute("TRUNCATE estado_pedido")
        resultados["cassandra"] = "ok"
    except Exception as e:
        resultados["cassandra"] = f"error: {str(e)[:80]}"

    try:
        driver = get_neo4j()
        with driver.session() as ses:
            ses.run("MATCH (n) DETACH DELETE n")
        driver.close()
        resultados["neo4j"] = "ok"
    except Exception as e:
        resultados["neo4j"] = f"error: {str(e)[:80]}"

    try:
        get_redis().flushdb()
        resultados["redis"] = "ok"
    except Exception as e:
        resultados["redis"] = f"error: {str(e)[:80]}"

    return resultados


@app.get("/api/admin/reporte/ciudades")
def reporte_ciudades(user=Depends(_admin_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT d.ciudad, DATE(p.fecha_hora) as fecha, COUNT(*) as pedidos, SUM(p.total) as facturacion
            FROM pedido p JOIN direccion d ON d.id_cliente=p.id_cliente AND d.nro_direccion=p.id_cliente_dir
            GROUP BY d.ciudad, DATE(p.fecha_hora) ORDER BY fecha DESC, pedidos DESC
        """)
        rows = cur.fetchall()
        return [{"ciudad": r[0], "fecha": str(r[1]), "pedidos": r[2], "facturacion": float(r[3])} for r in rows]
    finally:
        cur.close()
        conn.close()


@app.get("/api/admin/reporte/productos")
def reporte_productos(user=Depends(_admin_user)):
    driver = get_neo4j()
    try:
        with driver.session() as ses:
            result = ses.run("""
                MATCH (p:Pedido)-[c:CONTIENE]->(pr:Producto)
                RETURN pr.nombre AS producto, SUM(c.cantidad) AS unidades, COUNT(DISTINCT p) AS pedidos
                ORDER BY unidades DESC LIMIT 10
            """)
            return [{"producto": r["producto"], "unidades": r["unidades"], "pedidos": r["pedidos"]} for r in result]
    finally:
        driver.close()


@app.get("/api/admin/reporte/restaurantes")
def reporte_restaurantes(user=Depends(_admin_user)):
    driver = get_neo4j()
    try:
        with driver.session() as ses:
            result = ses.run("""
                MATCH (p:Pedido)-[:CONTIENE]->(pr:Producto)-[:OFRECIDO_POR]->(e:Establecimiento)
                WITH e, COUNT(DISTINCT p) AS pedidos
                OPTIONAL MATCH (c:Cliente)-[r:CALIFICO]->(e)
                RETURN e.nombre AS establecimiento, pedidos, AVG(r.puntaje) AS promedio
                ORDER BY pedidos DESC LIMIT 10
            """)
            return [{"establecimiento": r["establecimiento"], "pedidos": r["pedidos"],
                     "calificacion": round(r["promedio"], 2) if r["promedio"] else None} for r in result]
    finally:
        driver.close()


@app.get("/api/admin/reporte/finde")
def reporte_finde(user=Depends(_admin_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT dp.id_producto, SUM(dp.cantidad) as total FROM detalle_pedido dp
            JOIN pedido p ON dp.id_pedido=p.id_pedido
            WHERE EXTRACT(DOW FROM p.fecha_hora) IN (0,6) GROUP BY dp.id_producto
        """)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    if not rows:
        return []
    db = get_mongo()
    cats = {}
    for id_prod, cant in rows:
        doc = db.catalogo_establecimientos.find_one({"catalogo.id_producto": id_prod}, {"catalogo.$": 1})
        cat = doc["catalogo"][0].get("categoria", "?") if (doc and doc.get("catalogo")) else "?"
        cats[cat] = cats.get(cat, 0) + int(cant)
    return sorted([{"categoria": k, "unidades": v} for k, v in cats.items()], key=lambda x: x["unidades"], reverse=True)


@app.get("/api/admin/reporte/rapidos")
def reporte_rapidos(user=Depends(_admin_user)):
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id_pedido, p.total, e.nombre, c.nombre, c.apellido
            FROM pedido p JOIN establecimiento e ON p.id_establecimiento=e.id_establecimiento
            JOIN cliente c ON p.id_cliente=c.id_cliente WHERE p.total > 50 ORDER BY p.total DESC
        """)
        candidatos = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    session = get_cassandra()
    rapidos = []
    for id_p, total, est, cn, ca in candidatos:
        rows = list(session.execute("SELECT estado, fecha_hora FROM estado_pedido WHERE id_pedido=%s", (id_p,)))

        def _g(r, k):
            return r[k] if isinstance(r, dict) else getattr(r, k)

        def _ts(v):
            return datetime.fromisoformat(v) if isinstance(v, str) else v

        creado = next((_ts(_g(r, "fecha_hora")) for r in rows if _g(r, "estado") == "creado"), None)
        entregado = next((_ts(_g(r, "fecha_hora")) for r in rows if _g(r, "estado") == "entregado"), None)
        if creado and entregado:
            dur = (entregado - creado).total_seconds() / 60
            if dur < 30:
                rapidos.append({
                    "id_pedido": f"#{id_p}", "establecimiento": est,
                    "cliente": f"{cn} {ca}", "total": float(total), "duracion_min": round(dur, 1)
                })
    return rapidos


@app.get("/api/admin/reporte/top-productos")
def reporte_top_productos(user=Depends(_admin_user)):
    driver = get_neo4j()
    try:
        with driver.session() as ses:
            result = ses.run("""
                MATCH (p:Pedido)-[c:CONTIENE]->(pr:Producto)-[:OFRECIDO_POR]->(e:Establecimiento)
                RETURN pr.id AS id_producto, pr.nombre AS nombre, e.id AS id_est, e.nombre AS est, SUM(c.cantidad) AS unidades
                ORDER BY unidades DESC
            """)
            productos = list(result)
    finally:
        driver.close()

    db = get_mongo()
    pipeline = list(db.calificaciones.aggregate([
        {"$group": {"_id": "$id_establecimiento", "promedio": {"$avg": "$calificacion_establecimiento.puntaje"}}}
    ]))
    promedios = {c["_id"]: c["promedio"] for c in pipeline}
    seleccionados = []
    for p in productos:
        prom = promedios.get(p["id_est"], 0)
        if p["unidades"] > 100 or (prom and prom > 4.5):
            seleccionados.append({
                "producto": p["nombre"], "establecimiento": p["est"],
                "unidades": p["unidades"], "calificacion_establecimiento": round(prom, 2) if prom else None
            })
    return seleccionados


# ══════════════════════════════════════════════════════════════════════════════
# SEED (extracted from app_web.py)
# ══════════════════════════════════════════════════════════════════════════════

def _cargar_datos_directo():
    import bcrypt as _bcrypt
    from datetime import datetime as _dt, timedelta as _td

    def hp(p):
        return _bcrypt.hashpw(p.encode(), _bcrypt.gensalt()).decode()

    conn = get_postgres()
    cur = conn.cursor()

    clientes_data = [
        ("Manuel", "Oliver", "manu@test.com", "1162822101", hp("test123")),
        ("Fiona", "Garcia", "fiona@test.com", "1145678901", hp("test123")),
        ("Lucho", "Perez", "lucho@test.com", "1198765432", hp("test123")),
    ]
    ids_clientes = []
    for c in clientes_data:
        cur.execute("INSERT INTO cliente (nombre,apellido,email,telefono,password) VALUES (%s,%s,%s,%s,%s) RETURNING id_cliente", c)
        ids_clientes.append(cur.fetchone()[0])

    dirs = [
        (ids_clientes[0], 1, "Cotagaita", "1690", "Ramos Mejia", "1704", "Casa"),
        (ids_clientes[0], 2, "Av. Corrientes", "1234", "CABA", "1043", "Trabajo"),
        (ids_clientes[1], 1, "Belgrano", "5678", "CABA", "1067", "Casa"),
        (ids_clientes[2], 1, "Mitre", "234", "La Plata", "1900", "Casa"),
        (ids_clientes[2], 2, "9 de Julio", "789", "CABA", "1058", "Oficina"),
    ]
    for d in dirs:
        cur.execute("INSERT INTO direccion (id_cliente,nro_direccion,calle,numero,ciudad,cp,alias) VALUES (%s,%s,%s,%s,%s,%s,%s)", d)

    estabs = [
        ("Sushi Club", "Lima 123", "1123435678", "Lun-Vie 13-23", "restaurante", "sushi@test.com", hp("test123"), "Japonesa"),
        ("Burger King", "Av. Cabildo 4000", "1144556677", "Todos los dias 11-23", "restaurante", "bk@test.com", hp("test123"), "Hamburguesas"),
        ("Farmacia Doc", "Santa Fe 2500", "1155667788", "24hs", "tienda", "farmacia@test.com", hp("test123"), "Farmacia"),
    ]
    ids_estab, nombres_estab, tipos_estab = [], [], []
    for nombre, dir_, tel, hor, tipo, email, pwd, extra in estabs:
        cur.execute(
            "INSERT INTO establecimiento (nombre,direccion,telefono,horario,tipo,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_establecimiento",
            (nombre, dir_, tel, hor, tipo, email, pwd)
        )
        id_e = cur.fetchone()[0]
        ids_estab.append(id_e)
        nombres_estab.append(nombre)
        tipos_estab.append(tipo)
        if tipo == "restaurante":
            cur.execute("INSERT INTO restaurante (id_establecimiento,especialidad_culinaria) VALUES (%s,%s)", (id_e, extra))
        else:
            cur.execute("INSERT INTO tienda (id_establecimiento,rubro) VALUES (%s,%s)", (id_e, extra))

    reps = [
        ("Juan", "Lopez", "moto", True, "1166778899", "juan@test.com", hp("test123")),
        ("Maria", "Gomez", "bici", True, "1177889900", "maria@test.com", hp("test123")),
        ("Carlos", "Diaz", "auto", True, "1188990011", "carlos@test.com", hp("test123")),
    ]
    ids_rep, nombres_rep = [], []
    for rd in reps:
        cur.execute("INSERT INTO repartidor (nombre,apellido,vehiculo,disponibilidad,telefono,email,password) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_repartidor", rd)
        ids_rep.append(cur.fetchone()[0])
        nombres_rep.append(rd[0])

    hoy = _dt.now().date()
    for p_data in [
        ("VERANO20", "20% off en restaurantes", 20.0, hoy - _td(10), hoy + _td(30), 1000.0, "Solo restaurantes", "admin"),
        ("ENVIOGRATIS", "Envio gratis", 100.0, hoy - _td(5), hoy + _td(60), 500.0, "Cualquier categoria", "admin"),
    ]:
        cur.execute("INSERT INTO promocion (codigo,descripcion,descuento,fecha_inicio,fecha_fin,monto_minimo,condiciones,creada_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", p_data)
    conn.commit()

    db = get_mongo()
    p_sushi = [
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Roll California", "precio": 4500, "categoria": "rolls", "descripcion": "Palta, kanikama, queso", "disponible": True, "atributos": {"piezas": 8, "picante": "no", "sin_tacc": "si"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Roll Salmon", "precio": 5200, "categoria": "rolls", "descripcion": "Salmon, palta, queso", "disponible": True, "atributos": {"piezas": 8, "picante": "no", "sin_tacc": "si"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Gyoza", "precio": 3200, "categoria": "entrada", "descripcion": "Empanaditas japonesas", "disponible": True, "atributos": {"porciones": 6, "vegetariano": "no"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Coca Cola", "precio": 1800, "categoria": "bebida", "descripcion": "Botella 500ml", "disponible": True, "atributos": {"ml": 500, "alcohol": "no"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Mochi de chocolate", "precio": 2500, "categoria": "postre", "descripcion": "3 unidades", "disponible": True, "atributos": {"porciones": 3, "sin_azucar": "no"}},
    ]
    p_bk = [
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Whopper", "precio": 6500, "categoria": "principal", "descripcion": "Hamburguesa clasica", "disponible": True, "atributos": {"porciones": 1}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Doble Whopper", "precio": 8500, "categoria": "principal", "descripcion": "Doble carne", "disponible": True, "atributos": {"porciones": 1}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Papas medianas", "precio": 2800, "categoria": "entrada", "descripcion": "Papas fritas", "disponible": True, "atributos": {"porciones": 1}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Pepsi", "precio": 1500, "categoria": "bebida", "descripcion": "Lata 354ml", "disponible": True, "atributos": {"ml": 354, "alcohol": "no"}},
    ]
    p_farma = [
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Ibuprofeno 400mg", "precio": 2200, "categoria": "medicamento", "descripcion": "10 comprimidos", "disponible": True, "atributos": {"marca": "Actron"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Alcohol en gel", "precio": 1500, "categoria": "higiene", "descripcion": "250ml", "disponible": True, "atributos": {"marca": "Algabo", "contenido": "250ml"}},
        {"id_producto": f"prod_{uuid.uuid4().hex[:8]}", "nombre": "Vitamina C", "precio": 3500, "categoria": "suplemento", "descripcion": "30 comprimidos", "disponible": True, "atributos": {"marca": "Bayer"}},
    ]
    db.catalogo_establecimientos.insert_many([
        {"_id": ids_estab[0], "nombre": nombres_estab[0], "tipo": tipos_estab[0], "catalogo": p_sushi},
        {"_id": ids_estab[1], "nombre": nombres_estab[1], "tipo": tipos_estab[1], "catalogo": p_bk},
        {"_id": ids_estab[2], "nombre": nombres_estab[2], "tipo": tipos_estab[2], "catalogo": p_farma},
    ])

    session = get_cassandra()
    driver = get_neo4j()
    catalogos = [p_sushi, p_bk, p_farma]
    pedidos_cfg = [
        (0, 1, 0, [(0, 2), (3, 1)], 7, "entregado"), (1, 1, 1, [(0, 1), (2, 1), (3, 2)], 6, "entregado"),
        (0, 1, 1, [(1, 1)], 5, "entregado"), (2, 1, 0, [(0, 1), (4, 2)], 5, "entregado"),
        (1, 1, 2, [(0, 1), (1, 1)], 4, "entregado"), (0, 2, 0, [(1, 2), (4, 1)], 3, "entregado"),
        (2, 2, 1, [(0, 1), (3, 1)], 2, "en_camino"), (1, 1, 0, [(2, 2)], 1, "listo_para_retirar"),
        (0, 1, 2, [(0, 1)], 0, "preparando"), (2, 1, 1, [(0, 1), (2, 1)], 0, "creado"),
        (1, 1, 1, [(1, 1), (2, 1), (3, 1)], 0, "entregado"), (0, 1, 0, [(0, 1)], 0, "creado"),
    ]
    estados_int = {
        "creado": ["creado"], "preparando": ["creado", "aceptado", "preparando"],
        "listo_para_retirar": ["creado", "aceptado", "preparando", "listo_para_retirar"],
        "en_camino": ["creado", "aceptado", "preparando", "listo_para_retirar", "repartidor_asignado", "en_camino"],
        "entregado": ["creado", "aceptado", "preparando", "listo_para_retirar", "repartidor_asignado", "en_camino", "entregado"],
    }
    obs_map = {
        "creado": "Pedido creado", "aceptado": "Pedido recibido", "preparando": "En elaboracion",
        "listo_para_retirar": "Listo para retirar", "en_camino": "Saliendo del local", "entregado": "Pedido entregado"
    }

    for idx_p, (idx_cli, nro_dir, idx_est, prods, dias_atras, estado_final) in enumerate(pedidos_cfg):
        id_cli = ids_clientes[idx_cli]
        id_est = ids_estab[idx_est]
        catalogo = catalogos[idx_est]
        items = []
        total = 0
        for idx_prod, cant in prods:
            p = catalogo[idx_prod]
            sub = p["precio"] * cant
            total += sub
            items.append({"prod": p, "cant": cant, "subtotal": sub})
        fecha_p = _dt.now() - _td(days=dias_atras, hours=2)
        id_rep = ids_rep[idx_p % len(ids_rep)] if estado_final in ("en_camino", "entregado") else None
        cur.execute(
            "INSERT INTO pedido (fecha_hora,total,id_cliente,id_establecimiento,id_repartidor,id_cliente_dir) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id_pedido",
            (fecha_p, total, id_cli, id_est, id_rep, nro_dir)
        )
        id_pedido = cur.fetchone()[0]
        for item in items:
            cur.execute(
                "INSERT INTO detalle_pedido (id_pedido,id_producto,cantidad,precio_unitario,subtotal) VALUES (%s,%s,%s,%s,%s)",
                (id_pedido, item["prod"]["id_producto"], item["cant"], item["prod"]["precio"], item["subtotal"])
            )
        cur.execute(
            "INSERT INTO pago (id_pedido,monto,fecha,metodo,estado) VALUES (%s,%s,%s,%s,%s)",
            (id_pedido, total, fecha_p, "efectivo", "completado" if estado_final == "entregado" else "pendiente")
        )
        timeline = estados_int[estado_final]
        delta = 30 / max(len(timeline) - 1, 1)
        for i, estado in enumerate(timeline):
            f_est = fecha_p + _td(minutes=delta * i)
            obs = obs_map.get(estado)
            if estado == "repartidor_asignado" and id_rep:
                obs = f"Tomado por {nombres_rep[idx_p % len(ids_rep)]}"
            session.execute("INSERT INTO estado_pedido (id_pedido,fecha_hora,estado,observacion) VALUES (%s,%s,%s,%s)", (id_pedido, f_est, estado, obs))
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
            if id_rep and estado_final == "entregado":
                ses.run("MERGE (r:Repartidor {id:$id}) SET r.nombre=$n", id=id_rep, n=nombres_rep[idx_p % len(ids_rep)])
                ses.run("MATCH (r:Repartidor {id:$r}),(p:Pedido {id:$p}) MERGE (r)-[:ENTREGO]->(p)", r=id_rep, p=id_pedido)
        if estado_final == "entregado" and idx_p % 2 == 0:
            pq_e = 5 if idx_p % 3 == 0 else 4
            pq_r = 5 if idx_p % 4 == 0 else 4
            db.calificaciones.insert_one({
                "_id": f"pedido_{id_pedido}", "id_cliente": id_cli, "id_establecimiento": id_est, "id_repartidor": id_rep,
                "fecha": fecha_p.isoformat(),
                "calificacion_establecimiento": {"puntaje": pq_e, "comentario": "Todo excelente" if pq_e == 5 else "Estuvo bien", "respuesta_establecimiento": "Gracias!" if pq_e == 5 else None},
                "calificacion_repartidor": {"puntaje": pq_r, "comentario": "Rapido y amable" if pq_r == 5 else "OK"},
            })
            with driver.session() as ses:
                ses.run("MATCH (c:Cliente {id:$c}),(e:Establecimiento {id:$e}) MERGE (c)-[r:CALIFICO]->(e) SET r.puntaje=$p", c=id_cli, e=id_est, p=pq_e)
                if id_rep:
                    ses.run("MATCH (c:Cliente {id:$c}),(r:Repartidor {id:$r}) MERGE (c)-[rel:CALIFICO]->(r) SET rel.puntaje=$p", c=id_cli, r=id_rep, p=pq_r)

    conn.commit()
    cur.close()
    conn.close()
    driver.close()
    r_redis = get_redis()
    for id_r in ids_rep:
        r_redis.sadd("repartidores:disponibles", str(id_r))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
