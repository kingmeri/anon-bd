#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random, datetime, string, re, unicodedata
from faker import Faker
import mysql.connector

# ---------- Configuración ----------
DB_CFG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",        # cambia si usas otro usuario
    "password": "secret",  # cambia tu pass
    "database": "formacion_empleo",
}

N_PERSONAS   = 100
N_MATRICULAS = 100
N_PRACTICAS  = 100

fake = Faker("es_ES")
random.seed(42)

# ---------- Utilidades ASCII ----------
def to_ascii(s: str | None) -> str | None:
    """Quita tildes/ñ/diacríticos y fuerza ASCII seguro."""
    if s is None:
        return None
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # elimina cualquier carácter no-ASCII
    s = s.encode("ascii", "ignore").decode("ascii")
    # compacta espacios
    s = re.sub(r"\s+", " ", s).strip()
    return s

def ascii_email(local_part: str, domain: str) -> str:
    lp = to_ascii(local_part or "").lower()
    dm = to_ascii(domain or "").lower()
    # limpia caracteres no válidos en email
    lp = re.sub(r"[^a-z0-9._+\-]", "", lp)
    dm = re.sub(r"[^a-z0-9.\-]", "", dm)
    if not dm:
        dm = "example.com"
    if not lp:
        lp = "user"
    return f"{lp}@{dm}"

# ---------- Catálogos jerárquicos ----------
# Mantengo las etiquetas "reales" y limpio al insertar (to_ascii)
GEO = [
    {"cp": "28001", "ciudad": "Madrid",        "provincia": "Madrid",        "ccaa": "Comunidad de Madrid", "pais": "España"},
    {"cp": "08002", "ciudad": "Barcelona",     "provincia": "Barcelona",     "ccaa": "Cataluña",             "pais": "España"},
    {"cp": "41001", "ciudad": "Sevilla",       "provincia": "Sevilla",       "ccaa": "Andalucía",            "pais": "España"},
    {"cp": "46001", "ciudad": "Valencia",      "provincia": "Valencia",      "ccaa": "Comunidad Valenciana", "pais": "España"},
    {"cp": "50001", "ciudad": "Zaragoza",      "provincia": "Zaragoza",      "ccaa": "Aragón",               "pais": "España"},
    {"cp": "48001", "ciudad": "Bilbao",        "provincia": "Bizkaia",       "ccaa": "País Vasco",           "pais": "España"},
    {"cp": "15001", "ciudad": "A Coruña",      "provincia": "A Coruña",      "ccaa": "Galicia",              "pais": "España"},
    {"cp": "03001", "ciudad": "Alicante",      "provincia": "Alicante",      "ccaa": "Comunidad Valenciana", "pais": "España"},
    {"cp": "29001", "ciudad": "Málaga",        "provincia": "Málaga",        "ccaa": "Andalucía",            "pais": "España"},
    {"cp": "20001", "ciudad": "San Sebastián", "provincia": "Gipuzkoa",      "ccaa": "País Vasco",           "pais": "España"},
]

NIVEL_ESTUDIOS = [
    "Sin estudios", "Primaria", "Secundaria", "Bachillerato",
    "FP Grado Medio", "FP Grado Superior", "Universitario", "Postgrado"
]

SITUACION_LABORAL = [
    "Estudiante", "Desempleado", "Activo", "Autonomo", "Jubilado"  # ya sin tilde en Autonomo
]

FAMILIA_PROFESIONAL = [
    "Informatica y comunicaciones", "Administracion y gestion", "Sanidad",
    "Comercio y marketing", "Hosteleria y turismo"  # ya sin tildes
]

MODALIDADES = ["Presencial", "Online", "Mixta"]

SECTORES = [
    "Tecnologia", "Salud", "Educacion", "Finanzas", "Comercio",
    "Hosteleria", "Industria", "Transporte", "Energia"
]

EMPRESAS = [
    "Acme Corp", "InnovaTech", "SaludPlus", "EducaNet", "FinBank",
    "Comerzia", "HostelMax", "IndusPro", "TransGo", "EnerGreen"
]

# ---------- DNI / telefono / nacimiento ----------
DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
def gen_dni():
    num = random.randint(10000000, 99999999)
    letter = DNI_LETTERS[num % 23]
    return f"{num}{letter}"

def gen_phone():
    # móvil español típico
    return f"+34 {random.choice(['6','7'])}{random.randint(10000000,99999999)}"

