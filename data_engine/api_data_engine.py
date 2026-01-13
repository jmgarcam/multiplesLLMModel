# Data Engine API serving as the primary interface for the "real world" news dataset stored in MongoDB.
# It provides endpoints for temporal retrieval, insertion, and updates of raw news articles.
from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import time
import os
from bson import ObjectId

# Port for MongoDB
MONGO_PORT = 27017

app = Flask(__name__)


# Utility to parse database authentication credentials from a local configuration file.
def read_credentials():
    with open('login.txt', 'r') as f:
        lines = f.read().strip().split('\n')
    user = lines[0].split('=')[1].strip()
    password = lines[1].split('=')[1].strip()
    return user, password

user, password = read_credentials()
mongo_uri = f"mongodb://{user}:{password}@noRelational_db:{MONGO_PORT}/"
client = MongoClient(mongo_uri)
db = client['newspapers_db']


# Retrieves the list of available newspaper sources by querying MongoDB collection names.
@app.route('/newspapers', methods=['GET'])
def list_newspapers():
    collections = db.list_collection_names()
    return jsonify({"newspapers": collections})


# Retrieves news articles for a specific newspaper within a defined temporal window.
# Handles parsing of date parameters and constructs the corresponding timestamp filters.
@app.route('/news/<newspaper>', methods=['GET'])
def get_newspaper_items(newspaper):
    collection = db[newspaper]

    date_str = request.args.get('date')        
    shour_str = request.args.get('shour')         
    sminute_str = request.args.get('sminute')     
    ehour_str = request.args.get('ehour')    
    eminute_str = request.args.get('eminute')

    query_filter = {}

    if date_str and shour_str and sminute_str:
       
        try:
            date_dt = datetime.strptime(date_str, "%d-%m-%Y")
            start_h = int(shour_str)
            start_m = int(sminute_str)

            if ehour_str:
                end_h = int(ehour_str)
            else:
                end_h = start_h

            if eminute_str:
                end_m = int(eminute_str)
            else:
                end_m = start_m

            start_dt = date_dt.replace(hour=start_h, minute=start_m, second=0)

            if (end_h < start_h) or (end_h == start_h and end_m < start_m):
                # Crosses midnight → add one day to end time
                end_dt = (date_dt + timedelta(days=1)).replace(hour=end_h, minute=end_m, second=59)
            else:
                end_dt = date_dt.replace(hour=end_h, minute=end_m, second=59)

            ts_start = int(time.mktime(start_dt.timetuple()))
            ts_end = int(time.mktime(end_dt.timetuple()))

            query_filter = {"date_stored": {"$gte": ts_start, "$lte": ts_end}}

        except ValueError:
            return jsonify({"error": "Incorrect format. Date dd-mm-yyyy, hour 0-23 and minute 0-59"}), 400
    
    else:
        start_h = 99
        start_m = 99
        end_h = 99
        end_m = 99

    cursor = collection.find(query_filter, {'_id': 1, 'headline': 1, 'description': 1, 'fecha': 1, 'date_stored': 1})
    items = []
    for item in cursor:
        item['_id'] = str(item['_id'])  
        item['headline'] = str(item['headline'])
        item['date_stored'] = str(item['date_stored'])
        items.append(item)

    return jsonify({
        "newspaper": newspaper,
        "date": date_str,
        "ihour": start_h,
        "iminute": start_m,
        "ehour": end_h,
        "eminute": end_m,
        "total_items": len(items),
        "items": items
    })


# Updates a specific news entry identified by its unique ID with new data fields.
@app.route('/news/<newspaper>/<id>', methods=['PUT'])
def update_item(newspaper, id):
    collection = db[newspaper]
    new_data = request.get_json()

    if not new_data:
        return jsonify({"error": "No data received for update"}), 400

    try:
        query_filter = {"_id": ObjectId(id)}
    except Exception:
        query_filter = {"_id": id}

    result = collection.update_one(query_filter, {"$set": new_data})

    if result.matched_count == 0:
        return jsonify({"error": f"No entry found with id {id}"}), 404

    return jsonify({"message": f"Entry {id} updated successfully"}), 200


# Inserts a new raw news document into the specified newspaper's collection.
@app.route('/news/<newspaper>', methods=['POST'])
def insert_item(newspaper):
    collection = db[newspaper]
    data = request.get_json()
    try:
        if not data:
            return jsonify({"error": "No data received for update"}), 400

        result = collection.insert_one(data)

        return jsonify({
                "message": f" Document inserted successfully in '{newspaper}'"
        }), 201
   
    except Exception as e:
        return jsonify({"error": str(e)}), 500


app.run(host='0.0.0.0', port=5000)