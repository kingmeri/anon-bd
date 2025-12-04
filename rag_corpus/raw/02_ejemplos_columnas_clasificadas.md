# 02 · Ejemplos de columnas clasificadas por categoría

Este documento proporciona ejemplos concretos de columnas típicas y su clasificación en:

- `identificador_directo`
- `cuasi_identificador`
- `atributo_sensible`
- `no_sensible`

El objetivo es servir de referencia rápida para personas y para el modelo LLM.  
Los ejemplos son ilustrativos; en casos reales se tendrá en cuenta también el contexto del dataset.

---

## 1. identificador_directo

Columnas que identifican directamente a una persona o la distinguen de forma unívoca en el dataset.

| name                    | data_type | ejemplos_valores                      | category             | rationale                                                                                 |
|-------------------------|----------:|---------------------------------------|----------------------|-------------------------------------------------------------------------------------------|
| dni                     | string    | 12345678A, 87654321Z                  | identificador_directo| DNI español, identificador oficial único por persona.                                     |
| nif                     | string    | 12345678H, B12345678                  | identificador_directo| Identificador fiscal para personas físicas y jurídicas.                                   |
| nie                     | string    | X1234567L                             | identificador_directo| Identificador oficial para extranjeros residentes.                                       |
| pasaporte               | string    | AA1234567                             | identificador_directo| Número de pasaporte, identificador oficial único.                                        |
| num_ss                  | string    | 281234567890                          | identificador_directo| Número de la Seguridad Social, único por persona.                                        |
| num_historia_clinica    | string    | HCL00012345                           | identificador_directo| Identificador interno único por paciente en el sistema sanitario.                        |
| id_cliente              | int       | 1001, 1002, 1003                      | identificador_directo| Clave interna única por cliente; permite seguir a la persona en el dataset.              |
| id_paciente             | int       | 501, 502                              | identificador_directo| Clave interna única por paciente; reidentificación directa en ese sistema.               |
| id_empleado             | int       | 2001, 2002                            | identificador_directo| Clave interna única por empleado.                                                        |
| nombre_completo         | string    | "María López Pérez"                   | identificador_directo| Nombre y apellidos completos; identifica directamente a la persona.                      |
| nombre_y_apellidos      | string    | "Juan García Gómez"                   | identificador_directo| Equivalente a nombre completo.                                                           |
| primer_apellido         | string    | "García"                              | identificador_directo| En muchos contextos, junto con otros campos, se usa para identificación directa.         |
| email                   | string    | maria@example.com                     | identificador_directo| Correo electrónico personal, suele ser único por persona.                                |
| correo_electronico      | string    | jgomez@empresa.com                    | identificador_directo| Equivalente a email.                                                                     |
| telefono_movil          | string    | +34600111222                          | identificador_directo| Número de móvil personal, normalmente único por persona.                                 |
| telefono_contacto       | string    | 600111222                             | identificador_directo| Campo de contacto telefónico personal.                                                   |
| iban                    | string    | ES7921000813610123456789              | identificador_directo| Cuenta bancaria personal, identificador financiero único.                                |
| matricula               | string    | 1234ABC                               | identificador_directo| En muchos contextos policiales, asociada directamente a un titular concreto.             |
| num_expediente_persona  | string    | EXP-2024-000123                       | identificador_directo| Código de expediente personal único.                                                     |
| usuario_login           | string    | mlopezp                               | identificador_directo| Identificador de usuario único en el sistema.                                            |

---

## 2. cuasi_identificador

Columnas que por sí solas no identifican directamente, pero ayudan mucho a reidentificar cuando se combinan con otras.