def gen_birthdate(edad_min=18, edad_max=70):
    hoy = datetime.date.today()
    edad = random.randint(edad_min, edad_max)
    year = hoy.year - edad
    month = random.randint(1,12)
    day = random.randint(1,28)
    return datetime.date(year, month, day)

def main():
    conn = mysql.connector.connect(**DB_CFG)
    cur = conn.cursor()

    # Asegúrate de usar la BD
    cur.execute("CREATE DATABASE IF NOT EXISTS formacion_empleo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")
    cur.execute("USE formacion_empleo;")

    # --- PERSONA (100) ---
    persona_ids = []
    for _ in range(N_PERSONAS):
        geo_raw = random.choice(GEO)
        # limpiar geo a ASCII
        geo = {
            "cp": geo_raw["cp"],
            "ciudad": (geo_raw["ciudad"]),
            "provincia": (geo_raw["provincia"]),
            "ccaa": (geo_raw["ccaa"]),
            "pais": (geo_raw["pais"]),
        }

        # nombres/apellidos y email ASCII
        nombre = (fake.first_name())
        ap1 = (fake.last_name())
        ap2_val = (fake.last_name()) if random.random() < 0.8 else None
        dni = gen_dni()
        email = ascii_email(f"{nombre}.{ap1}.{random.randint(1,999)}", fake.free_email_domain())
        telefono = gen_phone()
        fnac = gen_birthdate()

        sexo = random.choice(["Mujer","Hombre","Otro","No especifica"])
        # si tu columna sigue en VARCHAR(12), descomenta la siguiente línea:
        # sexo = sexo[:12]

        nivel = (random.choice(NIVEL_ESTUDIOS))
        sitlab = (random.choice(SITUACION_LABORAL))
        ingresos = random.choice([None, random.randint(900, 6000)])  # mensual hogar aprox
        thogar = random.choice([None, random.randint(1,6)])
        consentimiento = random.choice([0,1,1,1])  # mayoría sí

        cur.execute("""
            INSERT INTO persona
            (dni, nombre, apellido1, apellido2, email, telefono,
             fecha_nacimiento, sexo, cp, ciudad, provincia, ccaa, pais,
             nivel_estudios, situacion_laboral, ingresos_hogar, tamano_hogar, consentimiento_contacto)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            dni, nombre, ap1, ap2_val, email, telefono,
            fnac, sexo, geo["cp"], geo["ciudad"], geo["provincia"], geo["ccaa"], geo["pais"],
            nivel, sitlab, ingresos, thogar, consentimiento
        ))
        persona_ids.append(cur.lastrowid)

    # --- MATRICULA (100) ---
    for _ in range(N_MATRICULAS):
        pid = random.choice(persona_ids)
        curso_raw = f"Curso de {random.choice(['Python','SQL','Ciberseguridad','Excel','Marketing','Atencion sanitaria'])} {random.randint(1,3)}"
        curso = (curso_raw)
        fam = (random.choice(FAMILIA_PROFESIONAL))
        modalidad = (random.choice(MODALIDADES))
        fmat = fake.date_between(start_date="-3y", end_date="today")
        cur.execute("""
            INSERT INTO matricula (id_persona, curso, familia_profesional, modalidad, fecha_matricula)
            VALUES (%s,%s,%s,%s,%s)
        """, (pid, curso, fam, modalidad, fmat))

    # --- PRACTICAS_EMPLEO (100) ---
    for _ in range(N_PRACTICAS):
        pid = random.choice(persona_ids)
        empresa = (random.choice(EMPRESAS))
        sector = (random.choice(SECTORES))
        salario = random.choice([None, random.randint(800, 2500)])

        geo_raw = random.choice(GEO)
        ciudad_p = (geo_raw["ciudad"])
        provincia_p = (geo_raw["provincia"])
        ccaa_p = (geo_raw["ccaa"])
        pais_p = (geo_raw["pais"])

        dur = random.randint(1, 6)
        cur.execute("""
            INSERT INTO practicas_empleo
            (id_persona, empresa, sector, salario_mensual,
             ciudad_puesto, provincia_puesto, ccaa_puesto, pais_puesto, duracion_meses)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (pid, empresa, sector, salario,
              ciudad_p, provincia_p, ccaa_p, pais_p, dur))

    conn.commit()
    cur.close(); conn.close()
    print("[OK] Insertadas 100 personas, 100 matrículas y 100 prácticas (ASCII-only).")

if __name__ == "__main__":
    main()
