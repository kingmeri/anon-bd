# classifier.py
import json
from llm_client import call_ollama
from rag_client import RAGClient
from prompts import build_prompt_without_context, build_prompt_with_context

rag_client = RAGClient()

def classify_columns_without_rag(columns):
    prompt = build_prompt_without_context(columns)
    raw = call_ollama(prompt)
    return json.loads(raw)  # aquí puedes envolver en try/except y validar

def build_retrieval_query(columns):
    desc = "; ".join(
        f'{c["name"]} ({c.get("data_type","desconocido")})'
        for c in columns
    )
    return (
        "Clasificación de columnas de una tabla según GDPR y AEPD en "
        "identificador_directo, cuasi_identificador, atributo_sensible y no_sensible. "
        f"Columnas: {desc}"
    )

def classify_columns_with_rag(columns, k=5):
    query = build_retrieval_query(columns)
    ctx = rag_client.retrieve_context(query, k=k)
    prompt = build_prompt_with_context(columns, ctx)
    raw = call_ollama(prompt)
    return json.loads(raw), ctx



