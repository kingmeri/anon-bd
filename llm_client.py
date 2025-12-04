# llm_client.py
import requests

def call_ollama(prompt: str, model: str, ollama_url: str, timeout: int = 180) -> str:
    """
    Llama a Ollama y devuelve SOLO el campo 'response' como string.
    Lanza excepciones HTTP si algo va mal.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    resp = requests.post(ollama_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")
