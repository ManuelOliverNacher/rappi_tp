"""
Modulo de autenticacion.
Maneja registro, login y logout de los 3 roles: cliente, establecimiento, repartidor.
"""
import bcrypt
import json
from connections import get_postgres, get_redis


def hashear_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_password(password, hash_guardado):
    return bcrypt.checkpw(password.encode('utf-8'), hash_guardado.encode('utf-8'))


def pedir_dato(label, requerido=True):
    """Pide un dato. Si el usuario escribe '0', cancela la operacion (devuelve None)."""
    while True:
        valor = input(f"  {label} (0 para cancelar): ").strip()
        if valor == "0":
            return None
        if valor or not requerido:
            return valor
        print("  Este campo es obligatorio")


def registrar_cliente():
    print("\nREGISTRO DE CLIENTE\n")
    print("(Escribi '0' en cualquier campo para cancelar)\n")

    nombre = pedir_dato("Nombre")
    if nombre is None: return
    apellido = pedir_dato("Apellido")
    if apellido is None: return
    email = pedir_dato("Email")
    if email is None: return
    email = email.lower()
    telefono = pedir_dato("Telefono", requerido=False)
    if telefono is None: return
    password = pedir_dato("Password")
    if password is None: return

    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_cliente FROM cliente WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"\nYa existe un cliente con el email {email}")
            input("\nPresione Enter para continuar...")
            return

        pwd_hash = hashear_password(password)
        cur.execute("""
            INSERT INTO cliente (nombre, apellido, email, telefono, password)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_cliente
        """, (nombre, apellido, email, telefono, pwd_hash))
        id_nuevo = cur.fetchone()[0]
        conn.commit()

        print(f"\nCliente registrado correctamente (ID: {id_nuevo})")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
    finally:
        cur.close()
        conn.close()

    input("\nPresione Enter para continuar...")


def registrar_establecimiento():
    print("\nREGISTRO DE ESTABLECIMIENTO\n")
    print("(Escribi '0' en cualquier campo para cancelar)\n")

    nombre = pedir_dato("Nombre del establecimiento")
    if nombre is None: return
    direccion = pedir_dato("Direccion")
    if direccion is None: return
    telefono = pedir_dato("Telefono", requerido=False)
    if telefono is None: return
    horario = pedir_dato("Horario (ej: Lun-Vie 10-22)", requerido=False)
    if horario is None: return

    print("\nTipo de establecimiento:")
    print("  1. Restaurante")
    print("  2. Tienda")
    print("  0. Cancelar")
    while True:
        tipo_opcion = input("  Elegi 1, 2 o 0: ").strip()
        if tipo_opcion == "0":
            return
        elif tipo_opcion == "1":
            tipo = "restaurante"
            extra_label = "Especialidad culinaria (ej: italiana, sushi, parrilla)"
            break
        elif tipo_opcion == "2":
            tipo = "tienda"
            extra_label = "Rubro (ej: farmacia, electronica, kiosco)"
            break
        else:
            print("  Opcion invalida")

    extra = pedir_dato(extra_label)
    if extra is None: return
    email = pedir_dato("Email")
    if email is None: return
    email = email.lower()
    password = pedir_dato("Password")
    if password is None: return

    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_establecimiento FROM establecimiento WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"\nYa existe un establecimiento con el email {email}")
            input("\nPresione Enter para continuar...")
            return

        pwd_hash = hashear_password(password)

        cur.execute("""
            INSERT INTO establecimiento (nombre, direccion, telefono, horario, tipo, email, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_establecimiento
        """, (nombre, direccion, telefono, horario, tipo, email, pwd_hash))
        id_nuevo = cur.fetchone()[0]

        if tipo == "restaurante":
            cur.execute("""
                INSERT INTO restaurante (id_establecimiento, especialidad_culinaria)
                VALUES (%s, %s)
            """, (id_nuevo, extra))
        else:
            cur.execute("""
                INSERT INTO tienda (id_establecimiento, rubro)
                VALUES (%s, %s)
            """, (id_nuevo, extra))

        conn.commit()
        print(f"\n{tipo.capitalize()} registrado correctamente (ID: {id_nuevo})")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
    finally:
        cur.close()
        conn.close()

    input("\nPresione Enter para continuar...")


def registrar_repartidor():
    print("\nREGISTRO DE REPARTIDOR\n")
    print("(Escribi '0' en cualquier campo para cancelar)\n")

    nombre = pedir_dato("Nombre")
    if nombre is None: return
    apellido = pedir_dato("Apellido")
    if apellido is None: return
    vehiculo = pedir_dato("Vehiculo (moto, auto, bici)", requerido=False)
    if vehiculo is None: return
    telefono = pedir_dato("Telefono", requerido=False)
    if telefono is None: return
    email = pedir_dato("Email")
    if email is None: return
    email = email.lower()
    password = pedir_dato("Password")
    if password is None: return

    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id_repartidor FROM repartidor WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"\nYa existe un repartidor con el email {email}")
            input("\nPresione Enter para continuar...")
            return

        pwd_hash = hashear_password(password)
        cur.execute("""
            INSERT INTO repartidor (nombre, apellido, vehiculo, disponibilidad, telefono, email, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_repartidor
        """, (nombre, apellido, vehiculo, True, telefono, email, pwd_hash))
        id_nuevo = cur.fetchone()[0]
        conn.commit()

        print(f"\nRepartidor registrado correctamente (ID: {id_nuevo})")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
    finally:
        cur.close()
        conn.close()

    input("\nPresione Enter para continuar...")

def login(rol):
    print(f"\nLOGIN COMO {rol.upper()}")
    print("(Escribi '0' en cualquier campo para cancelar)\n")

    email = pedir_dato("Email")
    if email is None: return None
    email = email.lower()
    password = pedir_dato("Password")
    if password is None: return None

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

    if rol not in config:
        print(f"Rol invalido: {rol}")
        input("\nPresione Enter para continuar...")
        return None

    cfg = config[rol]
    conn = get_postgres()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT {cfg['campos']} FROM {cfg['tabla']} WHERE email = %s",
            (email,)
        )
        row = cur.fetchone()

        if not row:
            print(f"\nNo existe ningun {rol} con ese email")
            input("\nPresione Enter para continuar...")
            return None

        pwd_hash = row[-1]
        if not verificar_password(password, pwd_hash):
            print("\nPassword incorrecta")
            input("\nPresione Enter para continuar...")
            return None

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

    r = get_redis()
    clave_sesion = f"sesion:{rol}:{usuario['id']}"
    r.set(clave_sesion, json.dumps(usuario), ex=600)

    print(f"\nBienvenido, {usuario['nombre']}")
    print(f"Sesion iniciada (expira en 10 minutos)")
    input("\nPresione Enter para continuar...")
    return usuario

def logout(usuario):
    if not usuario:
        return

    r = get_redis()
    clave_sesion = f"sesion:{usuario['rol']}:{usuario['id']}"
    r.delete(clave_sesion)

    print(f"\nHasta luego, {usuario['nombre']}")
    print(f"Sesion cerrada")
    input("\nPresione Enter para continuar...")