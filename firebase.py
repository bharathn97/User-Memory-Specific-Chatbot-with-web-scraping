import firebase_admin
from firebase_admin import credentials, initialize_app

# Initialize Firebase (ensure initialization only once)
if not firebase_admin._apps:
    cred = credentials.Certificate('chatbot-63c48-firebase-adminsdk-f4rlt-489720f814.json')
    initialize_app(cred)

db = firestore.client()

# Your other Firebase-related operations here
