# Resumen de Exposición — Rappi TP
## Ingeniería de Datos II · UADE
**Equipo:** Manuel Oliver Nacher · Fiona Pardo · Luciano Frasca · Matias Vilches · Tomas Zocchi

---

## 1. Pitch de arranque

Construimos una aplicación de delivery tipo Rappi que usa **cinco bases de datos simultáneas**, cada una resolviendo exactamente el problema para el que fue diseñada. No hay una base "principal" y otras "de soporte": PostgreSQL maneja transacciones, MongoDB guarda catálogos flexibles, Cassandra registra la historia de estados, Neo4j modela relaciones entre entidades, y Redis actúa como caché, carrito y lock distribuido.

La lógica de negocio vive completamente en Python (`use_cases/`), expuesta como API REST (FastAPI) y consumida por un frontend React o directamente desde la consola (`main.py`) o Streamlit (`app_web.py`).

**Frase para arrancar la expo:**
> *"Diseñamos el sistema eligiendo cada base por sus fortalezas nativas, no por conveniencia. Cada escritura o lectura está justificada por la naturaleza del dato."*

---

## 2. Las 5 bases: qué guarda cada una y por qué

### PostgreSQL (Supabase)
**Qué guarda:** usuarios (cliente, establecimiento, repartidor), pedidos, detalle de pedido, pagos, promociones, direcciones de entrega.

**Por qué PostgreSQL:** estos datos son relacionales y requieren consistencia ACID estricta. Un pedido siempre debe tener su detalle y su pago. Si algún INSERT falla, se hace rollback de toda la transacción. Los JOINs entre pedido, cliente, establecimiento y dirección son frecuentes y están indexados.

**Por qué NO otra:**
- No MongoDB porque los datos de pedidos tienen esquema rígido y necesitan transacciones multi-tabla con rollback.
- No Redis porque los datos deben persistir de forma duradera y ser consultables con filtros complejos (ciudad, fecha, total).
- No Cassandra porque no es apta para JOINs ni para writes transaccionales multi-tabla.

---

### MongoDB (Atlas)
**Qué guarda:** catálogos de productos por establecimiento (`catalogo_establecimientos`) y calificaciones de pedidos (`calificaciones`).

**Por qué MongoDB:** los productos tienen atributos variables según categoría (un roll de sushi tiene "piezas" y "picante"; un medicamento tiene "marca" y "requiere_receta"). MongoDB permite guardar cada producto con sus propios campos sin alterar un esquema fijo. Las calificaciones también son documentos embebidos con estructura opcional (puede haber o no calificación de repartidor).

**Por qué NO otra:**
- No PostgreSQL porque agregarle columnas opcionales a una tabla de productos para cada tipo de producto sería un desastre (NULLs masivos o tablas heredadas complejas).
- No Redis porque los catálogos son demasiado grandes para key-value y necesitan consultas por campo (buscar productos por id, filtrar disponibles).
- No Neo4j porque el catálogo es un documento, no una red de relaciones.

---

### Cassandra (Astra DB)
**Qué guarda:** la tabla `estado_pedido` con columnas `(id_pedido, fecha_hora, estado, observacion)`. Es una serie temporal: cada cambio de estado de un pedido genera un registro nuevo.

**Por qué Cassandra:** el patrón de acceso es siempre "dame todos los estados de este pedido ordenados por tiempo". Cassandra está optimizada para writes masivos con alta disponibilidad y para leer por partition key (id_pedido). El clustering por fecha_hora garantiza el orden cronológico.

**Por qué NO otra:**
- No PostgreSQL porque guardar una fila por cada cambio de estado en Postgres es costoso en writes bajo carga y no aporta las garantías de disponibilidad de Cassandra para series temporales.
- No MongoDB porque el patrón de append-only de series temporales es exactamente el caso de uso de Cassandra.

