import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


load_dotenv()

def check_mongo_connection(uri):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        print("MongoDB connection: SUCCESS")
        return client
    except ConnectionFailure:
        print("MongoDB connection: FAILED")
        return None

def list_databases(client):
    try:
        dbs = client.list_database_names()
        print("Databases:")
        for db in dbs:
            print(f" - {db}")
    except Exception as e:
        print(f"Error listing databases: {e}")

if __name__ == "__main__":
    # Replace the URI string with your MongoDB deployment's connection string.
    mongo_uri = os.getenv("MONGODB_URI")
    # mongo_uri = "mongodb+srv://anshdhalla219:BpKWaEEwNZamHzyt@cluster0.sm5qgyd.mongodb.net/"
    print(f"Connecting to MongoDB...{mongo_uri}")
    client = check_mongo_connection(mongo_uri)


    # if client:
    #     list_databases(client)
    #     db = client['recruiit']

    #     # Show collections in 'Recruiit' database
    #     print("Collections in 'Recruiit' database:")
    #     collections = db.list_collection_names()
    #     for coll in collections:
    #         print(f" - {coll}")

        # Show first 4 documents from 'candidate' collection
        # print("\nFirst 4 documents in 'candidate' collection:")
        # candidate_collection = db['candidate']
        # for doc in candidate_collection.find().limit(4):
        #     print(doc)