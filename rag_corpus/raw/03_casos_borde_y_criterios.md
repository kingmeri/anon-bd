# 03 · Casos borde y criterios de decisión

Este documento define criterios prácticos para resolver **situaciones ambiguas** en la clasificación de columnas.  
Debe usarse junto con la guía principal de clasificación (`01_guia_clasificacion_columnas.md`).

---

## 1. Localización y direcciones

### 1.1. Direcciones completas

**Ejemplos de nombres de columna:**

- `direccion`, `direccion_completa`, `domicilio`, `calle_y_numero`, `direccion_residencia`

**Criterio:**

- Si la dirección incluye calle + número + municipio / código postal:
  - Tratar como **al menos** `cuasi_identificador`.
  - En contextos donde la dirección se usa directamente para localizar a la persona (p. ej., base de datos de domicilios, padrón, policía), se puede considerar `identificador_directo`.
- Regla práctica para el modelo:
  - Si el dataset parece de **gestión de personas / domicilios / policía / sanidad**, favorecer `identificador_directo`.
  - En otros casos genéricos, usar `cuasi_identificador` por defecto y explicarlo en el `rationale`.

### 1.2. Direcciones parciales

**Ejemplos:**

- `calle` sin número
- `barrio`, `distrito`, `zona`

**Criterio:**

- Tratar normalmente como `cuasi_identificador`, al aportar localización relativamente específica pero no única.
- Si la granularidad es muy alta (p. ej. `barrio` en una gran ciudad), pero no se combina con más datos, seguir considerándolo `cuasi_identificador`.

---

## 2. Matrículas y vehículos

### 2.1. Matrícula de vehículo

**Ejemplos:**

- `matricula`, `num_matricula`, `placa`, `licencia_vehiculo`

**Criterio:**

- En datasets policiales, de tráfico o donde se conoce que cada matrícula está asociada a un titular:
  - Tratar como `identificador_directo`.
- En datasets muy agregados (estadísticas anónimas, sin vínculo claro a personas físicas):
  - Se podría degradar a `cuasi_identificador`, pero el modelo debe ser conservador y explicar la decisión.

### 2.2. Datos técnicos de vehículo

**Ejemplos:**

- `modelo_vehiculo`, `marca_vehiculo`, `anio_matriculacion`, `tipo_combustible`

**Criterio:**

- Normalmente `no_sensible`, salvo que esté claramente vinculado a una persona identificable y el dataset sea de tipo policial / sancionador, en cuyo caso pueden ayudar a la reidentificación junto con otros campos → `cuasi_identificador`.

---

## 3. Campos de texto libre

### 3.1. Descripciones y notas

**Ejemplos:**

- `descripcion`, `observaciones`, `notas`, `comentarios`, `detalle_incidencia`

**Criterio general:**

- Aunque el nombre de la columna no sea específico, en muchos contextos de administración, sanidad o policía **estas columnas contienen datos personales mezclados** (nombres, situaciones, salud, etc.).
- Por defecto, si el contexto del dataset es policial, sanitario o de servicios sociales:
  - Clasificar como `atributo_sensible` o, como mínimo, `cuasi_identificador`, indicando en el `rationale` que puede contener datos personales variados.
- Si el contexto es puramente técnico o de logs y sabemos que el texto libre está sanitizado:
  - Se puede considerar `no_sensible`.

**Regla para el modelo:**

- Si no hay evidencia de sanitización previa y el dominio del dataset es sensible (salud, policía, servicios sociales, justicia, etc.), asumir que el texto puede contener datos sensibles → `atributo_sensible`.

---

## 4. Identificadores técnicos y hashes

### 4.1. Hashes de identificadores

**Ejemplos:**

- `hash_dni`, `hash_id_usuario`, `id_usuario_hash`, `pseudonimo`

**Criterio:**

- Aunque estén “hasheados”, si el hash se utiliza como clave estable para seguir a una persona en el sistema:
  - Tratar como `identificador_directo` (seudonimización, no anonimización).
- Si el hash se genera solo para una exportación puntual y no se reutiliza en otros sistemas (no siempre habrá forma de saberlo), el modelo debe ser conservador y asumir que **permite rastrear a la persona en ese dataset** → `identificador_directo`.