**Nota técnica:** Astra DB usa protocolo DSE que el driver Python nativo no soporta. Se implementó `AstraRestSession` en `connections.py`, un wrapper que traduce `session.execute(cql, params)` a llamadas HTTP al REST v2 de Astra, manteniendo la misma interfaz para el resto del código.

---

### Neo4j (Aura)
**Qué guarda:** nodos `Cliente`, `Establecimiento`, `Pedido`, `Producto`, `Repartidor` y relaciones `REALIZO`, `CONTIENE`, `OFRECIDO_POR`, `ENTREGO`, `CALIFICO`.

**Por qué Neo4j:** los reportes que cruzan "qué productos pidió qué cliente", "qué repartidor entregó qué pedido", o "qué establecimientos tienen mejor calificación de sus clientes habituales" son consultas de grafo naturales. En SQL equivaldrían a JOINs de 4 o 5 niveles que se vuelven lentos con volumen.

**Por qué NO otra:**
- No PostgreSQL porque las consultas de navegación por relaciones (camino entre entidades) son O(n) en SQL y O(1) en Neo4j por cada salto.
- No MongoDB porque los documentos no modelan relaciones cruzadas eficientemente.

---

### Redis (Redis Cloud)
**Qué guarda:** sesiones de usuarios, carritos de compra (como Hash), caché de catálogos, caché de promociones, locks distribuidos y sets de disponibilidad de repartidores.

**Por qué Redis:** es in-memory, submilisegundo. El carrito debe ser instantáneo. El caché de catálogos evita ir a MongoDB en cada consulta. Los locks (NX + EX) previenen que dos repartidores tomen el mismo pedido o que el cliente haga doble-click en confirmar pedido.

**Por qué NO otra:**
- No PostgreSQL porque las sesiones y el carrito son datos temporales; agregar TTL y sets en SQL es costoso y verboso.
- No MongoDB porque Redis tiene tipos de datos nativos (Hash, Set, String con TTL, operaciones atómicas NX) perfectos para estos patrones.

---

## 3. Casos de uso — La sección más importante

### Tabla resumen: qué caso toca qué base

| Caso de uso | PostgreSQL | MongoDB | Cassandra | Neo4j | Redis |
|-------------|:----------:|:-------:|:---------:|:-----:|:-----:|
| Login / logout | ✓ (read) | | | | ✓ (sesion write/delete) |
| Registro usuario | ✓ (write) | | | | |
| Ver catálogo (cliente) | ✓ (lista establecimientos) | ✓ (productos) | | | ✓ (cache hit/miss) |
| Agregar al carrito | ✓ (lista establecimientos) | ✓ (productos disponibles) | | | ✓ (Hash write) |
| Confirmar pedido ⭐ | ✓ (pedido+detalle+pago) | | ✓ (estado "creado") | ✓ (grafo) | ✓ (lock + delete carrito) |
| Ver mis pedidos | ✓ (cabecera) | | ✓ (estado actual) | | |
| Aplicar promoción | ✓ (fallback) | | | | ✓ (cache-aside) |
| Calificar pedido ⭐ | ✓ (read pedido) | ✓ (write calificacion) | ✓ (verifica entregado) | ✓ (CALIFICO) | |
| Historial de pedidos | ✓ (pedidos+detalle) | ✓ (nombres productos) | | | |
| Agregar producto (establecimiento) | | ✓ (write catalogo) | | | ✓ (invalida cache) |
| Actualizar producto | | ✓ (update catalogo) | | | ✓ (invalida cache) |
| Cambiar estado pedido (est.) | | | ✓ (write estado) | | ✓ (invalida cache) |
| Calificaciones (est.) | | ✓ (read + write respuesta) | | | |
| Crear promoción | ✓ (write) | | | | ✓ (cache con TTL) |
| Tomar pedido (repartidor) ⭐ | ✓ (UPDATE pedido + repartidor) | | ✓ (estado "repartidor_asignado") | | ✓ (lock NX + SMOVE sets) |
| Actualizar entrega (repartidor) | ✓ (si entregado: disponibilidad) | | ✓ (write estado) | ✓ (si entregado: ENTREGO) | ✓ (si entregado: SMOVE) |
| Ver calificaciones (repartidor) | | ✓ (read) | | | |
| Reporte: pedidos por ciudad | ✓ (JOIN+GROUP BY) | | | | |
| Reporte: productos más pedidos | | | | ✓ (CONTIENE sum) | |
| Reporte: locales populares | | | | ✓ (CONTIENE + CALIFICO) | |
| Reporte: categorías en fines | ✓ (DOW filter) | ✓ (categorías) | | | |
| Reporte: pedidos rápidos y caros | ✓ (total>50) | | ✓ (timestamps creado→entregado) | | |
| Reporte: top productos | | ✓ (calif. promedio) | | ✓ (unidades) | |

