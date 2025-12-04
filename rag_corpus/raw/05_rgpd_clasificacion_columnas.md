# 05 – RGPD y clasificación de columnas de datos

## 1. Alcance del RGPD

El RGPD se aplica al tratamiento de **datos personales** de personas físicas identificadas o identificables, tanto si el tratamiento es automatizado como si forma parte de un fichero estructurado.

No se aplica a:
- Datos de personas jurídicas (nombre de la empresa, forma jurídica, datos de contacto corporativos).
- Información realmente anónima, donde ya no es posible identificar a una persona física por ningún medio razonable.

Esto es importante porque:
- Columnas que solo contienen información puramente agregada o anónima podrían clasificarse como **no_sensible**.
- Columnas que se pueden vincular, directa o indirectamente, a una persona física caen dentro del ámbito del RGPD.

## 2. Definición de dato personal (para guiar al modelo)

**Dato personal** ≈ cualquier información sobre una persona física identificada o identificable.  
Se considera que una persona es identificable si puede ser identificada, directa o indirectamente, mediante:

- Un identificador como:
  - Nombre y apellidos
  - Número de documento de identidad (DNI/NIE/pasaporte)
  - Número de cliente/afiliado expedido por una entidad
  - Datos de localización
  - Identificadores en línea (cookies, identificadores de dispositivo, etc.)
- O uno o varios elementos propios de la identidad física, fisiológica, genética, psíquica, económica, cultural o social.

Puntos clave para el modelo de columnas:

- Una columna que por sí sola identifique claramente a la persona (p.ej., `dni`, `num_afiliado`, `correo_personal`) debe tender a **identificador_directo**.
- Columnas que no identifican por sí solas, pero sí **en combinación** con otras (p.ej., `fecha_nacimiento`, `código_postal`, `sexo`) son candidatas a **cuasi_identificador**.

## 3. Categorías especiales de datos (atributos sensibles)

El RGPD define ciertas categorías de datos especialmente sensibles, cuyo tratamiento está en principio prohibido salvo excepciones. Son, entre otros:

- Datos que revelen:
  - Origen racial o étnico
  - Opiniones políticas
  - Convicciones religiosas o filosóficas
  - Afiliación sindical
- Datos:
  - Genéticos
  - Biométricos dirigidos a identificar de manera unívoca a una persona
  - Relativos a la salud
  - Relativos a la vida sexual u orientación sexual

Para la clasificación de columnas:

- Cualquier columna que contenga información claramente encajable aquí (ej. `diagnostico`, `enfermedad_principal`, `religion`, `orientacion_sexual`, `afiliacion_sindical`) debe inclinarse hacia **atributo_sensible**.
- Aunque un dato sensible esté codificado (p.ej., `dx_code`, `icd10_code`), si su semántica es claramente de salud, también debe clasificarse como **atributo_sensible**.

## 4. Anonimización y seudonimización según RGPD

### 4.1 Información anónima

- Información que **no guarda relación** con una persona física identificada o identificable.
- O datos que se han convertido en anónimos de forma que el interesado **no sea identificable** (ni siquiera con medios razonables).

Estos datos quedan **fuera del ámbito del RGPD**.

En tu clasificación:

- Columnas con datos generados sintéticamente o irreversiblemente anonimizados (sin posibilidad razonable de reidentificación) pueden mapearse a **no_sensible**, aunque su “tema” original fuera sensible.

### 4.2 Seudonimización

La seudonimización reduce el vínculo directo con la identidad, pero **no deja de ser tratamiento de datos personales** si existe información adicional (tabla de correspondencia, claves, etc.) que permita volver a identificar.

Ejemplos típicos:
- Reemplazar `dni` por un identificador interno reversible (`id_paciente`, `id_cliente`) con tabla de mapeo.
- Hashes o tokens que pueden revertirse o vincularse mediante información auxiliar.

Para el modelo:

- Columnas que contengan seudónimos que aún pueden vincularse a una persona (porque la organización conserva el mapeo) deberían seguir tratándose como:
  - **identificador_directo**, si el seudónimo funciona como ID estable y único de la persona en la BBDD.
  - O **cuasi_identificador**, si funciona más como atributo que en combinación permite reidentificar.

## 5. Principios del RGPD que justifican tu taxonomía

Los principios más relevantes:

- **Minimización de datos**: los datos deben ser adecuados, pertinentes y limitados a lo necesario.
- **Limitación de la finalidad**: los datos se recogen con fines determinados, explícitos y legítimos.
- **Integridad y confidencialidad**: los datos deben tratarse de forma que se garantice su seguridad.

Tu clasificación de columnas en:
- `identificador_directo`
- `cuasi_identificador`
- `atributo_sensible`
- `no_sensible`

es coherente con estos principios porque:

1. Permite decidir qué columnas requieren **medidas de protección más fuertes**.
2. Ayuda a decidir qué columnas deberían ser **anonimizadas, seudonimizadas o suprimidas** según el contexto.
3. Facilita justificar el diseño de medidas técnicas y organizativas (p.ej., aplicar técnicas más agresivas a atributos sensibles o altamente identificables).

## 6. Guía práctica para el modelo (vista RGPD)

### 6.1 Preguntas que el modelo debe “hacerse” implícitamente

Dado el **nombre de la columna** y el **tipo de dato**:

1. **¿Esta columna identifica directamente a una persona?**  
   - Si la respuesta es sí → `identificador_directo`.
2. **Si no la identifica directamente, ayuda a identificarla combinada con otras columnas típicas?**  
   - Si sí → `cuasi_identificador`.
3. **¿La información pertenece a una de las categorías especiales o revela aspectos muy íntimos de la persona?**  
   - Si sí → `atributo_sensible`.
4. **¿La información está claramente fuera del ámbito del RGPD o es puramente técnica/operacional sin enlace a una persona?**  
   - Si sí → `no_sensible`.

### 6.2 Ejemplos de mapeo orientativo

- `dni`, `nie`, `nif`, `passport_number`, `num_seguridad_social`, `id_cliente` (si es el identificador principal) → `identificador_directo`.
- `nombre`, `apellidos`, `nombre_completo`, `email_personal`, `telefono_movil` → `identificador_directo`.
- `fecha_nacimiento`, `codigo_postal`, `municipio`, `provincia`, `sexo`, `profesion`, `situacion_laboral` → normalmente `cuasi_identificador`.
- `diagnostico`, `enfermedad`, `tratamiento`, `discapacidad`, `religion`, `orientacion_sexual`, `origen_etnico` → `atributo_sensible`.
- `importe_compra`, `numero_linea_factura`, `timestamp_log`, `version_app`, `id_servidor` (si no se vincula a una persona) → candidatos a `no_sensible` (dependiendo del contexto).

