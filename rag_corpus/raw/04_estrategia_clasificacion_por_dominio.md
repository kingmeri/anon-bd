# 04 · Estrategia de clasificación por dominio de dataset

Este documento proporciona pautas específicas según el **dominio del dataset**, para ayudar a la clasificación de columnas en:

- `identificador_directo`
- `cuasi_identificador`
- `atributo_sensible`
- `no_sensible`

El modelo LLM debe usar este documento cuando reciba información sobre el tipo de base de datos (sanitaria, policial, financiera, etc.).

---

## 1. Dominios considerados

Los dominios principales que se contemplan son:

1. **Sanitario / Salud**
2. **Policial / Seguridad / Justicia**
3. **Servicios sociales / Bienestar social**
4. **Financiero / Bancario / Seguros**
5. **RRHH / Empleo / Gestión de personal**
6. **Marketing / CRM / Comercial**
7. **Administración general / Tramitación administrativa**

Si el dominio no está claro, aplicar la estrategia de **“dominio desconocido”** (ver sección 8).

---

## 2. Dominio sanitario / salud

### 2.1. Identificadores directos típicos

- `num_historia_clinica`, `id_paciente`, `dni`, `nombre_completo`, `telefono`, `email`
- Cualquier identificador interno de paciente que permita seguirle en el sistema → `identificador_directo`.

### 2.2. Atributos sensibles

En salud, muchos campos son directamente `atributo_sensible`:

- Diagnósticos: `diagnostico_principal`, `diagnostico_secundario`
- Medicación y tratamiento: `tratamiento`, `medicacion`, `farmaco`
- Información sobre discapacidad o dependencia: `grado_discapacidad`, `nivel_dependencia`
- Resultados de pruebas: `resultado_analitica`, `resultado_prueba_imagen`
- Observaciones médicas: `informe_clinico`, `nota_medica`, `evolucion_enfermeria`
- Datos sobre salud mental: `diagnostico_psiquiatrico`, `evaluacion_psicologica`

### 2.3. Cuasi-identificadores frecuentes

- Datos demográficos: edad, fecha_nacimiento, sexo, nacionalidad, municipio, provincia.
- Datos de centro asistencial: `centro_salud_asignado`, `hospital_referencia`, `unidad_clinica`.

### 2.4. Estrategia general para el modelo

- En caso de duda entre `cuasi_identificador` y `atributo_sensible` en campos clínicos:
  - Preferir `atributo_sensible`.
- En campos de texto libre (`nota_clinica`, `comentario_medico`):
  - Asumir que contienen datos de salud y potencialmente otros datos personales → `atributo_sensible`.

---

## 3. Dominio policial / seguridad / justicia

### 3.1. Identificadores directos típicos

- `dni`, `nie`, `pasaporte`, `nombre_completo`, `alias`, `id_persona`, `id_sospechoso`, `id_victima`
- Matrículas: `matricula_vehiculo`, `num_placa`
- Identificadores de expediente personal: `num_expediente_persona`, `id_interno_detencion`

### 3.2. Atributos sensibles

- Información sobre delitos o infracciones:
  - `tipo_delito`, `clasificacion_delito`, `antecedentes_penales`, `num_causa`, `situacion_penal`
- Situaciones de protección:
  - `victima_violencia_genero`, `orden_alejamiento`, `programa_proteccion_testigos`
- Información sobre medidas cautelares o sentencias.

### 3.3. Cuasi-identificadores frecuentes

- Datos de localización de incidentes:
  - `municipio_incidente`, `barrio_incidente`, `zona`, `coordenadas_incidente`
- Profesión / rol:
  - `profesion`, `ocupacion`, `rol_en_hecho` (en algunos contextos puede ser sensible).

### 3.4. Estrategia general para el modelo

- Los campos que describen hechos delictivos, sanciones o medidas judiciales se consideran `atributo_sensible`.
- Las matrículas de vehículos se tratan, por defecto, como `identificador_directo` en este dominio.
- Campos tipo `descripcion_hechos`, `relato_suceso` deben considerarse `atributo_sensible`.

---

## 4. Dominio servicios sociales / bienestar social

### 4.1. Identificadores directos típicos

- `id_beneficiario`, `id_expediente_social`, `dni`, `nombre_completo`, `telefono`, `email`.

### 4.2. Atributos sensibles

- Información sobre:

  - Violencia de género: `victima_violencia_genero`
  - Situaciones de exclusión social: `situacion_exclusion`, `riesgo_exclusion`
  - Prestaciones específicas: `renta_insercion`, `ingreso_minimo_vital`, `ayuda_vivienda`
  - Situaciones familiares complejas: `menores_a_cargo_en_riesgo`, `medida_tutela`

- Campos de texto libre con informes sociales: `informe_social`, `valoracion_tecnica`, `observaciones_trabajador_social`.

### 4.3. Cuasi-identificadores

- Datos demográficos y de residencia (edad, municipio, cod_postal).
- Datos de convivencia: `num_hijos`, `tipo_hogar`, `estado_civil`.

### 4.4. Estrategia general

- Ante la duda, los campos que reflejan situaciones de vulnerabilidad se clasifican como `atributo_sensible`.
- Los campos “económicos” asociados a prestaciones sociales sensibles también → `atributo_sensible`.

---

## 5. Dominio financiero / bancario / seguros

### 5.1. Identificadores directos

