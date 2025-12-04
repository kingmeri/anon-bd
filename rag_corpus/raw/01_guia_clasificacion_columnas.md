# Guía de clasificación de columnas para anonimización (TFG)

## 1. Objetivo de este documento

Este documento define **cómo clasificar columnas de bases de datos tabulares** en las siguientes categorías:

- `identificador_directo`
- `cuasi_identificador`
- `atributo_sensible`
- `no_sensible`

La guía está pensada para que la utilicen:

- Personas que anotan / revisan datos.
- El modelo LLM que usamos para clasificar columnas automáticamente.

Las decisiones de clasificación se basarán en:

- El **nombre de la columna**.
- El **tipo de dato**.
- Ejemplos de **valores** de la columna (si están disponibles).
- El **contexto legal y técnico** de la anonimización (GDPR, AEPD, etc.).

## 2. Categorías y definiciones operativas

### 2.1. `identificador_directo`

**Definición operativa**  
Columna cuyo contenido permite **identificar de forma directa y unívoca** a una persona concreta **sin necesidad de combinarla** con otras columnas ni con fuentes externas complejas.

Suelen ser identificadores como:

- Nombre y apellidos completos (especialmente si incluyen ambos apellidos).
- DNI, NIE, pasaporte, número de documento de identidad.
- Número de seguridad social.
- Número de historia clínica.
- IBAN u otros identificadores bancarios personales.
- Correos electrónicos personales claramente identificables (ej. `nombre.apellido@`, `dni@`).
- Teléfonos personales (móvil, fijo) cuando son de una persona concreta.
- Matrículas de vehículos asociadas directamente a una persona, cuando ese hecho se conoce en el contexto.

**Heurísticas**:

- Si la columna por sí sola suele apuntar a “una persona concreta única” → `identificador_directo`.
- Si la columna parece una **clave técnica** que es única por persona (ej. `id_cliente`, `id_paciente`) aunque no sea un identificador “del mundo real”, aquí decidimos tratarla también como `identificador_directo`, porque permite reidentificar a la persona en ese dataset.

**Ejemplos de nombre de columna**:

- `dni`, `NIF`, `num_documento`, `documento_identidad`
- `nombre`, `nombre_completo`, `nombre_y_apellidos`
- `id_cliente`, `id_usuario`, `id_paciente`, `id_empleado`
- `email`, `correo_electronico`, `telefono`, `movil`, `telefono_contacto`
- `num_ss`, `nss`, `num_historia_clinica`
- `iban`, `cuenta_bancaria`

---

### 2.2. `cuasi_identificador`

**Definición operativa**  
Columna que **no identifica por sí sola de forma directa**, pero que:

- combinada con otras columnas del mismo dataset, o
- combinada con fuentes externas razonablemente accesibles,

puede llevar a identificar a una persona concreta o reducir mucho el grupo de posibles personas.

Suelen ser atributos como:

- Datos de localización: municipio, distrito, código postal, dirección parcial.
- Datos demográficos: fecha de nacimiento, edad exacta, sexo, nacionalidad.
- Datos laborales genéricos: categoría profesional, departamento, tipo de contrato si combinados con otros.
- Identificadores internos que no son únicos pero son muy informativos.

**Heurísticas**:

- Si la columna se parece a: **localización, demografía, características personales no extremas** → candidata a `cuasi_identificador`.
- Si la columna por sí sola no basta para identificar, pero “combinada con 1–2 columnas más” podría aislar a una persona (ej. `fecha_nacimiento + municipio + sexo`) → `cuasi_identificador`.
- Si dudas entre `cuasi_identificador` y `no_sensible`, y contiene información sobre la persona (no sobre el sistema), preferir `cuasi_identificador`.

**Ejemplos de nombre de columna**:

- `fecha_nacimiento`, `edad`, `anio_nacimiento`
- `sexo`, `genero`
- `municipio`, `ciudad`, `provincia`, `region`, `cod_postal`
- `profesion`, `categoria_profesional`, `puesto_trabajo`, `departamento`
- `nacionalidad`, `pais_residencia`
- `centro_salud_asignado`, `colegio`, `centro_trabajo` (sin identificador directo asociado)

---

### 2.3. `atributo_sensible`

**Definición operativa**  
Columna que contiene información especialmente protegida o muy intrusiva sobre la persona, por ejemplo:

- Salud física o mental, discapacidad.
- Datos genéticos o biométricos.
- Opiniones políticas, afiliación sindical.
- Religión, creencias filosóficas.
- Vida sexual u orientación sexual.
- Datos sobre infracciones administrativas o penales.
- Información económica muy detallada o situaciones de vulnerabilidad (ej. prestaciones sociales sensibles).

**Heurísticas**:

- Si el contenido entra en las **categorías especiales de datos** del GDPR (salud, religión, política, etc.) → `atributo_sensible`.
- Si la columna revela **situaciones de riesgo o vulnerabilidad** (violencia de género, programas de protección, enfermedades graves) → `atributo_sensible`.
- Si la columna describe **infracciones, sanciones, antecedentes** → `atributo_sensible`.

**Ejemplos de nombre de columna**:

- Salud:
  - `diagnostico_principal`, `enfermedad`, `patologia`, `tratamiento`, `grado_discapacidad`
- Datos penales:
  - `antecedentes_penales`, `tipo_delito`, `sancion`, `situacion_penal`
- Política / religión / orientación:
  - `afiliacion_sindical`, `afiliacion_politica`, `religion`, `confesion_religiosa`
  - `orientacion_sexual`
- Situaciones de vulnerabilidad:
  - `victima_violencia_genero`, `nivel_dependencia`, `perceptor_renta_insercion`
