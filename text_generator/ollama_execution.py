import json
from datetime import datetime, timedelta
from ollama import chat
from ollama import Client
import re
import requests

# Module handling interactions with the Ollama API. It constructs prompts, 
# manages HTTP requests for standard and RAG-based generation, and parses the resulting JSON output.

# Global error counter (assuming it is defined in the main scope)
error_count = 0

# Executes a standard (No-RAG) generation request to Ollama. 
def exec_ollama(prompt_input, ollama_ip, ollama_port, title, description, model):
    url = f"http://{ollama_ip}:{ollama_port}/api/generate"

    # Prompt construction (Spanish content preserved, variables updated to English)
    prompt = (
        f"source_title: {title}\n"
        f"target_word_count: {len(description.split())}\n"
        "INSTRUCCIONES: Genera un JSON siguiendo las reglas definidas en el Modelfile."
    )

    response = requests.post(
        url,
        json={"model": model, "prompt": prompt},
        stream=True
    )

    full_text = ""
    for line in response.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue  # ignore non-JSON lines
        
        # Concatenate partial texts
        if "response" in data and data["response"]:
            full_text += data["response"]

    if not full_text.strip():
        print("The LLM did not return text")
        return None

    # Parse final JSON (if your prompt requests JSON)
    try:
        full_text = full_text.strip()
        full_text = re.sub(r"^```json\s*|```$", "", full_text, flags=re.MULTILINE).strip()
        output = json.loads(full_text.strip())
    except json.JSONDecodeError:
        print("Could not parse JSON. Raw response:")
        print(full_text)
        
        # Handling the global counter
        global error_count
        error_count += 1

        return None
    
    # Normalize fields
    if "changes_made" in output and isinstance(output["changes_made"], str):
        output["changes_made"] = [output["changes_made"]]

    return output


# Executes a RAG-enhanced generation request to Ollama.
def exec_ollama_rag(prompt_input, ollama_ip, ollama_port, title, description, context, model):
    url = f"http://{ollama_ip}:{ollama_port}/api/generate"

    # Prompt construction (Spanish content preserved, variables updated to English)
    prompt = (
        f"source_title: {title}\n"
        f"target_word_count: {len(description.split())}\n"
        f"context: {context}\n"
        "INSTRUCCIONES: Genera un JSON siguiendo las reglas definidas en el Modelfile."
    )

    response = requests.post(
        url,
        json={"model": model, "prompt": prompt},
        stream=True
    )

    full_text = ""
    for line in response.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue  # ignore non-JSON lines
        
        # Concatenate partial texts
        if "response" in data and data["response"]:
            full_text += data["response"]

    if not full_text.strip():
        print("The LLM did not return text")
        return None

    # Parse final JSON
    try:
        full_text = full_text.strip()
        full_text = re.sub(r"^```json\s*|```$", "", full_text, flags=re.MULTILINE).strip()
        output = json.loads(full_text.strip())
    except json.JSONDecodeError:
        print("Could not parse JSON. Raw response:")
        print(full_text)
        
        # Handling the global counter
        global error_count
        error_count += 1

        return None
    
    # Normalize fields
    if "changes_made" in output and isinstance(output["changes_made"], str):
        output["changes_made"] = [output["changes_made"]]

    return output