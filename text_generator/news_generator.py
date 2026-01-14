import time
import requests
import json
from datetime import datetime, timedelta
from ollama import chat
from ollama import Client
import re
import chromadb
from chromadb.utils import embedding_functions
import argparse 
import sys

from ollama_execution import exec_ollama, exec_ollama_rag

# --- Configuration Constants (IP addresses and ports for services) ---
API_IP = "localhost"
REAL_API_PORT = 5010
CHROMADB_IP = "localhost"
CHROMADB_PORT = 8001
OLLAMA_IP = "localhost" 
OLLAMA_PORT = 11434
LLM_API_IP = "localhost"
LLM_API_PORT = 6002

error_count = 0

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
    print("Data:" + str(data))
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error updating entry: {e}")
        return None

if __name__ == '__main__':

    # --- BLOQUE DE ARGUMENTOS ---
    parser = argparse.ArgumentParser(description="Ejecutar pipeline de generación de noticias.")
    
    # Argumentos originales
    parser.add_argument('--model', required=True, type=str, help='Prefijo del nombre del modelo (ej: QWEN_7B_)')
    parser.add_argument('--id_llm', required=True, type=int, help='Identificador numérico del LLM (ej: 1, 2)')
    
    # --- NUEVOS ARGUMENTOS DE FECHA ---
    parser.add_argument('--sdate', required=True, type=str, help='Fecha de inicio en formato dd-mm-yyyy')
    parser.add_argument('--edate', required=True, type=str, help='Fecha de fin en formato dd-mm-yyyy')
    
    args = parser.parse_args()
    
    cli_model_name = args.model
    cli_id_llm = args.id_llm
    
    # --- PROCESAMIENTO DE FECHAS ---
    try:
        # Convertimos los strings de entrada a objetos datetime
        start_date = datetime.strptime(args.sdate, "%d-%m-%Y")
        end_date = datetime.strptime(args.edate, "%d-%m-%Y")
        
        # Validacion básica
        if start_date > end_date:
            print("Error: La fecha de inicio (sdate) no puede ser posterior a la fecha de fin (edate).")
            sys.exit(1)
            
    except ValueError:
        print("Error de formato: Las fechas deben ser dd-mm-yyyy (ej: 25-10-2025)")
        sys.exit(1)

    print(f"Ejecutando proceso desde {start_date.date()} hasta {end_date.date()}")

    # Definimos horas fijas (día completo) ya que el script original lo hacía así
    start_hour = 0
    end_hour = 23
    
    # Initialize counters
    num_generated_news_NO_RAG = 0
    num_generated_news_RAG = 0
    error_count = 0
    
    # Initialize ChromaDB client
    chroma_client = chromadb.HttpClient(host=CHROMADB_IP, port=CHROMADB_PORT)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
     model_name="intfloat/multilingual-e5-large"
    )

    features = [3,2,1]  # Temperatures
    
    # Main processing loop
    newspapers_data = get_newspapers()
    if newspapers_data:
        for newspaper in newspapers_data.get("newspapers", []):
            
            for id_feature in features:
                
                modelo = cli_model_name 
                id_llm = cli_id_llm  
                
                model_NO_RAG = modelo + "LLM_resumen_NO_RAG_T"+str(id_feature)
                model_RAG = modelo + "LLM_resumen_RAG_T"+str(id_feature)

                collection = chroma_client.get_or_create_collection(name="real_news_data_" + str(newspaper), embedding_function=embedding_fn)
                endpoint_url = "http://" + str(LLM_API_IP) + ":" + str(LLM_API_PORT) + "/newsLLM/" + newspaper
                
                # Bucle de fechas: Calculamos la diferencia de días basándonos en los argumentos
                delta_days = (end_date - start_date).days
                
                for i in range(delta_days + 1):
                    current_date = start_date + timedelta(days=i)
                    day = current_date.day
                    month = current_date.month
                    year = current_date.year
                
                    print(f"Procesando fecha: {day}-{month}-{year} para {newspaper}")

                    # Llamada a la API de noticias reales
                    news_response = read_newspaper_news(newspaper, str(day) + "-" + str(month) + "-" + str(year), str(start_hour), "00", str(end_hour), "00")
                    
                    if news_response and "items" in news_response:
                        for news_item in news_response["items"]:
                            
                            document_NO_RAG = dict()
                            document_RAG = dict()

                            if news_item.get("description"):
                                query_text = news_item["headline"]
                                results = collection.query(
                                        query_texts=[query_text],
                                        n_results=10 
                                    )
                                context = results["documents"]
                                print("contexto: " + str(context))
                                
                                news_item["description"] = remove_html(news_item["description"])
                                
                                try:
                                    print("title: " + news_item["headline"])
                                    
                                    # Generate synthetic description WITHOUT RAG
                                    document_NO_RAG = {
                                    "RAG": 0,
                                    "id_news": news_item["_id"],
                                    "timestamp_llm": int(datetime.now().timestamp()),
                                    "id_feature": id_feature,
                                    "id_llm": id_llm,
                                    "synthetic_description": exec_ollama(None, OLLAMA_IP, OLLAMA_PORT, "source_title: " + str(news_item["headline"]), "source_description: " + str(news_item["description"]), model_NO_RAG).get("synthetic_description", "N/A"),
                                    }
                                    print("NO RAG: " + str(document_NO_RAG))

                                    # Generate synthetic description WITH RAG
                                    document_RAG = {
                                    "RAG": 1,
                                    "id_news": news_item["_id"],
                                    "timestamp_llm": int(datetime.now().timestamp()),
                                    "id_feature": id_feature,
                                    "id_llm": id_llm,
                                    "context": context[0],
                                    "synthetic_description": exec_ollama_rag(None, OLLAMA_IP, OLLAMA_PORT, "source_title: " + str(news_item["headline"]), "descripcion: " + str(news_item["description"]), context, model_RAG).get("synthetic_description", "N/A"),
                                    }
                                    print("Yes RAG: " + str(document_RAG))
                        
                                    # Send generated documents
                                    try:
                                        if document_RAG:
                                            response = requests.post(endpoint_url, json=document_RAG)
                                            num_generated_news_RAG += 1
                                            if response.status_code == 201:
                                                print("RAG Document inserted successfully")
                                            else:
                                                print(f"Error {response.status_code}: {response.text}")

                                        if document_NO_RAG:
                                            response = requests.post(endpoint_url, json=document_NO_RAG)
                                            num_generated_news_NO_RAG += 1
                                            if response.status_code == 201:
                                                print("NO-RAG Document inserted successfully")
                                            else:
                                                print(f"Error {response.status_code}: {response.text}")

                                    except requests.exceptions.RequestException as e:
                                        print("Error connecting to API:", e)
                                    
                                except Exception as e:
                                    print("Error processing news with Ollama:", e)
                                    error_count += 1
    else:
        print("No se pudieron obtener periódicos.")

    # Print final execution statistics
    print("------------------------------------------------")
    print("The number of Ollama errors was: " + str(error_count))
    print("The number of generated RAG news was: " + str(num_generated_news_RAG))
    print("The number of generated NO RAG news was: " + str(num_generated_news_NO_RAG))
    print("End time: " + str(datetime.now()))