import time
import requests
import json
from datetime import datetime, timedelta
from ollama import chat
from ollama import Client
import re
import chromadb
from chromadb.utils import embedding_functions
import threading
import argparse
import sys

# Asegúrate de tener este módulo disponible
from ollama_execution import exec_ollama, exec_ollama_rag

# --- Configuration Constants ---
API_IP = "localhost"
REAL_API_PORT = 5010
CHROMADB_IP = "localhost"
CHROMADB_PORT = 8001
OLLAMA_IP = "localhost" 
OLLAMA_PORT = 11434
LLM_API_IP = "localhost"
LLM_API_PORT = 6002

# --- Global Variables & Locks ---
data_lock = threading.Lock() 
error_count = 0
num_generated_news_NO_RAG = 0
num_generated_news_RAG = 0

# --- Helper Functions ---
def remove_html(text):
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def get_newspapers():
    url = str("http://") + API_IP + ":" + str(REAL_API_PORT) + "/newspapers"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling endpoint: {e}")
        return None

def read_newspaper_news(newspaper, date, shour, sminute, ehour, eminute):
    params = "date=" + date + "&shour=" + shour + "&sminute=" + sminute + "&ehour=" + ehour + "&eminute=" + eminute
    url = str("http://") + API_IP + ":" + str(REAL_API_PORT) + "/news/" + newspaper + "?"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling endpoint: {e}")
        return None

def update_news(newspaper, news_id, tag, tag_value):
    url = str("http://") + API_IP + ":" + str(REAL_API_PORT) + "/news/" + newspaper + "/" + str(news_id)
    headers = {"Content-Type": "application/json"}
    data = {tag: tag_value}
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error updating entry: {e}")
        return None

# --- Worker Function (Thread) ---
def process_feature_thread(newspaper, id_feature, start_date, end_date, start_hour, end_hour, collection, id_llm, modelo):
    global error_count
    global num_generated_news_NO_RAG
    global num_generated_news_RAG

    # Definición del modelo basada en el argumento recibido
    model_NO_RAG = modelo + "LLM_resumen_NO_RAG_T"+str(id_feature)
    model_RAG = modelo + "LLM_resumen_RAG_T"+str(id_feature)

    endpoint_url = "http://" + str(LLM_API_IP) + ":" + str(LLM_API_PORT) + "/newsLLM/" + newspaper

    # Date iteration loop
    # Calculamos la diferencia de días
    delta_days = (end_date - start_date).days
    
    for i in range(delta_days + 1):
        current_date = start_date + timedelta(days=i)
        day = current_date.day
        month = current_date.month
        year = current_date.year
    
        # Procesar noticias
        news_data = read_newspaper_news(newspaper, str(day) + "-" + str(month) + "-" + str(year), str(start_hour), "00", str(end_hour), "00")
        
        if news_data is not None and "items" in news_data:
            for news_item in news_data["items"]:
                
                document_NO_RAG = dict()
                document_RAG = dict()

                if news_item.get("description"):
                    # RAG Search
                    query_text = news_item["headline"]
                    try:
                        results = collection.query(
                                query_texts=[query_text],
                                n_results=10 
                            )
                        context = results["documents"]
                    except Exception as e:
                        print(f"Error querying ChromaDB: {e}")
                        context = [""]

                    news_item["description"] = remove_html(news_item["description"])
                    
                    try:
                        print(f"[Thread-F{id_feature}] Processing: {news_item['headline'][:30]}...")
                        
                        # --- NO RAG Generation ---
                        synthetic_desc_no_rag = exec_ollama(None, OLLAMA_IP, OLLAMA_PORT, "source_title: " + str(news_item["headline"]), "source_description: " + str(news_item["description"]), model_NO_RAG).get("synthetic_description", "N/A")

                        document_NO_RAG = {
                        "RAG": 0,
                        "id_news": news_item["_id"],
                        "timestamp_llm": int(datetime.now().timestamp()),
                        "id_feature": id_feature,
                        "id_llm": id_llm,
                        "synthetic_description": synthetic_desc_no_rag,
                        }
                        # print(f"[Thread-F{id_feature}] NO-RAG created")

                        # --- RAG Generation ---
                        synthetic_desc_rag = exec_ollama_rag(None, OLLAMA_IP, OLLAMA_PORT, "source_title: " + str(news_item["headline"]), "descripcion: " + str(news_item["description"]), context, model_RAG).get("synthetic_description", "N/A")

                        document_RAG = {
                        "RAG": 1,
                        "id_news": news_item["_id"],
                        "timestamp_llm": int(datetime.now().timestamp()),
                        "id_feature": id_feature,
                        "id_llm": id_llm,
                        "context": context[0] if context else "",
                        "synthetic_description": synthetic_desc_rag,
                        }
                        # print(f"[Thread-F{id_feature}] RAG created")
                
                        # --- Send to API ---
                        try:
                            # Enviar RAG
                            if document_RAG:
                                response = requests.post(endpoint_url, json=document_RAG)
                                with data_lock:
                                    num_generated_news_RAG += 1
                                if response.status_code == 201:
                                    print(f"[Thread-F{id_feature}] RAG Inserted OK")
                                else:
                                    print(f"Error RAG API: {response.status_code}")

                            # Enviar NO RAG
                            if document_NO_RAG:
                                response = requests.post(endpoint_url, json=document_NO_RAG)
                                with data_lock:
                                    num_generated_news_NO_RAG += 1
                                if response.status_code == 201:
                                    print(f"[Thread-F{id_feature}] NO-RAG Inserted OK")
                                else:
                                    print(f"Error NO-RAG API: {response.status_code}")

                        except requests.exceptions.RequestException as e:
                            print("Error connecting to Storage API:", e)
                        
                    except Exception as e:
                        print("Error processing news with Ollama:", e)
                        with data_lock:
                            error_count += 1

