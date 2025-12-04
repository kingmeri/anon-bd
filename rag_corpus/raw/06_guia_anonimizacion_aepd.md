# 06 – Guía básica de anonimización (AEPD/PDPC) aplicada a columnas de BBDD

## 1. Contexto y alcance

La guía básica de anonimización, traducida y publicada por la AEPD, se centra en:

- Datos **estructurados**: tablas, hojas de cálculo, bases de datos relacionales.
- Datos **textuales** sencillos (números, fechas, texto plano).
- Casos de uso típicos de intercambio interno y externo de datos, y retención a largo plazo.

Esto encaja perfectamente con tu escenario de **columnas de bases de datos**.

## 2. Anonimización vs desidentificación

La guía distingue:

- **Desidentificación**: eliminación de identificadores directos (nombre, dirección postal, número de documento, etc.).  
  Es solo el **primer paso**, y NO garantiza anonimato pleno.
- **Anonimización**: proceso basado en el riesgo que combina:
  - Técnicas de anonimización sobre los datos.
  - Salvaguardas adicionales para evitar reidentificación.
- **Reidentificación**: volver a identificar a individuos en un conjunto de datos que había sido desidentificado o anoninizado (por ejemplo, mediante vinculación con otras fuentes).

Punto clave para tu modelo:

- Columnas con identificadores directos juegan un papel fundamental en la **desidentificación**.
- Columnas que son cuasi-identificadores son críticas en el control del **riesgo de reidentificación**.

## 3. Paso 1 – Conozca sus datos: tipos de atributos en un registro

La guía propone ver cada registro como compuesto por:

- **Identificadores directos**: permiten identificar inmediatamente al individuo.
- **Identificadores indirectos o seudoidentificadores**: no identifican por sí solos, pero sí en combinación (edad, código postal, profesión, etc.).
- **Atributos objetivo**: variables de interés analítico (p.ej., resultado de un test, consumo mensual, etc.) que preferimos no distorsionar salvo que generemos datos sintéticos.

Esto está totalmente alineado con tus cuatro categorías:

- `identificador_directo` ↔ identificadores directos.
- `cuasi_identificador` ↔ identificadores indirectos/seudoidentificadores.
- `atributo_sensible` ↔ atributos que, además, encajan en categorías sensibles RGPD.
- `no_sensible` ↔ atributos que no permiten identificar ni son sensibles.

## 4. Paso 2 – Desidentificar: tratamiento de identificadores directos

La guía recomienda que, para identificadores directos, normalmente se aplique:

- **Supresión** del atributo (eliminar la columna o su contenido).
- **Seudonimización**:
  - Reemplazar valores por identificadores aleatorios únicos.
  - Mantener, si es necesario, una tabla de correspondencia de identidad **muy protegida**.

Ejemplos de identificadores directos típicos:
- Nombre, dirección de correo electrónico, número de teléfono móvil.
- Número de documento nacional de identidad, pasaporte, número de cuenta, etc.

Para la clasificación de columnas:

- Todo lo que encaje en esta lista debería tender a `identificador_directo`.
- Estas columnas suelen ser las primeras candidatas a:
  - Supresión completa.
  - O seudonimización si se necesita trazabilidad.

## 5. Paso 3 – Técnicas de anonimización sobre identificadores indirectos/cuasi-identificadores

La guía detalla varias técnicas, especialmente útiles para columnas que tu modelo marcará como `cuasi_identificador`:

### 5.1 Generalización

Consiste en reemplazar valores concretos por rangos o categorías más amplias.  
Ejemplos típicos:

- Edad → rangos: 21–25, 26–30, 31–35…
- Peso, altura → rangos de 5 o 10 unidades.
- Dirección → nivel de calle → barrio → ciudad → provincia.

Uso en tu contexto:

- Columnas como `edad`, `codigo_postal`, `direccion`, `fecha_nacimiento` pueden requerir generalización para reducir el riesgo de reidentificación.
- El modelo puede ayudar a priorizar estas columnas como `cuasi_identificador`.

### 5.2 Intercambio (shuffling)

Reorganiza los valores de una columna entre registros, de forma que:
- Los valores aparecen en el conjunto de datos.
- Pero ya no están asociados a las personas originales.

Es útil cuando:
- El análisis solo requiere estadísticas agregadas a nivel de atributo (distribuciones, medias, etc.), no la relación exacta entre atributos por individuo.

### 5.3 Perturbación de datos

Modifica ligeramente los valores (sobre todo numéricos/fechas) para reducir identificabilidad:

- Redondeo.
- Añadir ruido aleatorio.

Aplicable a:
- Columnas como `importe`, `numero_visitas`, `edad`, `dias_estancia`, cuando pequeñas variaciones no afectan al análisis.

### 5.4 Datos sintéticos

