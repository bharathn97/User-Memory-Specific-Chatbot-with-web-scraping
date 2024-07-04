from datetime import datetime
from typing import List, Optional

from mongoengine import (ConnectionFailure, DateTimeField, Document,
                         ReferenceField, StringField, connect, disconnect)


class User(Document):
    username = StringField(unique=True, required=True)
    password = StringField(required=True)

class ChatHistory(Document):
    created_at = DateTimeField(default=datetime.utcnow)
    role = StringField(required=True)
    message = StringField(required=True)
    user = ReferenceField(User, reverse_delete_rule=2)

# Connect to MongoDB with error handling
try:
    connect("chatbot", host="mongodb+srv://bharathnagendrababu:wlDa8RXoZGEMoXgY@chatbotdb.pxummzl.mongodb.net/")
except ConnectionFailure:
    disconnect()
    connect("chatbot", host="mongodb+srv://bharathnagendrababu:wlDa8RXoZGEMoXgY@chatbotdb.pxummzl.mongodb.net/")

def register_user(username, password):
    user = User(username=username, password=password)
    try:
        user.save()
        return True
    except:
        return False

def get_user(username, password):
    user = User.objects(username=username, password=password).first()
    return user

def save_chat_history(user_id, role, message):
    user = User.objects(id=user_id).first()
    if user:
        chat_history = ChatHistory(user=user, role=role, message=message)
        chat_history.save()

def get_chat_history(user_id):
    user = User.objects(id=user_id).first()
    if user:
        history = ChatHistory.objects(user=user).order_by("created_at")
        return history
    return []

def init_db():
    # No initialization required for MongoDB
    pass
