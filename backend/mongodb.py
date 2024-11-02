# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
# from dotenv import load_dotenv
# import os
# from pathlib import Path

# # Get the path to the current file's directory
# base_dir = Path(__file__).resolve().parent

# # Construct the path to the .env file
# env_file = base_dir / '.env'

# # Load environment variables from .env file
# load_dotenv(dotenv_path=env_file, override=True)

# uri = f"mongodb+srv://admin:{os.getenv('MONGODB_PASSWORD')}@practices.y36ua.mongodb.net/?retryWrites=true&w=majority"

# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))

# # Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
# except Exception as e:
#     print(e)