- Otros:
  - `huella_dactilar_hash`, `plantilla_biometrica`, `dato_genetico`

---

### 2.4. `no_sensible`

**Definición operativa**  
Columna que:

- No permite identificar de forma directa, ni
- constituye un cuasi-identificador relevante, ni
- contiene información especialmente sensible sobre la persona.

Suelen ser:

- Datos puramente técnicos o de sistema.
- Atributos agregados que ya no apuntan a individuos.
- Información de negocio que no se refiere directamente a la persona (ej. características del producto, códigos internos de proceso, etc.).

**Heurísticas**:

- Si la columna describe características de **un objeto, producto, transacción** y no de la persona → `no_sensible`.
- Si la columna es un **flag o código interno** sin relación clara con la persona → `no_sensible`.
- Si aún así hay duda, pero no hay forma razonable de usarla para reidentificar (ni combina bien con otras para aislar a una persona) → `no_sensible`.

**Ejemplos de nombre de columna**:

- Datos de producto / operación:
  - `importe_compra`, `importe_venta`, `tipo_producto`, `categoria_producto`
  - `fecha_operacion` (cuando no se asocia directamente a una persona concreta).
- Datos técnicos:
  - `id_registro`, `hash_registro`, `timestamp_insercion`
  - `codigo_error`, `version_app`, `num_intentos`
- Otros:
  - `descripcion_incidente` cuando está suficientemente anonimizada y sin detalles personales.

---

## 3. Principios generales de decisión

Estas reglas se aplican tanto a personas humanas como al modelo:

1. **Siempre asignar EXACTAMENTE UNA categoría por columna.**
2. **Regla de prioridad (de más a menos “fuerte”):**

   Si una columna podría encajar en varias categorías, aplicar esta prioridad:

   1. `identificador_directo`
   2. `atributo_sensible`
   3. `cuasi_identificador`
   4. `no_sensible`

   Ejemplo:
   - Una columna `matricula_vehiculo` que se usa como identificador único de persona en un contexto concreto:
     - Mejor tratarla como `identificador_directo`.

3. Si existe duda entre `cuasi_identificador` y `no_sensible`:
   - Preferir `cuasi_identificador` **si la columna describe una característica de la persona** (edad, zona de residencia, etc.).
   - Preferir `no_sensible` si describe solo características de productos, procesos o aspectos técnicos.

4. Si el nombre de la columna es ambiguo:
   - Usar los ejemplos de valores (cuando estén disponibles).
   - Si aun así no está claro, escoger la categoría **más protectora** (por ejemplo `cuasi_identificador` antes que `no_sensible`) y explicarlo en el `rationale`.

---

## 4. Ejemplos resumidos por categoría

Aquí se listan algunos ejemplos típicos (ver documento `02_ejemplos_columnas_clasificadas.md` para más detalle):

- `identificador_directo`:
  - `dni`, `id_cliente`, `nombre_completo`, `email`, `telefono_movil`, `num_ss`
- `cuasi_identificador`:
  - `fecha_nacimiento`, `edad`, `cod_postal`, `municipio`, `provincia`, `profesion`
- `atributo_sensible`:
  - `diagnostico_principal`, `afiliacion_sindical`, `religion`, `antecedentes_penales`, `orientacion_sexual`
- `no_sensible`:
  - `importe_compra`, `tipo_producto`, `id_registro_interno`, `timestamp_alta`, `codigo_error`

---

## 5. Casos especiales y criterios prácticos

### 5.1. Claves técnicas (`id_*`)

- Si una clave técnica permite reconstruir o seguir a una persona en el dataset (ej. `id_cliente`, `id_paciente`), la tratamos como `identificador_directo` **aunque no sea un identificador del “mundo real”**.

### 5.2. Nombres parciales o iniciales

- `inicial_nombre`, `inicial_apellido`:
  - Si claramente se usan como alternativa al nombre completo → `cuasi_identificador`.
- `alias`, `apodo`:
  - Si el alias identifica a la persona dentro del sistema → `identificador_directo`.

### 5.3. Localización muy precisa

- `direccion_completa`, `latitud`, `longitud`, `coordenadas_gps`:
  - Tratar como `identificador_directo` o `cuasi_identificador` según el contexto; en caso de duda, `cuasi_identificador` como mínimo.

### 5.4. Datos derivados o agregados

- `indice_riesgo`, `score_crediticio`:
  - Si se obtiene a partir de datos sensibles (ej. salud, penales), suele ser prudente tratarlos como `atributo_sensible`.
  - Si solo reflejan comportamiento de compra despersonalizado → valorar entre `cuasi_identificador` o `no_sensible` según el grado de detalle.

---

## 6. Cómo debe usar esta guía el modelo LLM

Cuando el modelo reciba una lista de columnas, debe:

1. Leer la definición de cada categoría en esta guía.
2. Para cada columna:
   - Analizar el nombre.
   - Tener en cuenta el tipo de dato.
   - Cuando haya ejemplos de valores, usarlos para clarificar el significado.
3. Aplicar la **regla de prioridad** cuando una columna pueda encajar en varias categorías.
4. Devolver un JSON con:
   - `name`: nombre de la columna tal como aparece en la entrada.
   - `category`: una de `identificador_directo`, `cuasi_identificador`, `atributo_sensible`, `no_sensible`.
   - `rationale`: 2–3 frases breves explicando la decisión, mencionando si se ha aplicado la prioridad o si hay duda.
   - `confidence`: número entre 0.0 y 1.0 que represente su seguridad (alta si es un caso muy típico, más baja en casos ambiguos).

Este documento se utilizará como **contexto principal en el RAG**, por lo que el modelo debe seguir estas definiciones incluso si su conocimiento general difiere.