⭐ = mostrar en la demo si no alcanza el tiempo

---

### Caso estrella 1: Confirmar pedido (cliente)

Este es el caso más rico porque escribe en 4 bases en secuencia. Lo que hace `confirmar_pedido()` en `use_cases/cliente.py`:

**Paso 0 — Lock anti-doble-click (Redis):**
```
SET lock:checkout:cliente:{id} "1" NX EX 10
```
Si la clave ya existe (otro proceso o doble-click) devuelve error inmediatamente. TTL de 10 segundos como seguro.

**Paso 1 — Dirección de entrega (PostgreSQL):**
Muestra las direcciones guardadas del cliente o permite crear una nueva. Se escribe en la tabla `direccion` si es nueva.

**Paso 2 — INSERT transaccional (PostgreSQL):**
Dentro de un mismo `try/except` con `rollback`:
- INSERT en `pedido` → obtiene `id_pedido`
- INSERT en `detalle_pedido` (un row por producto)
- INSERT en `pago` (método: efectivo, estado: pendiente)
- INSERT en `promocion_pedido` (si había código aplicado)
Si cualquier INSERT falla, `conn.rollback()` revierte todo.

**Paso 3 — Estado inicial (Cassandra):**
```sql
INSERT INTO estado_pedido (id_pedido, fecha_hora, estado, observacion)
VALUES (?, ?, 'creado', 'Pedido creado por el cliente')
```
Fallo no-crítico: si Cassandra falla, el pedido ya está en Postgres y se muestra un aviso sin interrumpir el flujo.

**Paso 4 — Grafo (Neo4j):**
Crea o actualiza (MERGE) nodos `Cliente`, `Establecimiento`, `Pedido` y cada `Producto`. Crea las relaciones:
- `(Cliente)-[:REALIZO]->(Pedido)`
- `(Pedido)-[:CONTIENE {cantidad}]->(Producto)` por cada item
- `(Producto)-[:OFRECIDO_POR]->(Establecimiento)`

Fallo no-crítico: si Neo4j falla (DNS, instancia pausada), el pedido sigue siendo válido.

**Paso 5 — Limpiar carrito (Redis):**
```
DEL carrito:cliente:{id}
```
El lock se libera en el bloque `finally`, siempre, incluso si algo falla.

---

### Caso estrella 2: Tomar pedido (repartidor)

Demuestra el patrón de lock distribuido para concurrencia. Lo que hace `tomar_pedido()` en `use_cases/repartidor.py`:

**Lock anti-concurrencia (Redis):**
```
SET lock:repartidor:asignacion:{id_pedido} {id_repartidor} NX EX 5
```
Si dos repartidores intentan tomar el mismo pedido al mismo tiempo, solo el primero obtiene el lock. El segundo recibe "Otro repartidor ya está tomando este pedido". TTL de 5 segundos.

**Verificación double-check (PostgreSQL):**
Aunque el lock está activo, se verifica nuevamente que `id_repartidor IS NULL` en el pedido antes de actualizar. Esto previene race conditions si el lock expiró muy rápido.

