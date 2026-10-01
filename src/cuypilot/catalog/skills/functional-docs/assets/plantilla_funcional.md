# <Nombre del pipeline o modelo>

> Última actualización: <AAAA-MM-DD> · Código: `<ruta del módulo o notebook>`

## 1. Propósito

Qué problema de negocio resuelve y para quién, en un párrafo. [COMPLETAR si no se deduce del código]

## 2. Entradas

| Tabla / origen | Contenido | Filtros aplicados |
|---|---|---|
| `catalogo.esquema.tabla` | Qué representa cada fila | Ej.: solo últimos 12 meses |

## 3. Salidas

| Tabla / destino | Contenido | Granularidad | Modo de escritura |
|---|---|---|---|
| `catalogo.esquema.tabla` | Qué representa cada fila | Ej.: una fila por cliente y mes | Sobrescritura / incremental / merge |

## 4. Reglas de negocio

1. **<Nombre de la regla>:** descripción en lenguaje de negocio (qué se calcula, qué se excluye y por qué).
2. ...

## 5. Parámetros

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `fecha_proceso` | Fecha de corte de los datos | Día anterior |

## 6. Frecuencia y dependencias

- **Frecuencia:** [COMPLETAR: diaria / semanal / a demanda]
- **Depende de:** procesos o tablas que deben terminar antes.
- **Lo usan:** reportes, modelos o procesos que consumen la salida.

## 7. Calidad de datos y supuestos

- Validaciones que hace el proceso (nulos, duplicados, rangos).
- Supuestos sobre los datos de entrada.

## 8. Limitaciones conocidas

- Casos que el proceso no cubre o que trata de forma aproximada.

## 9. Responsables

| Rol | Persona / equipo |
|---|---|
| Dueño funcional | [COMPLETAR] |
| Dueño técnico | [COMPLETAR] |