### 4.2. IDs de registro

**Ejemplos:**

- `id_registro`, `id_fila`, `row_id`

**Criterio:**

- Si apuntan a la **fila** y no a la persona (p. ej., hay múltiples filas por persona), se pueden tratar como `no_sensible`, porque no son identificadores personales directos.
- Si se usan claramente como clave de persona (ej. `id_cliente`, `id_paciente`), aplicar la guía general: `identificador_directo`.

---

## 5. Fechas y tiempos

### 5.1. Fechas de nacimiento

- Siempre `cuasi_identificador` (ver guía principal).

### 5.2. Fechas de eventos

**Ejemplos:**

- `fecha_compra`, `fecha_llamada`, `fecha_visita`, `fecha_incidencia`

**Criterio:**

- En general: `no_sensible`, salvo que la combinación de muchos campos temporales muy detallados pueda permitir seguimiento de una persona en un contexto muy específico.
- Si el evento está asociado a situaciones sensibles (p. ej. `fecha_delito`, `fecha_ingreso_psi`), la columna puede considerarse `atributo_sensible` por contexto.

### 5.3. Timestamps técnicos

**Ejemplos:**

- `fecha_creacion_registro`, `fecha_actualizacion`, `timestamp`

**Criterio:**

- Generalmente `no_sensible`, al ser metadatos técnicos.

---

## 6. Datos económicos

### 6.1. Importes y saldos

**Ejemplos:**

- `saldo_cuenta`, `importe_nomina`, `importe_prestacion`, `limite_credito`

**Criterio:**

- La información económica puede ser muy sensible en ciertos contextos (endeudamiento, morosidad, prestaciones).
- Sin embargo, en esta taxonomía, se suele tratar como:

  - `cuasi_identificador` si permite inferir mucho sobre la persona pero no encaja estrictamente en categorías especiales de GDPR.
  - `atributo_sensible` si se refiere a situaciones de **vulnerabilidad económica** (p. ej. prestacions sociales sensibles, morosidad grave, embargos).

### 6.2. Indicadores agregados

**Ejemplos:**

- `score_riesgo_crediticio`, `indice_vulnerabilidad`, `nivel_renta_segmento`

**Criterio:**

- Si derivan claramente de datos muy sensibles, tratarlos como `atributo_sensible`.
- Si son indicadores comerciales estándar sin connotaciones claras de vulnerabilidad, se pueden considerar `cuasi_identificador` o incluso `no_sensible` según el contexto.

---

## 7. Campos ambiguos o genéricos

### 7.1. Nombres genéricos: `dato1`, `campo_extra`, `valor`

**Criterio:**

- El nombre no aporta información.  
- Si hay ejemplos de valores, el modelo debe clasificarlos según su contenido real.
- Si no hay ejemplos y el contexto es sensible (sanidad, policía, justicia, servicios sociales), el modelo debe ser conservador:
  - Asumir que pueden contener información personal relevante → `cuasi_identificador` o `atributo_sensible` según la naturaleza del dataset.
  - Explicar esta decisión en el `rationale`.

### 7.2. Columnas mixtas

**Ejemplos:**

- `contacto` que a veces contiene teléfono, otras email, otras nombre + teléfono.

**Criterio:**

- Si en la práctica suele incluir identificadores directos (teléfono, email, nombre completo):
  - Clasificar como `identificador_directo`, aunque el nombre sea genérico.

---

## 8. Reglas de desempate

Cuando una columna parece encajar en varias categorías, se usará esta prioridad:

1. `identificador_directo`
2. `atributo_sensible`
3. `cuasi_identificador`
4. `no_sensible`

Ejemplos:

- `direccion_completa` en un dataset policial:
  - Puede verse como `cuasi_identificador`, pero se prefiere `identificador_directo` por la prioridad.
- `score_riesgo_crediticio` en un dataset financiero de morosidad:
  - Puede ser `cuasi_identificador` o `atributo_sensible`; si refleja una situación de vulnerabilidad → `atributo_sensible`.

El modelo debe **explicar siempre en el `rationale`** cuándo se aplica esta prioridad para desempatar.