**Updates (PostgreSQL):**
- `UPDATE pedido SET id_repartidor = ?` — asigna el repartidor
- `UPDATE repartidor SET disponibilidad = false` — lo marca como ocupado

**Estado (Cassandra):**
INSERT `repartidor_asignado` con observación "Tomado por {nombre}".

**Sets de disponibilidad (Redis):**
```
SMOVE repartidores:disponibles repartidores:ocupados {id_repartidor}
```
El set `repartidores:disponibles` permite al sistema saber instantáneamente cuántos repartidores hay libres sin consultar Postgres.

**Al entregar:** el flujo se invierte — Cassandra registra `entregado`, Redis hace el SMOVE de vuelta a disponibles, Postgres actualiza disponibilidad a true, y Neo4j crea `(Repartidor)-[:ENTREGO]->(Pedido)`.

---

### Caso estrella 3: Ver catálogo (cliente) — patrón cache-aside

Demuestra cómo Redis reduce la carga sobre MongoDB. Lo que hace `mostrar_catalogo()` en `use_cases/cliente.py`:

```python
# Intento 1: Redis
cache = r.get(f"catalogo:establecimiento:{id_establecimiento}")
if cache:
    doc = json.loads(cache)   # Sirve desde memoria, ~1ms
else:
    # Intento 2: MongoDB
    doc = db.catalogo_establecimientos.find_one({"_id": id_establecimiento})
    r.set(clave_cache, json.dumps(doc), ex=300)   # Guarda en cache 5 minutos
```

Cuando el establecimiento modifica su catálogo (`agregar_producto`, `actualizar_producto`, `cambiar disponibilidad`), se ejecuta:
```python
r.delete(f"catalogo:establecimiento:{id_establecimiento}")
```
Esto invalida el cache para que la próxima consulta vaya a MongoDB y traiga datos frescos.

---

### Caso complementario: Calificar pedido (cliente)

Muestra cómo Cassandra actúa como fuente de verdad para el estado y MongoDB como almacén de documentos ricos.

1. **Cassandra:** se consulta el estado actual del pedido para verificar que esté `entregado`. Solo se puede calificar un pedido entregado.
2. **MongoDB:** se verifica que no exista ya `calificaciones.find_one({"_id": "pedido_{id}"})`. Evita calificaciones duplicadas.
3. **MongoDB:** se inserta el documento de calificación con puntaje (1-5), comentario opcional y respuesta del establecimiento (inicialmente null).
4. **Neo4j:** se crea la relación `(Cliente)-[:CALIFICO {puntaje}]->(Establecimiento)` y, si hubo repartidor, `(Cliente)-[:CALIFICO]->(Repartidor)`.

---

## 4. Los reportes del panel Admin

Todos están en `use_cases/admin.py`. Los interesantes son los que cruzan bases:

| Reporte | Bases | Cómo cruza |
|---------|-------|-----------|
| Pedidos por ciudad | Solo PostgreSQL | JOIN entre `pedido` y `direccion`, GROUP BY ciudad y fecha |
| Productos más pedidos | Solo Neo4j | `MATCH (Pedido)-[CONTIENE]->(Producto)` SUM de cantidades |
| Locales más populares | Solo Neo4j | Combina cantidad de pedidos con promedio de `[:CALIFICO]` |
| **Categorías en fines de semana** | PostgreSQL + MongoDB | Postgres filtra `DOW IN (0,6)` → trae ids de productos; Mongo resuelve la categoría de cada id |
| **Pedidos rápidos y caros** | PostgreSQL + Cassandra | Postgres filtra `total > 50` → Cassandra calcula el tiempo entre estado `creado` y `entregado` |
| **Top productos** | Neo4j + MongoDB | Neo4j cuenta unidades pedidas por producto; Mongo calcula promedio de calificación del establecimiento; combina los dos filtros (>100 unidades OR calif >4.5) |

