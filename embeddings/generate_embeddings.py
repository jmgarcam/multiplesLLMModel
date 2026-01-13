import chromadb
import requests
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta
import re

# Vector database ingestion script. Orchestrates the extraction of news articles from the data engine, 
# performs text sanitization and embedding generation using a multilingual Sentence Transformer model, 
# and populates ChromaDB collections to enable semantic search capabilities.

IP_API= "localhost"
API_PORT=5009

# Text sanitization utility.
def remove_html(text):

     # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', text)
    # Remove extra spaces or unnecessary line breaks
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text


# Retrieves the set of news articles for a specific source and time window
def read_newspaper_news(newspaper, date, start_hour, start_minute, end_hour, end_minute):

    params = "date="+date+"&shour="+start_hour+"&sminute="+start_minute+"&ehour="+end_hour+"&eminute="+end_minute
    url = str("http://")+IP_API+":"+str(API_PORT)+"/news/"+newspaper+"?"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an error if HTTP code is 4xx or 5xx
        return response.json()  # Returns the response in JSON format
    except requests.exceptions.RequestException as e:
        print(f"Error calling endpoint: {e}")
        return None

# Queries the data engine to obtain the catalogue of available newspaper sources 
def read_newspapers():
    url = str("http://")+IP_API+":"+str(API_PORT)+"/newspapers"
    try:
        response = requests.get(url)
        response.raise_for_status() 
        return response.json()  
    except requests.exceptions.RequestException as e:
        print(f"Error calling endpoint: {e}")
        return None

if __name__ == "__main__":
    print("Start - " + str(datetime.now()))
    # Update these dates as needed
    start_date = datetime.strptime("08-01-2026", "%d-%m-%Y")
    end_date = datetime.strptime("08-01-2026", "%d-%m-%Y")
   

    chroma_client = chromadb.HttpClient(host='localhost', port=8001)

    # Initialization of the embedding function using 'intfloat/multilingual-e5-large'
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="intfloat/multilingual-e5-large"
    )
    
    for newspaper in read_newspapers().get('newspapers'):
       
        print(newspaper + " - " + str(datetime.now()), flush=True)
        # Create or retrieve a distinct collection for each newspaper source
        collection = chroma_client.get_or_create_collection(name="real_news_data_"+str(newspaper), embedding_function=embedding_fn)

        count = 0
        current_day = start_date
        real_news = []
        texts = []
        while current_day <= end_date:
            
            print(current_day.strftime("%d-%m-%Y") + " --- " + str(datetime.now()), flush=True)          
            real_news=(read_newspaper_news(newspaper, str(current_day.strftime("%d-%m-%Y")), "00", "00", "23", "00").get("items"))
            print(len(real_news))

            for news_item in real_news:
                # Insert news into Chroma
                if news_item["description"] != None and news_item["description"] not in texts:

                    news_item["description"] = remove_html(news_item["description"])
                    texts.append(news_item["description"])
                    collection.add(documents= news_item["description"], ids=str(count))
                    count = count + 1
                    
                    
            current_day += timedelta(days=1)