| name                      | data_type | ejemplos_valores                | category           | rationale                                                                                      |
|---------------------------|----------:|---------------------------------|--------------------|------------------------------------------------------------------------------------------------|
| fecha_nacimiento          | date      | 1998-05-12                      | cuasi_identificador| Fecha completa de nacimiento; combinada con otros datos reduce mucho el grupo posible.         |
| anio_nacimiento           | int       | 1980, 1995                      | cuasi_identificador| Año de nacimiento; menos preciso pero sigue aportando información identificativa.              |
| edad                      | int       | 23, 45                          | cuasi_identificador| Edad actual; dato demográfico clásico de cuasi-identificador.                                 |
| sexo                      | string    | "M", "F", "Otro"                | cuasi_identificador| Dato demográfico clave que, combinado con otros, ayuda a reidentificar.                       |
| genero                    | string    | "Hombre", "Mujer"               | cuasi_identificador| Similar a sexo.                                                                               |
| municipio_residencia      | string    | "Madrid", "Toledo"              | cuasi_identificador| Localización de residencia a nivel municipal.                                                  |
| ciudad                    | string    | "Barcelona"                     | cuasi_identificador| Localización de ciudad.                                                                        |
| provincia                 | string    | "Madrid", "Sevilla"             | cuasi_identificador| Localización a nivel provincial.                                                               |
| comunidad_autonoma        | string    | "Andalucía"                     | cuasi_identificador| Región amplia, pero igualmente informativa.                                                   |
| cod_postal                | string    | "28001", "08906"                | cuasi_identificador| Código postal; muy informativo para localización.                                             |
| pais_residencia           | string    | "España", "Francia"             | cuasi_identificador| País de residencia; menos preciso, pero relevante en ciertos contextos.                        |
| nacionalidad              | string    | "Española", "Italiana"          | cuasi_identificador| Dato demográfico relevante.                                                                   |
| profesion                 | string    | "Enfermera", "Policía"          | cuasi_identificador| Profesión; combinada con otras columnas puede aislar a individuos.                            |
| puesto_trabajo            | string    | "Jefe de sección"               | cuasi_identificador| Puesto laboral concreto.                                                                      |
| categoria_profesional     | string    | "Grupo A1", "Grupo C2"          | cuasi_identificador| Clasificación laboral; dato demográfico laboral.                                              |
| centro_trabajo            | string    | "Comisaría Distrito Centro"     | cuasi_identificador| Ubicación laboral; relevante combinada con otros datos.                                       |
| centro_salud_asignado     | string    | "CS Lavapiés"                   | cuasi_identificador| Ubicación asistencial asignada.                                                               |
| tipo_contrato             | string    | "Indefinido", "Temporal"        | cuasi_identificador| Información laboral que aporta contexto demográfico.                                          |
| estudios                  | string    | "Grado en Derecho"              | cuasi_identificador| Nivel formativo; dato demográfico.                                                            |
| idioma_principal          | string    | "Español", "Catalán"            | cuasi_identificador| Puede tener relevancia en combinación con origen y localización.                              |
| num_hijos                 | int       | 0, 1, 2                         | cuasi_identificador| Información familiar.                                                                          |

---

## 3. atributo_sensible

Columnas especialmente protegidas (salud, penal, orientación, religión, etc.) o que reflejan situaciones de vulnerabilidad.

| name                       | data_type | ejemplos_valores                          | category          | rationale                                                                                         |
|----------------------------|----------:|-------------------------------------------|-------------------|---------------------------------------------------------------------------------------------------|
| diagnostico_principal      | string    | "Diabetes tipo 2", "Depresión mayor"      | atributo_sensible | Información de salud directamente identificable como categoría especial de datos.                |
| diagnostico_secundario     | string    | "Hipertensión", "Ansiedad"                | atributo_sensible | Igual que el anterior.                                                                           |
| enfermedad_cronica         | string    | "EPOC", "Esclerosis múltiple"             | atributo_sensible | Enfermedades crónicas: datos de salud.                                                           |
| tratamiento_farmacologico  | string    | "Metformina", "ISRS"                      | atributo_sensible | Datos sobre medicación y tratamiento médico.                                                     |
| grado_discapacidad         | int       | 33, 65                                    | atributo_sensible | Indica discapacidad reconocida, dato especialmente protegido.                                   |
| estado_salud_general       | string    | "Grave", "Leve", "Estable"                | atributo_sensible | Información sanitaria.                                                                           |
| antecedentes_penales       | string    | "Robo con fuerza", "Delito leve"          | atributo_sensible | Información sobre historial penal.                                                               |
| tipo_delito                | string    | "Tráfico de drogas", "Lesiones"           | atributo_sensible | Datos relativos a infracciones penales.                                                          |
| situacion_penal            | string    | "En libertad condicional"                 | atributo_sensible | Situación procesal o penitenciaria.                                                              |
| sancion_impuesta           | string    | "Multa de 600€", "Localización permanente"| atributo_sensible | Detalle de sanciones penales o administrativas graves.                                          |
| afiliacion_sindical        | string    | "Sindicato X"                             | atributo_sensible | Dato sobre afiliación sindical, categoría especial GDPR.                                        |
| afiliacion_politica        | string    | "Partido Y"                               | atributo_sensible | Opinión / afiliación política.                                                                  |
| religion                   | string    | "Católica", "Musulmana", "Atea"           | atributo_sensible | Creencias religiosas o filosóficas.                                                             |
| orientacion_sexual         | string    | "Homosexual", "Heterosexual", "Bisexual"  | atributo_sensible | Dato relativo a vida sexual u orientación sexual.                                               |
| victima_violencia_genero   | bool      | true/false                                | atributo_sensible | Indica condición de víctima de violencia de género, situación de vulnerabilidad extrema.        |
| nivel_dependencia          | string    | "Grado I", "Grado II"                     | atributo_sensible | Grado de dependencia, información sanitaria/social sensible.                                    |
| ingreso_minimo_vital       | bool      | true/false                                | atributo_sensible | Indica percepción de prestación social sensible.                                                |
| plantilla_biometrica       | string    | (hash biométrico)                         | atributo_sensible | Datos biométricos usados para identificación (huellas, rostro, etc.).                          |
| dato_genetico              | string    | "Mutación BRCA1+"                         | atributo_sensible | Datos genéticos vinculados a la persona.                                                        |
| evaluacion_psicologica     | string    | "Ansiedad moderada", "Sin rasgos patológicos"| atributo_sensible| Informe psicológico o de salud mental.                                                          |