**Por qué necesita cruzar en "Categorías en fines de semana":** PostgreSQL sabe cuándo se hizo el pedido y qué productos tiene, pero no sabe la categoría del producto (eso está en MongoDB). Entonces primero filtra días de finde en Postgres (EXTRACT DOW), luego va a MongoDB a buscar la categoría de cada id_producto.

**Por qué necesita cruzar en "Pedidos rápidos y caros":** PostgreSQL tiene el monto total del pedido, pero no tiene los timestamps de cada estado — eso está en Cassandra. Primero filtra `total > 50` en Postgres, luego consulta Cassandra para calcular cuánto tardó desde `creado` hasta `entregado`.

---

## 5. Conclusión para cerrar

La persistencia políglota no es "usar muchas bases para parecer más técnico". Es elegir la herramienta correcta para cada problema: consistencia transaccional en SQL, flexibilidad documental en Mongo, escalabilidad temporal en Cassandra, navegación de relaciones en Neo4j, velocidad y temporalidad en Redis. El desafío real es mantener la consistencia entre ellas, que resolvemos con writes ordenados, locks distribuidos y fallas no-críticas aisladas que no rompen el flujo principal.

---

## 6. Machete de preguntas del profe — respuestas cortas

**¿Por qué no usaron solo PostgreSQL para todo?**
PostgreSQL no escala bien para series temporales de estados (Cassandra), no modela bien atributos variables por producto (MongoDB), las consultas de grafo son O(n JOINs) en SQL vs O(1) por salto en Neo4j, y Redis es in-memory lo que ninguna DB relacional iguala para carrito y locks.

**¿Qué pasa si Neo4j falla?**
El pedido igual se crea. Las escrituras en Neo4j están dentro de `try/except` con mensaje de aviso. El grafo se puede reconstruir desde PostgreSQL si es necesario. Es la única base que toleramos como degraded-mode.

**¿Por qué Cassandra para los estados y no PostgreSQL?**
El patrón es append-only + leer por partition key (id_pedido). Cassandra está diseñada exactamente para eso: writes muy rápidos y sin locks, alta disponibilidad, ordenación por clustering key (fecha_hora). En Postgres habría que indexar una tabla que crece indefinidamente.

**¿Cómo evitan que dos repartidores tomen el mismo pedido?**
Con un lock distribuido en Redis: `SET lock:repartidor:asignacion:{id_pedido} NX EX 5`. `NX` significa "solo escribe si NO existe". El primero en escribir gana; el segundo recibe error. TTL de 5 segundos como fail-safe si el proceso se cae.

**¿Qué es el TTL del carrito?**
24 horas (`r.expire(clave_carrito, 86400)`). Se extiende cada vez que agregás un producto. Al confirmar el pedido, se elimina con `DEL`.

**¿Cómo funciona el caché de catálogos?**
Patrón cache-aside: primero se busca en Redis (`r.get()`). Si está, se sirve desde ahí (JSON serializado, TTL 5 minutos). Si no está, se consulta MongoDB y se guarda en Redis. Cuando el establecimiento modifica su catálogo, se invalida la clave de cache (`r.delete()`).

**¿Cómo guardan las sesiones?**
En Redis con clave `sesion:{rol}:{id_usuario}`, TTL 600 segundos (10 minutos). Contiene un JSON con id, rol, nombre y email. El frontend guarda la sesión en `localStorage`. La app Python la consulta en cada request autenticado.

**¿Cómo conectan a Cassandra si no tienen el driver nativo?**
Astra DB usa protocolo DSE que `cassandra-driver` 3.x no soporta. Implementamos `AstraRestSession` en `connections.py`: un wrapper con la misma interfaz (`session.execute(cql, params)`) que internamente hace HTTP al REST v2 de Astra. Parsea el CQL con regex para extraer tabla, columnas y parámetros.

