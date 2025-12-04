ollama run llama3.2:3b-instruct-q4_K_M << 'EOF'
Eres experto en GDPR. Clasifica las columnas en:
- identificador_directo
- cuasi_identificador
- atributo_sensible
- no_sensible

Responde en español y SOLO JSON con este esquema:

{
  "items": [
    {
      "name": "string",
      "category": "identificador_directo|cuasi_identificador|atributo_sensible|no_sensible",
      "rationale": "string",
      "confidence": 0.0
    }
  ]
}

Columnas:
- dni (string)
- edad (int)
- ciudad (string)
- diagnosticos_medicos (string)

EOF