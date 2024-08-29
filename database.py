from pymongo import MongoClient

def connect_to_mongodb(uri, db_name):
    try:
        client = MongoClient(uri)
        db = client[db_name]
        print("Connected to MongoDB")
        return db
    except Exception as e:
        print(f"Error: Could not connect to MongoDB.\n{e}")
        return None

def insert_document(db, collection_name, document):
    try:
        collection = db[collection_name]
        result = collection.insert_one(document)
        print(f"Inserted document with ID: {result.inserted_id}")
    except Exception as e:
        print(f"Error: Could not insert document.\n{e}")

def find_documents(db, collection_name, query=None):
    try:
        collection = db[collection_name]
        if query:
            cursor = collection.find(query)
        else:
            cursor = collection.find()

        return list(cursor)
    except Exception as e:
        print(f"Error: Could not retrieve documents.\n{e}")
        return []