- `iban`, `num_cuenta`, `tarjeta_credito`, `id_cliente`, `dni`, `nombre_completo`.

### 5.2. Atributos sensibles

- Datos sobre **morosidad o impago**:
  - `situacion_morosidad`, `importe_impago`, `dias_mora`.
- Datos que reflejan **vulnerabilidad financiera**:
  - `cliente_en_riesgo`, `procedimiento_embargo`, `nivel_sobreendeudamiento`.
- Historial de siniestros en seguros si conllevan información de salud o judicial:
  - `tipo_siniestro`, `siniestro_corporales`, `siniestro_penal`.

### 5.3. Cuasi-identificadores

- Importes generalistas: `importe_compra`, `importe_operacion`, `saldo_medio` (depende del nivel de detalle).
- Segmentación de clientes: `segmento_renta`, `segmento_riesgo`, `tipo_cliente`.

### 5.4. Estrategia general

- Campos claramente técnicos o de producto → `no_sensible`.
- Campos que señalen riesgo, morosidad o procesos legales → `atributo_sensible`.
- Importes agregados sin contexto de vulnerabilidad clara → `no_sensible` o `cuasi_identificador` según granularidad.

---

## 6. Dominio RRHH / empleo / gestión de personal

### 6.1. Identificadores directos

- `id_empleado`, `dni`, `num_ss`, `email_corporativo` (si es personal), `telefono_trabajador`.

### 6.2. Atributos sensibles

- Información sobre salud laboral:
  - `baja_medica`, `tipo_baja`, `motivo_baja` (si implica salud).
- Sanciones disciplinarias internas:
  - `expediente_disciplinario`, `falta_grave`, `suspension_empleo_sueldo`.
- Afiliación sindical:
  - `afiliacion_sindical`, `delegado_sindical`.

### 6.3. Cuasi-identificadores

- `puesto_trabajo`, `categoria_profesional`, `departamento`, `centro_trabajo`.
- `fecha_ingreso_empresa`, `antiguedad`.

### 6.4. Estrategia general

- Todo lo que tenga que ver con salud y sanciones disciplinarias → `atributo_sensible`.
- Datos de puesto, categoría y centro → `cuasi_identificador`.

---

## 7. Dominio marketing / CRM / comercial

### 7.1. Identificadores directos

- `id_cliente`, `email`, `telefono`, `dni`, `nombre_completo`.

### 7.2. Atributos sensibles

- Preferencias que impliquen categorías especiales (ej. afiliación política, religión, salud).
- Segmentaciones que definan vulnerabilidad clara (ej. “clientes sobreendeudados”) si llegan a ese nivel de detalle.

### 7.3. Cuasi-identificadores

- `edad`, `sexo`, `municipio`, `cod_postal`.
- Preferencias de productos o canales cuando den un perfil muy concreto: `interes_seguro_salud`, `interes_productos_inversion`.

### 7.4. No sensibles

- `canal_preferido`, `frecuencia_compra`, `importe_medio_compra` en muchos contextos.

### 7.5. Estrategia general

- Tratar la mayoría de campos de segmentación de clientes como `cuasi_identificador`.
- Ser especialmente cuidadoso con segmentos que sugieran información de salud, política o vulnerabilidad económica → `atributo_sensible`.

---

## 8. Dominio administración general / tramitación

### 8.1. Identificadores directos

- `id_expediente_persona`, `num_solicitud`, `dni`, `nombre_completo`, `telefono_contacto`, `email`.

### 8.2. Atributos sensibles

- Datos sobre:
  - Procesos sancionadores, infracciones, multas graves.
  - Datos de salud incluida en expedientes.
  - Información social sensible (por ejemplo, procedimientos de protección de menores).

### 8.3. Cuasi-identificadores

- Datos demográficos y de residencia.
- Datos de relación con la administración: `tipo_solicitud`, `tipo_tramite`, `unidad_gestora` (normalmente no sensibles, pero pueden aportar contexto).

---

## 9. Estrategia en dominio desconocido

Cuando el dominio del dataset **no está claro**, el modelo debe:

1. Aplicar estrictamente las definiciones del documento `01_guia_clasificacion_columnas.md`.
2. Ser **conservador**:
   - En caso de duda entre `cuasi_identificador` y `no_sensible`, preferir `cuasi_identificador`.
   - En caso de duda entre `cuasi_identificador` y `atributo_sensible`, valorar si el contenido puede encajar en categorías especiales de datos; si sí, elegir `atributo_sensible`.
3. Indicar en el `rationale` que no se conoce el dominio y que la decisión se ha tomado siguiendo la regla de prioridad y la prudencia en términos de protección de datos.

---

## 10. Uso por parte del modelo LLM

Cuando el modelo reciba:

- una descripción del dataset (ej. “tabla de pacientes hospitalarios”, “base de datos de expedientes policiales”), o
- pistas en nombres de columnas (`id_paciente`, `num_expediente_penal`, `victima_violencia_genero`, etc.),

debe:

1. Identificar el **dominio más probable**.
2. Aplicar las reglas de este documento **además** de las definiciones básicas de la guía principal.
3. Explicitar en el `rationale` cuando una decisión se vea influida por el dominio:

   > Ejemplo de rationale:  
   > "Columna de tipo fecha de nacimiento en un contexto sanitario; se clasifica como cuasi_identificador según la guía general y la sección de dominio sanitario."

Este documento se incluirá como contexto en el RAG junto con la guía principal y los ejemplos de columnas.