**¿MongoDB tiene esquema o no?**
No tiene esquema fijo, pero nosotros lo respetamos por convención. Cada documento de catálogo tiene `_id` = id del establecimiento, `nombre`, `tipo` y un array `catalogo` donde cada producto tiene `id_producto`, `nombre`, `precio`, `categoria`, `disponible` y `atributos` (este último varía por categoría).

**¿Qué es el doble-click lock en el checkout?**
`SET lock:checkout:cliente:{id} "1" NX EX 10`. Si el cliente hace doble-click en "Confirmar pedido" o hay dos requests simultáneos, el segundo encuentra la clave y recibe un error amigable. Se libera en el bloque `finally` del try, siempre.

**¿Cómo muestran el estado actual de un pedido?**
Cassandra guarda todos los estados con timestamp. El código consulta con `LIMIT 1` y ordena por `fecha_hora DESC` (el AstraRestSession hace el sort en Python antes de devolver los resultados). El estado más reciente es el actual.

**¿Cuándo se escribe en Neo4j?**
En tres momentos: al confirmar un pedido (nodos + relaciones REALIZO/CONTIENE/OFRECIDO_POR), al entregar un pedido (ENTREGO), y al calificar (CALIFICO). También en el seed de datos de prueba.

**¿Para qué sirven los Sets de Redis?**
`repartidores:disponibles` y `repartidores:ocupados` son Redis Sets que contienen los IDs de repartidores en cada estado. `SMOVE` es atómico: mueve un ID de un set al otro en una sola operación. Permite saber instantáneamente cuántos repartidores hay libres sin consultar PostgreSQL.

---

## 7. Apéndice técnico breve

### Estructura de tablas PostgreSQL (principales)

```
cliente         (id_cliente, nombre, apellido, email, telefono, password)
establecimiento (id_establecimiento, nombre, direccion, telefono, horario, tipo, email, password)
restaurante     (id_establecimiento FK, especialidad_culinaria)
tienda          (id_establecimiento FK, rubro)
repartidor      (id_repartidor, nombre, apellido, vehiculo, disponibilidad, telefono, email, password)
pedido          (id_pedido, fecha_hora, total, id_cliente FK, id_establecimiento FK, id_repartidor FK, id_cliente_dir)
detalle_pedido  (id_pedido FK, id_producto, cantidad, precio_unitario, subtotal)
pago            (id_pago, id_pedido FK, monto, fecha, metodo, estado)
promocion       (id_promocion, codigo UNIQUE, descripcion, descuento, fecha_inicio, fecha_fin, monto_minimo, condiciones, creada_por)
promocion_pedido(id_promocion FK, id_pedido FK, descuento_aplicado)
direccion       (id_cliente FK, nro_direccion, calle, numero, ciudad, cp, alias)
```

### Documento MongoDB — calificaciones

```json
{
  "_id": "pedido_42",
  "id_cliente": 1,
  "id_establecimiento": 2,
  "id_repartidor": 3,
  "fecha": "2026-06-15T10:30:00",
  "calificacion_establecimiento": {
    "puntaje": 5,
    "comentario": "Excelente",
    "respuesta_establecimiento": "Gracias!"
  },
  "calificacion_repartidor": {
    "puntaje": 4,
    "comentario": "Llegó rápido"
  }
}
```

### Tabla Cassandra — estado_pedido

```sql
CREATE TABLE estado_pedido (
    id_pedido     INT,
    fecha_hora    TIMESTAMP,
    estado        TEXT,
    observacion   TEXT,
    PRIMARY KEY (id_pedido, fecha_hora)
) WITH CLUSTERING ORDER BY (fecha_hora DESC);
```

### Grafo Neo4j — nodos y relaciones