- Se aplican transformaciones fuertes para generar registros artificiales sin correspondencia con individuos reales.
- Útiles para desarrollo y pruebas de software, menos adecuados para entrenar modelos de IA si se destruye excesivamente la estructura original.

En tu proyecto:

- Podríais utilizar datos sintéticos para entornos de desarrollo.
- El modelo de clasificación os indica qué columnas, por su nivel de riesgo, merecen transformaciones más agresivas.

## 6. Paso 4 – Cálculo del riesgo: k-anonimidad

La guía propone usar **k-anonimidad** para estimar el riesgo de reidentificación:

- Se agrupan registros que son **idénticos en los identificadores indirectos**.
- El valor de `k` es el tamaño del grupo más pequeño:
  - k = 1 → registro único → muy alto riesgo.
  - k = 3 o 5 → umbrales sugeridos como aceptables.
- Umbrales diferentes según:
  - Intercambio interno de datos.
  - Intercambio externo.
  - Retención a largo plazo.

Relación con tu modelo:

- Las columnas marcadas como `cuasi_identificador` por el LLM son exactamente las que entran en el cálculo de k-anonimidad.
- Cuantos más cuasi-identificadores muy granulares combinéis, más probable que aparezcan registros únicos.

## 7. Paso 5 – Gestión de riesgos de reidentificación y revelación

La guía insiste en:

- Documentar el proceso de anonimización (técnicas, parámetros) y proteger esa documentación.
- Considerar distintos tipos de riesgo:
  - **Revelación de identidad** (se identifica a una persona concreta).
  - **Revelación de atributos** (se infiere un atributo sensible sobre una persona aunque el registro no sea único).
- Analizar escenarios de brechas de datos:
  - Pérdida solo de datos anonimizados.
  - Pérdida solo de tabla de correspondencia.
  - Pérdida de ambos conjuntamente.

Para la clasificación de columnas:

- Columnas etiquetadas como `atributo_sensible` combinadas con `cuasi_identificador` elevan mucho el riesgo de revelación de atributos, incluso si no se conoce el identificador directo.
- Esto justifica aplicar:
  - Técnicas fuertes (generalización agresiva, perturbación, supresión).
  - Controles legales y contractuales cuando se comparten datos anonimizados con terceros.

## 8. Anexo práctico: mapeo columnas ↔ categoría modelo ↔ técnicas sugeridas

### 8.1 identificador_directo

Ejemplos de columnas:
- `nombre`, `apellidos`, `nombre_completo`
- `dni`, `nie`, `nif`, `num_pasaporte`
- `telefono_movil`, `email_personal`, `direccion_postal`

Técnicas típicas:
- Supresión de columna o valor.
- Seudonimización (ID aleatorios, tablas de correspondencia protegidas).
- Enmascaramiento parcial (para usos muy concretos, p.ej., mostrar solo últimos dígitos).

### 8.2 cuasi_identificador

Ejemplos:
- `fecha_nacimiento`, `edad`, `codigo_postal`, `municipio`, `provincia`
- `sexo`, `profesion`, `categoria_profesional`
- Cualquier atributo que, en combinación con otros, haga a la persona fácilmente identificable.

Técnicas:
- Generalización (rangos de edad, zonas geográficas amplias).
- Perturbación de datos (redondeo, ruido).
- Intercambio/shuffling cuando solo se necesitan estadísticas a nivel de atributo.

### 8.3 atributo_sensible

Ejemplos:
- Columnas de salud: `diagnostico`, `enfermedad`, `tratamiento`, `discapacidad`, `icd_code`
- Columnas ideológicas o íntimas: `religion`, `orientacion_sexual`, `afiliacion_sindical`, `origen_etnico`

Técnicas:
- Combinación de:
  - Fuerte generalización o agrupación en categorías amplias.
  - Perturbación si tiene sentido.
  - Supresión cuando el uso no justifica el riesgo.

### 8.4 no_sensible

Ejemplos:
- Variables puramente técnicas u operativas: `version_app`, `id_servidor` (sin vínculo a usuario), métricas de sistema.
- Datos ya agregados y no reidentificables.

Técnicas:
- En general, pueden conservarse tal cual.
- Aun así, conviene revisar si combinaciones inesperadas con otras columnas podrían convertirlas en cuasi-identificadores.

## 9. Cómo usar esta guía en tu RAG

En el flujo RAG:

1. Recuperar fragmentos de esta guía cuando:
   - El modelo dude entre `identificador_directo` y `cuasi_identificador`.
   - Aparezcan columnas de salud, ideología, etc., para reforzar la noción de `atributo_sensible`.
2. Utilizar secciones sobre:
   - Clasificación de atributos (directos/indirectos/objetivo).
   - Técnicas de anonimización según tipo de atributo.
3. Dar contexto normativo y práctico a Ollama para que la clasificación:
   - Sea coherente con RGPD + AEPD.
   - Tenga una base de “riesgo de reidentificación”, no solo de intuición semántica.

