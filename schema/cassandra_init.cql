DROP TABLE IF EXISTS estado_pedido;

CREATE TABLE estado_pedido (
    id_pedido int,
    fecha_hora timestamp,
    estado text,
    observacion text,
    PRIMARY KEY (id_pedido, fecha_hora)
) WITH CLUSTERING ORDER BY (fecha_hora DESC);