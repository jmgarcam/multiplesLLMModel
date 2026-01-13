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

from ollama_execution import exec_ollama, exec_ollama_rag

# It manages the retrieval of real news, interfaces with ChromaDB for RAG context retrieval, 
# and triggers the LLM generation processes for both RAG and No-RAG scenarios 
# across defined timeframes and features.

# --- Configuration Constants (IP addresses and ports for services) ---
# IP and port for real news
API_IP = "localhost"
REAL_API_PORT = 5010
# IP and port for ChromaDB
CHROMADB_IP = "localhost"
CHROMADB_PORT = 8001
# IP and port for Ollama
OLLAMA_IP = "localhost" 
OLLAMA_PORT = 11434
# IP and port for LLM API
LLM_API_IP = "localhost"
LLM_API_PORT = 6002

# Global counter to track LLM generation errors
error_count = 0

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

if __name__ == '__main__':

    # Define the simulation timeframe
    year = 2026
    start_month = 1
    end_month = 1
    start_day = 8
    end_day = 8
    start_hour = 0
    end_hour = 23
    start_date = datetime(year, start_month, start_day)
    end_date = datetime(year, end_month, end_day)

    # Initialize counters
    num_generated_news_NO_RAG = 0
    num_generated_news_RAG = 0
    error_count = 0
    
    # Initialize ChromaDB client and embedding function (Multilingual E5)
    chroma_client = chromadb.HttpClient(host=CHROMADB_IP, port=CHROMADB_PORT)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
     model_name="intfloat/multilingual-e5-large"
    )

    features = [3,2,1]  # Feature identifiers to iterate over, equivalent to temperatures under study
    

    # Main processing loop: Iterate through newspapers, features, and dates
    for newspaper in get_newspapers()["newspapers"]:

        for id_feature in features:
            
            # Model definitions for Ollama
            modelo = "QWEN_7B_"
            id_llm = 2  # Identifier for the LLM model in use
            #1 = mistral 7B-instruct
            #2 = QWEN 7B
            model_NO_RAG = modelo + "LLM_resumen_NO_RAG_T"+str(id_feature)
            model_RAG = modelo + "LLM_resumen_RAG_T"+str(id_feature)

            # Connect to or create the vector collection for the specific newspaper
            collection = chroma_client.get_or_create_collection(name="real_news_data_" + str(newspaper), embedding_function=embedding_fn)
            endpoint_url = "http://" + str(LLM_API_IP) + ":" + str(LLM_API_PORT) + "/newsLLM/" + newspaper

            # Date iteration loop
            for i in range((end_date - start_date).days + 1):
                current_date = start_date + timedelta(days=i)
                day = current_date.day
                month = current_date.month
                year = current_date.year
            
                # Process each news item found for the current date/time
                for news_item in read_newspaper_news(newspaper, str(day) + "-" + str(month) + "-" + str(year), str(start_hour), "00", str(end_hour), "00")["items"]:
                    
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
                        print("contexto: " + str(context))
                        
                        news_item["description"] = remove_html(news_item["description"])
                        print(len(news_item["description"].split()))
                        
                        try:
                            print("title: " + news_item["headline"])
                            print(news_item["description"])
                            
                            # Generate synthetic description WITHOUT RAG context
                            document_NO_RAG = {
                            "RAG": 0,
                            "id_news": news_item["_id"],
                            "timestamp_llm": int(datetime.now().timestamp()),
                            "id_feature": id_feature,
                            "id_llm": id_llm,
                            "synthetic_description": exec_ollama(None, OLLAMA_IP, OLLAMA_PORT, "source_title: " + str(news_item["headline"]), "source_description: " + str(news_item["description"]), model_NO_RAG).get("synthetic_description", "N/A"),
                            }
                            print("NO RAG: " + str(document_NO_RAG))

                            # Generate synthetic description WITH RAG context
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
                    
                            # Send generated documents to the storage API
                            try:
                                if document_RAG:
                                    response = requests.post(endpoint_url, json=document_RAG)
                                    num_generated_news_RAG += 1
                                    
                                    if response.status_code == 201:
                                        print("Document inserted successfully:")
                                        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
                                    else:
                                        print(f"Error {response.status_code}: {response.text}")

                                if document_NO_RAG:
                                    response = requests.post(endpoint_url, json=document_NO_RAG)
                                    num_generated_news_NO_RAG += 1
                                    
                                    if response.status_code == 201:
                                        print("Document inserted successfully:")
                                        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
                                    else:
                                        print(f"Error {response.status_code}: {response.text}")

                            except requests.exceptions.RequestException as e:
                                print("Error connecting to API:", e)
                            
                        except Exception as e:
                            print("Error processing news with Ollama:", e)
                            error_count = error_count + 1

    # Print final execution statistics
    print("The number of Ollama errors was: " + str(error_count))
    print("The number of generated RAG news was: " + str(num_generated_news_RAG))
    print("The number of generated NO RAG news was: " + str(num_generated_news_NO_RAG))
    print("End time: " + str(datetime.now()))