---

## 4. no_sensible

Columnas que no identifican directamente, ni son cuasi-identificadores relevantes, ni contienen información especialmente sensible.

| name                     | data_type | ejemplos_valores                       | category    | rationale                                                                                   |
|--------------------------|----------:|----------------------------------------|------------|---------------------------------------------------------------------------------------------|
| importe_compra           | float     | 123.45, 59.99                          | no_sensible | Importe de una transacción, sin identificación directa de la persona.                      |
| importe_venta            | float     | 2500.00, 899.90                        | no_sensible | Similar al anterior.                                                                       |
| tipo_producto            | string    | "Seguro hogar", "Tarjeta crédito"      | no_sensible | Características del producto, no de la persona.                                            |
| categoria_producto       | string    | "Electrónica", "Ropa"                  | no_sensible | Clasificación de producto.                                                                 |
| descripcion_producto     | string    | "Portátil 15 pulgadas"                 | no_sensible | Descripción de un objeto, no de la persona.                                               |
| fecha_operacion          | date      | 2024-03-10                             | no_sensible | Fecha de una transacción; en sí misma no identifica al sujeto.                             |
| id_registro              | int       | 1, 2, 3                                | no_sensible | Identificador de la fila/registro, no de la persona (puede ser distinto de id_persona).    |
| codigo_error             | string    | "ERR_01", "TIMEOUT"                    | no_sensible | Código técnico, no relacionado con los datos personales.                                   |
| version_app              | string    | "v1.2.3"                               | no_sensible | Versión de la aplicación usada.                                                            |
| canal_venta              | string    | "Online", "Presencial", "Telefónico"   | no_sensible | Canal de comercialización.                                                                 |
| tipo_operacion           | string    | "Alta", "Baja", "Modificación"         | no_sensible | Tipo de operación sobre un expediente o servicio.                                         |
| categoria_incidencia     | string    | "Técnica", "Comercial", "Información"  | no_sensible | Clasificación interna de incidencias.                                                      |
| prioridad_incidencia     | string    | "Alta", "Media", "Baja"                | no_sensible | Grado de prioridad interna de un ticket.                                                   |
| estado_expediente        | string    | "Abierto", "Cerrado", "En estudio"     | no_sensible | Estado del expediente, sin datos directos de la persona.                                  |
| fecha_creacion_registro  | datetime  | 2024-01-10T15:34:21                    | no_sensible | Timestamp técnico de creación.                                                             |
| fecha_actualizacion      | datetime  | 2024-02-05T09:12:00                    | no_sensible | Timestamp de actualización.                                                                |
| source_system            | string    | "CRM", "ERP", "WEB"                    | no_sensible | Sistema origen del dato.                                                                   |
| cod_oficina              | string    | "001", "275"                           | no_sensible | Código de oficina/centro, sin identificar a individuos concretos por sí solo.             |
| indicador_test           | bool      | true/false                             | no_sensible | Flag técnico para marcar datos de prueba.                                                  |
| version_reglamento       | string    | "GDPR_2016", "LOPDGDD_2018"            | no_sensible | Referencias normativas generales, no personales.                                           |

---

Estos ejemplos se utilizan como referencia en el RAG.  
Cuando el modelo dude sobre una columna real, puede buscar en este documento casos similares y aplicar la misma lógica.
