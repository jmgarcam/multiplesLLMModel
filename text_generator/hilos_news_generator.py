import time
import requests
import json
from datetime import datetime, timedelta
from ollama import chat
from ollama import Client
import re
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
import threading  # Única librería nueva necesaria

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

# Global counter to track LLM generation errors
# Usamos un Lock para modificar estas variables globales de forma segura entre hilos
data_lock = threading.Lock() 
error_count = 0
num_generated_news_NO_RAG = 0
num_generated_news_RAG = 0

# Utility function that sanitizes input text.
def remove_html(text):
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', text)
    # Remove extra spaces or unnecessary line breaks
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

# Retrieves the list of available newspaper sources.
def get_newspapers():
    url = str("http://") + API_IP + ":" + str(REAL_API_PORT) + "/newspapers"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling endpoint: {e}")
        return None

# Fetches news articles for a specific newspaper and time window from the real news API.
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

# Updates specific metadata tags for a news entry in the database. 
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

# Función Worker para ejecutar en cada hilo (contiene toda la lógica interna del bucle original)
def process_feature_thread(newspaper, id_feature, start_date, end_date, start_hour, end_hour, collection, id_llm, modelo):
    # Referenciamos las variables globales que vamos a modificar
    global error_count
    global num_generated_news_NO_RAG
    global num_generated_news_RAG

    
    # Model definitions for Ollama
    model_NO_RAG = modelo + "LLM_resumen_NO_RAG_T"+str(id_feature)
    model_RAG = modelo + "LLM_resumen_RAG_T"+str(id_feature)

    endpoint_url = "http://" + str(LLM_API_IP) + ":" + str(LLM_API_PORT) + "/newsLLM/" + newspaper

    # Date iteration loop
    for i in range((end_date - start_date).days + 1):
        current_date = start_date + timedelta(days=i)
        day = current_date.day
        month = current_date.month
        year = current_date.year
    
        # Process each news item found for the current date/time
        # Nota: start_hour y end_hour se pasan como argumentos para mantener la variable original
        news_data = read_newspaper_news(newspaper, str(day) + "-" + str(month) + "-" + str(year), str(start_hour), "00", str(end_hour), "00")
        
        if news_data is not None and "items" in news_data:
            for news_item in news_data["items"]:
                
                document_NO_RAG = dict()
                document_RAG = dict()

                if news_item["description"]:
                    # Perform RAG search: Find similar documents in ChromaDB using the headline
                    query_text = news_item["headline"]
                    results = collection.query(
                            query_texts=[query_text],
                            n_results=10 
                        )
                    context = results["documents"]
                    
                    news_item["description"] = remove_html(news_item["description"])
                    print(len(news_item["description"].split()))
                    
                    try:
                        print(f"[Thread-F{id_feature}] title: " + news_item["headline"])
                        # print(news_item["description"]) # Comentado para no saturar consola en multihilo, descomentar si necesario
                        
                        # Generate synthetic description WITHOUT RAG context
                        # Ejecutamos Ollama y extraemos valor
                        synthetic_desc_no_rag = exec_ollama(None, OLLAMA_IP, OLLAMA_PORT, "source_title: " + str(news_item["headline"]), "source_description: " + str(news_item["description"]), model_NO_RAG).get("synthetic_description", "N/A")

                        document_NO_RAG = {
                        "RAG": 0,
                        "id_news": news_item["_id"],
                        "timestamp_llm": int(datetime.now().timestamp()),
                        "id_feature": id_feature,
                        "id_llm": id_llm,
                        "synthetic_description": synthetic_desc_no_rag,
                        }
                        print(f"[Thread-F{id_feature}] NO-RAG created")

                        # Generate synthetic description WITH RAG context
                        synthetic_desc_rag = exec_ollama_rag(None, OLLAMA_IP, OLLAMA_PORT, "source_title: " + str(news_item["headline"]), "descripcion: " + str(news_item["description"]), context, model_RAG).get("synthetic_description", "N/A")

                        document_RAG = {
                        "RAG": 1,
                        "id_news": news_item["_id"],
                        "timestamp_llm": int(datetime.now().timestamp()),
                        "id_feature": id_feature,
                        "id_llm": id_llm,
                        "context": context[0],
                        "synthetic_description": synthetic_desc_rag,
                        }
                        print(f"[Thread-F{id_feature}] RAG created")
                
                        # Send generated documents to the storage API
                        try:
                            if document_RAG:
                                response = requests.post(endpoint_url, json=document_RAG)
                                
                                # Bloqueo para contador seguro
                                with data_lock:
                                    num_generated_news_RAG += 1
                                
                                if response.status_code == 201:
                                    print(f"[Thread-F{id_feature}] Document inserted successfully (RAG)")
                                    # print(json.dumps(response.json(), indent=2, ensure_ascii=False))
                                else:
                                    print(f"Error {response.status_code}: {response.text}")

                            if document_NO_RAG:
                                response = requests.post(endpoint_url, json=document_NO_RAG)
                                
                                # Bloqueo para contador seguro
                                with data_lock:
                                    num_generated_news_NO_RAG += 1
                                
                                if response.status_code == 201:
                                    print(f"[Thread-F{id_feature}] Document inserted successfully (NO RAG)")
                                    # print(json.dumps(response.json(), indent=2, ensure_ascii=False))
                                else:
                                    print(f"Error {response.status_code}: {response.text}")

                        except requests.exceptions.RequestException as e:
                            print("Error connecting to API:", e)
                        
                    except Exception as e:
                        print("Error processing news with Ollama:", e)
                        with data_lock:
                            error_count = error_count + 1

if __name__ == '__main__':

    # Define the simulation timeframe
    year = 2025
    start_month = 10
    end_month = 11
    start_day = 25
    end_day = 11
    start_hour = 0
    end_hour = 23
    start_date = datetime(year, start_month, start_day)
    end_date = datetime(year, end_month, end_day)

    # Initialize counters (ya definidos arriba globalmente, pero mantenemos lógica de init si fuera local)
    # error_count = 0 
    
    # Initialize ChromaDB client and embedding function (Multilingual E5)
    chroma_client = chromadb.HttpClient(host=CHROMADB_IP, port=CHROMADB_PORT)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
     model_name="intfloat/multilingual-e5-large"
    )

    features = [3,2,1]  # Feature identifiers to iterate over, equivalent to temperatures under study
    model = "QWEN_7B_"
    id_llm = 2  # Identifier for the LLM model in use
    #1 = mistral 7B-instruct
    #2 = QWEN 7B

    # Main processing loop: Iterate through newspapers
    for newspaper in get_newspapers()["newspapers"]:
        
        # Connect to or create the vector collection for the specific newspaper
        # Lo hacemos aquí antes de los hilos para pasar el objeto ya creado
        collection = chroma_client.get_or_create_collection(name="real_news_data_" + str(newspaper), embedding_function=embedding_fn)
        
        # Lista para guardar los hilos activos
        threads = []

        # feature loop -> AHORA EN HILOS
        for id_feature in features:
            print(f"Lanzando hilo para Newspaper: {newspaper}, Feature: {id_feature}")
            
            # Creamos el hilo pasando TODAS las variables necesarias que antes estaban en el scope local
            t = threading.Thread(target=process_feature_thread, args=(
                newspaper, 
                id_feature, 
                start_date, 
                end_date, 
                start_hour, 
                end_hour, 
                collection, 
                id_llm,
                model
            ))
            threads.append(t)
            t.start()