```
Nodos:    Cliente, Establecimiento, Pedido, Producto, Repartidor
Relaciones:
  (Cliente)-[:REALIZO]->(Pedido)
  (Pedido)-[:CONTIENE {cantidad}]->(Producto)
  (Producto)-[:OFRECIDO_POR]->(Establecimiento)
  (Repartidor)-[:ENTREGO]->(Pedido)
  (Cliente)-[:CALIFICO {puntaje}]->(Establecimiento)
  (Cliente)-[:CALIFICO {puntaje}]->(Repartidor)
```

### Patrones de claves Redis (verificado en código)

| Clave | Tipo | TTL real | Uso |
|-------|------|----------|-----|
| `sesion:{rol}:{id}` | String (JSON) | 600s (10 min) | Sesión activa |
| `carrito:cliente:{id}` | Hash | 86400s (24 hs) | Carrito en curso |
| `catalogo:establecimiento:{id}` | String (JSON) | 300s (5 min) | Cache de catálogo |
| `promo:{codigo}` | String (JSON) | dias_restantes × 86400 | Cache de promoción |
| `lock:checkout:cliente:{id}` | String | 10s | Anti-doble-click checkout |
| `lock:repartidor:asignacion:{id_pedido}` | String | 5s | Anti-doble-asignación |
| `repartidores:disponibles` | Set | sin TTL | IDs libres |
| `repartidores:ocupados` | Set | sin TTL | IDs con pedido activo |

### Cómo correr la app para la demo

```bash
# Backend (terminal 1)
uvicorn api_server:app --reload --port 8000

# Frontend (terminal 2)
cd frontend && npm run dev
# → http://localhost:5173

# CLI (alternativa)
python main.py

# Streamlit (alternativa)
streamlit run app_web.py
# → http://localhost:8501
```

### Estados posibles de un pedido (en orden)

`creado` → `aceptado` → `preparando` → `listo_para_retirar` → `repartidor_asignado` → `en_camino` → `entregado`

También existe `cancelado` (desde el establecimiento).

---

## 8. Diferencias verificadas entre el código y la documentación

Estas diferencias las encontré leyendo el código real. **Si el profe corre la app, va a ver lo que está en el código, no en el README.**

| Dato | README dice | Código real | Dónde |
|------|------------|-------------|-------|
| TTL carrito Redis | "2 hs" | **24 hs** (86400s) | `cliente.py` línea 205 |
| TTL catálogo Redis | "1 hora" | **5 minutos** (300s) | `cliente.py` línea 76 |
| TTL lock checkout | "5 seg" | **10 segundos** | `cliente.py` línea 281 |
| Nombre clave sesión | `session:{token}` | **`sesion:{rol}:{id_usuario}`** | `auth.py` + `connections.py` |
| Nombre clave lock checkout | `lock:pedido:{id}` | **`lock:checkout:cliente:{id}`** | `cliente.py` línea 280 |
| "Exportación a CSV" en Analytics | Mencionado en README | **No existe en el código** | — |
| `actualizar_producto` CLI | No mencionado como faltante | **Fue implementado** (esta sesión) | `establecimiento.py` |

### Aviso para la demo

- **Neo4j puede estar pausada** (Aura free-tier se pausa a los 3 días). Antes de exponer, entrá a `console.neo4j.io` y verificá que esté activa. Si no, los reportes 2, 3 y 6 van a fallar, y los pedidos van a mostrar un warning pero igual se van a crear.
- **Orden de inicio:** primero levantá el backend (`uvicorn`), después el frontend. Si el frontend carga antes que el backend, las primeras requests van a dar 503.
- **Para mostrar el registro en PostgreSQL:** creá un usuario desde `/register` del frontend o desde opción "2. Registrarme" del CLI, luego mostrá `SELECT * FROM cliente ORDER BY id_cliente DESC LIMIT 5` en Supabase o con `psql`.
- El seed de datos (`Admin → Sistema → Cargar datos de prueba`) carga datos en las **5 bases simultáneamente** — es una buena demo del políglotico en acción.
