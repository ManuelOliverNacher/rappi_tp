"""
RAPPI TP - Aplicacion principal con menu diferenciado por rol.
Ingenieria de Datos II - UADE
"""
import os
from use_cases import auth, cliente, establecimiento, repartidor, admin

ADMIN_USER = "admin"
ADMIN_PASS = "admin1234"


def limpiar_pantalla():
    os.system('clear' if os.name == 'posix' else 'cls')


def header(titulo):
    limpiar_pantalla()
    print("=" * 50)
    print(f"  {titulo}")
    print("=" * 50)


def pedir_opcion(opciones_validas):
    while True:
        opcion = input("\nElegi una opcion: ").strip()
        if opcion in opciones_validas:
            return opcion
        print(f"Opcion invalida. Elegi entre: {', '.join(opciones_validas)}")


def menu_principal():
    while True:
        header("RAPPI - INGRESO")
        print("""
  1. Soy Cliente
  2. Soy Establecimiento (restaurante o tienda)
  3. Soy Repartidor
  4. Admin del sistema

  0. Salir
""")
        opcion = pedir_opcion(["0", "1", "2", "3", "4"])

        if opcion == "0":
            print("\nHasta luego")
            break
        elif opcion == "1":
            flujo_rol("cliente")
        elif opcion == "2":
            flujo_rol("establecimiento")
        elif opcion == "3":
            flujo_rol("repartidor")
        elif opcion == "4":
            flujo_admin()


def flujo_rol(rol):
    header(f"INGRESO COMO {rol.upper()}")
    print(f"""
  1. Iniciar sesion
  2. Registrarme
  0. Volver
""")
    opcion = pedir_opcion(["0", "1", "2"])

    if opcion == "0":
        return
    elif opcion == "1":
        usuario = auth.login(rol)
        if usuario:
            mostrar_menu_rol(rol, usuario)
    elif opcion == "2":
        if rol == "cliente":
            auth.registrar_cliente()
        elif rol == "establecimiento":
            auth.registrar_establecimiento()
        elif rol == "repartidor":
            auth.registrar_repartidor()


def mostrar_menu_rol(rol, usuario):
    if rol == "cliente":
        menu_cliente(usuario)
    elif rol == "establecimiento":
        menu_establecimiento(usuario)
    elif rol == "repartidor":
        menu_repartidor(usuario)


def menu_cliente(usuario):
    while True:
        header(f"Cliente: {usuario.get('nombre', 'Usuario')}")
        print("""
  1. Ver catalogos de establecimientos
  2. Agregar producto al carrito
  3. Ver mi carrito
  4. Confirmar pedido
  5. Ver estado de mis pedidos
  6. Calificar un pedido
  7. Ver mi historial de pedidos
  8. Aplicar promocion

  0. Cerrar sesion
""")
        opcion = pedir_opcion(["0", "1", "2", "3", "4", "5", "6", "7", "8"])

        if opcion == "0":
            auth.logout(usuario)
            break
        elif opcion == "1": cliente.ver_catalogos()
        elif opcion == "2": cliente.agregar_al_carrito(usuario)
        elif opcion == "3": cliente.ver_carrito(usuario)
        elif opcion == "4": cliente.confirmar_pedido(usuario)
        elif opcion == "5": cliente.ver_mis_pedidos(usuario)
        elif opcion == "6": cliente.calificar_pedido(usuario)
        elif opcion == "7": cliente.ver_historial(usuario)
        elif opcion == "8": cliente.aplicar_promocion(usuario)


def menu_establecimiento(usuario):
    while True:
        header(f"Establecimiento: {usuario.get('nombre', 'Negocio')}")
        print("""
  1. Ver mi catalogo
  2. Agregar producto al catalogo
  3. Actualizar producto
  4. Ver pedidos pendientes
  5. Cambiar estado de un pedido
  6. Ver calificaciones recibidas
  7. Responder a una calificacion
  8. Crear promocion

  0. Cerrar sesion
""")
        opcion = pedir_opcion(["0", "1", "2", "3", "4", "5", "6", "7", "8"])

        if opcion == "0":
            auth.logout(usuario)
            break
        elif opcion == "1": establecimiento.ver_mi_catalogo(usuario)
        elif opcion == "2": establecimiento.agregar_producto(usuario)
        elif opcion == "3": establecimiento.actualizar_producto(usuario)
        elif opcion == "4": establecimiento.ver_pedidos_pendientes(usuario)
        elif opcion == "5": establecimiento.cambiar_estado_pedido(usuario)
        elif opcion == "6": establecimiento.ver_calificaciones(usuario)
        elif opcion == "7": establecimiento.responder_calificacion(usuario)
        elif opcion == "8": establecimiento.crear_promocion(usuario)


def menu_repartidor(usuario):
    while True:
        header(f"Repartidor: {usuario.get('nombre', 'Repartidor')}")
        print("""
  1. Marcar como disponible
  2. Marcar como ocupado
  3. Ver pedidos asignados a mi
  4. Actualizar estado de entrega
  5. Ver mis calificaciones

  0. Cerrar sesion
""")
        opcion = pedir_opcion(["0", "1", "2", "3", "4", "5"])

        if opcion == "0":
            auth.logout(usuario)
            break
        elif opcion == "1": repartidor.marcar_disponible(usuario)
        elif opcion == "2": repartidor.marcar_ocupado(usuario)
        elif opcion == "3": repartidor.ver_pedidos_asignados(usuario)
        elif opcion == "4": repartidor.actualizar_estado_entrega(usuario)
        elif opcion == "5": repartidor.ver_mis_calificaciones(usuario)


def flujo_admin():
    header("ADMIN - INGRESO")
    user = input("\nUsuario: ").strip()
    password = input("Password: ").strip()

    if user == ADMIN_USER and password == ADMIN_PASS:
        menu_admin()
    else:
        print("\nCredenciales incorrectas")
        input("\nPresione Enter para continuar...")


def menu_admin():
    while True:
        header("ADMIN - PANEL")
        print("""
  GESTION:
   1. Cargar datos de prueba (seed)
   2. Verificar conexion a las 5 bases
   3. Limpiar TODAS las bases

  REPORTES:
   4. Pedidos por ciudad
   5. Productos mas solicitados
   6. Restaurantes mas populares
   7. Categorias top los fines de semana
   8. Pedidos >$50 entregados en <30 min
   9. Productos con >100 pedidos o calif >4.5

   0. Cerrar sesion
""")
        opcion = pedir_opcion(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])

        if opcion == "0":
            break
        elif opcion == "1": admin.cargar_datos_prueba()
        elif opcion == "2": admin.verificar_conexiones()
        elif opcion == "3": admin.limpiar_todas_las_bases()
        elif opcion == "4": admin.reporte_pedidos_por_ciudad()
        elif opcion == "5": admin.reporte_productos_mas_solicitados()
        elif opcion == "6": admin.reporte_restaurantes_populares()
        elif opcion == "7": admin.reporte_categorias_findes()
        elif opcion == "8": admin.reporte_rapidos_y_caros()
        elif opcion == "9": admin.reporte_top_productos()


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\nHasta luego")