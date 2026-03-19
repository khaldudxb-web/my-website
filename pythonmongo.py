from pymongo import MongoClient
client = MongoClient("mongodb+srv://khaldudxb_db_user:5zWzdlnZYrOJnXLe@mongodbcluster.clyqmaj.mongodb.net/")
print("Connection Successful")

db = client["Aviation"]
print("connected to aviation")

aviation_data = db["Aviation_Data"]