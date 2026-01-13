from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import time
import os
from bson import ObjectId
import requests

# Context Manager API. Handles the storage of LLM-generated synthetic descriptions (RAG/NO-RAG) 
# in MongoDB and provides endpoints to merge and serve this synthetic data alongside the original real-world news.


# API for real news data
# Port for MongoDB
MONGO_PORT = 27017
# API host andd port for real news
API_HOST = "data_engine"
REAL_API_PORT = 5000

# Fetches raw news data from the external API for a specific date range
def read_newspaper_news(newspaper, date, start_hour, start_minute, end_hour, end_minute):

    params = "date=" + date + "&shour=" + start_hour + "&sminute=" + start_minute + "&ehour=" + end_hour + "&eminute=" + end_minute
    url = str("http://") + API_HOST + ":" + str(REAL_API_PORT) + "/news/" + newspaper + "?"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an error if HTTP code is 4xx or 5xx
        return response.json()  # Returns the response in JSON format
    except requests.exceptions.RequestException as e:
        print(f"Error calling endpoint: {e}")
        return None


app = Flask(__name__)

# Reads database credentials from a local text file
def read_credentials():
    with open('login.txt', 'r') as file:
        lines = file.read().strip().split('\n')
    user = lines[0].split('=')[1].strip()
    password = lines[1].split('=')[1].strip()
    return user, password

user, password = read_credentials()
mongo_uri = f"mongodb://{user}:{password}@noRelational_db:{MONGO_PORT}/"
client = MongoClient(mongo_uri)

# Database references
rag_db = client['llm_news_RAG']
no_rag_db = client['llm_news_NO_RAG']


# Endpoint to save a news item into the database (RAG or No-RAG collection)
@app.route('/newsLLM/<newspaper>', methods=['POST'])
def insert_document(newspaper):
   
    try:
        data = request.get_json(force=True)

        if not data:
            return jsonify({"error": "No valid JSON received"}), 400

        # Check if RAG flag is 1
        if int(data.get("RAG", "")) == 1:
            collection = rag_db[newspaper]
        else:
            collection = no_rag_db[newspaper]

        result = collection.insert_one(data)

        return jsonify({
            "message": f"Document inserted successfully in '{newspaper}'",
            "inserted_id": str(result.inserted_id),
            "id_news": data.get("id_news", "N/A"),
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Retrieves real news and merges them with the LLM-generated data stored in MongoDB
@app.route('/newsLLM/<newspaper>', methods=['GET'])
def get_llm_news(newspaper):

    rag = request.args.get('rag')
    date = request.args.get('date')              # dd-mm-yyyy
    start_hour = request.args.get('shour')   # start hour (0-23)
    start_minute = request.args.get('sminute') # start minute (0-59)
    end_hour = request.args.get('ehour')       # end hour optional (0-23)
    end_minute = request.args.get('eminute')   # end minute optional (0-59)


    if int(rag) == 1:
        collection = rag_db[newspaper]
    else:
        collection = no_rag_db[newspaper]
        
    news_response = read_newspaper_news(newspaper, date, start_hour, start_minute, end_hour, end_minute)
    real_news = news_response.get("items") if news_response else []

    entries = []
    for i in range(len(real_news)):
        
        query_filter = {"id_news": real_news[i].get("_id")}
        cursor = collection.find(query_filter, {'_id': 0, 'timestamp_llm': 1, 'id_feature': 1, 'synthetic_description': 1, "context": 1, "id_llm": 1})
    
        for entry in cursor:
            print(entry)
            entry["id_news"] = real_news[i].get("_id")
            entry['id_feature'] = str(entry['id_feature'])
            entry['headline'] = str(real_news[i].get("headline", ""))
            entry['synthetic_description'] = str(entry['synthetic_description'])
            entry['timestamp_llm'] = str(entry['timestamp_llm'])
            entry['id_llm'] = str(entry['id_llm'])
            if rag == '1':
                entry['context'] = (entry['context'])
            entry['real_description'] = real_news[i].get("description", "")
            entries.append(entry)

    return jsonify({
        "newspaper": newspaper,
        "date": date,
        "shour": start_hour,
        "sminute": start_minute,
        "ehour": end_hour,
        "eminute": end_minute,
        "total_items": len(entries),
        "items": entries    
    })


if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=7000)