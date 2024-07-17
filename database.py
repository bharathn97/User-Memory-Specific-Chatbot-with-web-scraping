from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

if not firebase_admin._apps:
    cred = credentials.Certificate('chatbot-63c48-firebase-adminsdk-f4rlt-489720f814.json')
    initialize_app(cred)

db = firestore.client()

def register_user(username, password):
    users_ref = db.collection('users')
    query = users_ref.where('username', '==', username).limit(1)
    existing_user = list(query.get())
    
    if existing_user:
        return False
    
    user_data = {
        'username': username,
        'password': password
    }
    users_ref.add(user_data)
    return True


def get_user(username, password):
    users_ref = db.collection('users')
    query = users_ref.where('username', '==', username).where('password', '==', password).limit(1).stream()
    user = next(query, None)
    if user:
        return user
    return None

def save_chat_history(user_id, role, message):
    chat_history_ref = db.collection('chat_history')
    chat_data = {
        'created_at': datetime.utcnow(),
        'role': role,
        'message': message,
        'user_id': user_id
    }
    chat_history_ref.add(chat_data)

def get_chat_history(user_id):
    chat_history_ref = db.collection('chat_history')
    history = chat_history_ref.where('user_id', '==', user_id).order_by('created_at').stream()
    return [doc.to_dict() for doc in history]

def init_db():
    # No initialization required for Firestore
    pass