# --- Main Execution ---
if __name__ == '__main__':

    # --- 1. Argument Parser ---
    parser = argparse.ArgumentParser(description="Ejecutar pipeline de generación de noticias con Hilos.")
    
    parser.add_argument('--model', required=True, type=str, help='Prefijo del nombre del modelo (ej: QWEN_7B_)')
    parser.add_argument('--id_llm', required=True, type=int, help='ID numérico del LLM (ej: 1, 2)')
    parser.add_argument('--sdate', required=True, type=str, help='Fecha inicio dd-mm-yyyy')
    parser.add_argument('--edate', required=True, type=str, help='Fecha fin dd-mm-yyyy')
    
    args = parser.parse_args()

    # --- 2. Date Processing ---
    try:
        start_date = datetime.strptime(args.sdate, "%d-%m-%Y")
        end_date = datetime.strptime(args.edate, "%d-%m-%Y")
        
        if start_date > end_date:
            print("Error: Fecha inicio posterior a fecha fin.")
            sys.exit(1)
    except ValueError:
        print("Error: Formato de fecha incorrecto. Use dd-mm-yyyy")
        sys.exit(1)

    print(f"Iniciando proceso multihilo del {start_date.date()} al {end_date.date()}")
    print(f"Modelo: {args.model} | ID LLM: {args.id_llm}")

    # Variables fijas de hora
    start_hour = 0
    end_hour = 23
    
    # Init Chroma
    chroma_client = chromadb.HttpClient(host=CHROMADB_IP, port=CHROMADB_PORT)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
     model_name="intfloat/multilingual-e5-large"
    )

    features = [3,2,1] 
    
    # --- 3. Main Loop ---
    newspapers_list = get_newspapers()
    
    if newspapers_list:
        for newspaper in newspapers_list["newspapers"]:
            
            # Crear colección para pasar al hilo
            collection = chroma_client.get_or_create_collection(name="real_news_data_" + str(newspaper), embedding_function=embedding_fn)
            
            threads = []
            
            # Lanzar hilos por feature
            for id_feature in features:
                print(f"Lanzando hilo -> Newspaper: {newspaper}, Feature: {id_feature}")
                
                t = threading.Thread(target=process_feature_thread, args=(
                    newspaper, 
                    id_feature, 
                    start_date, # Pasamos el objeto datetime parseado de args
                    end_date,   # Pasamos el objeto datetime parseado de args
                    start_hour, 
                    end_hour, 
                    collection, 
                    args.id_llm, # Pasamos ID LLM de args
                    args.model   # Pasamos Model Name de args
                ))
                threads.append(t)
                t.start()
            
            # --- ESPERAR A QUE TERMINEN LOS HILOS ---
            # Es importante esperar aquí (o fuera del bucle de periódicos) para que el script no termine
            # antes de que los hilos acaben su trabajo.
            for t in threads:
                t.join()
            
            print(f"--- Finalizados hilos para {newspaper} ---")

    else:
        print("No se pudieron recuperar periódicos.")

    # Print final statistics
    print("\n================================================")
    print("RESUMEN DE EJECUCIÓN")
    print("Errores de Ollama: " + str(error_count))
    print("Noticias RAG generadas: " + str(num_generated_news_RAG))
    print("Noticias NO RAG generadas: " + str(num_generated_news_NO_RAG))
    print("Hora fin: " + str(datetime.now()))
    print("================================================")