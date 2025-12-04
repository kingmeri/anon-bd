# 00_resumen_reglas

## 🧩 Objetivo
Clasificar columnas de bases de datos en una de las cuatro categorías:
1. **IDENTIFICADOR_DIRECTO**
2. **ATRIBUTO_SENSIBLE**
3. **CUASI_IDENTIFICADOR**
4. **NO_SENSIBLE**

## 🧠 1. Definiciones extremadamente claras

### 🔹 IDENTIFICADOR_DIRECTO
Dato que identifica de forma única e inmediata a una persona. Incluye identificadores internos cuando representan a una persona concreta.

**Ejemplos:**
- DNI, NIE, NIF, pasaporte
- Teléfono móvil, email personal
- id_cliente, id_persona, id_paciente, id_usuario (si representan personas)
- Matrícula de coche

### 🔹 ATRIBUTO_SENSIBLE
Datos de categorías especiales (salud, biometría, religión, política, orientación sexual, antecedentes…).

### 🔹 CUASI_IDENTIFICADOR
Dato que no identifica por sí solo pero sí en combinación con otros.

### 🔹 NO_SENSIBLE
Datos que no permiten identificar a una persona ni revelan información sensible.

## 🔥 2. Regla de prioridad
1. IDENTIFICADOR_DIRECTO
2. ATRIBUTO_SENSIBLE
3. CUASI_IDENTIFICADOR
4. NO_SENSIBLE

## 🎯 3. Reglas rápidas por nombre
- Prefijo id_ → IDENTIFICADOR_DIRECTO si representa persona.
- Contiene salud (diagnóstico, enfermedad…) → ATRIBUTO_SENSIBLE.
- Ubicación/demografía → CUASI_IDENTIFICADOR.
- Datos técnicos → NO_SENSIBLE.

## 🎲 4. Casos borde
- Texto libre → CUASI_IDENTIFICADOR (o sensible si es salud)
- Hashes/UUID → NO_SENSIBLE
- Dirección completa → CUASI_IDENTIFICADOR
- Matrícula → IDENTIFICADOR_DIRECTO

## 🧭 5. Dominios
### Sanitario
- Identificadores: id_paciente
- Sensibles: diagnóstico
- Cuasi: edad, CP

### Financiero
- Identificadores: id_cliente
- Sensibles: importe exacto
- Cuasi: tramo salarial

## 🏁 Formato de respuesta esperado
categoria: IDENTIFICADOR_DIRECTO | ATRIBUTO_SENSIBLE | CUASI_IDENTIFICADOR | NO_SENSIBLE
razon: explicación breve
