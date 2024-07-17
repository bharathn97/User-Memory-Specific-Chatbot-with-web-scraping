import os
import re
from datetime import datetime

import gradio as gr
from firebase_admin import credentials, firestore, initialize_app
from huggingface_hub import InferenceClient
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Initialize Firebase
cred = credentials.Certificate('../chatbot-63c48-firebase-adminsdk-f4rlt-489720f814.json')
initialize_app(cred)
db = firestore.client()

# Ensure the script is running from the correct directory
script_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_directory)

# Initialize Chroma vectorstore and persist it to './db'
chroma_db = Chroma(embedding_function=HuggingFaceEmbeddings(), persist_directory=script_directory)

# Hugging Face Inference Client
client = InferenceClient("HuggingFaceH4/zephyr-7b-beta")

# Initialize memory
memory = ConversationBufferWindowMemory(memory_key="chat_history", k=5, return_messages=True)

def retrieve_relevant_context(question):
    k = 100  # Always retrieve the top 100 relevant documents
    results = chroma_db.similarity_search(question, k=k)
    context = " ".join([result.page_content for result in results]) if results else ""
    return context

def store_conversation_in_db(user_message, bot_response, user_id):
    try:
        user_doc = Document(page_content=user_message, metadata={"role": "user"})
        bot_doc = Document(page_content=bot_response, metadata={"role": "assistant"})
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20, length_function=len)
        user_chunks = text_splitter.split_documents([user_doc])
        bot_chunks = text_splitter.split_documents([bot_doc])
        
        chroma_db.add_documents(user_chunks)
        chroma_db.add_documents(bot_chunks)
        
        chat_history_ref = db.collection('chat_history')
        chat_history_ref.add({
            'user_id': user_id,
            'role': 'user',
            'message': user_message,
            'created_at': datetime.utcnow()
        })
        chat_history_ref.add({
            'user_id': user_id,
            'role': 'assistant',
            'message': bot_response,
            'created_at': datetime.utcnow()
        })
    except Exception as e:
        print(f"Error storing conversation in DB: {e}")

def load_user_history(username):
    try:
        users_ref = db.collection('users')
        user_query = users_ref.where('username', '==', username).stream()
        user = list(user_query)
        if not user:
            return []
        
        user_doc = user[0]
        user_id = user_doc.id

        chat_history_ref = db.collection('chat_history')
        history_query = chat_history_ref.where('user_id', '==', user_id).order_by('created_at').stream()
        history = list(history_query)
        
        documents = []
        for entry in history:
            doc = Document(page_content=entry.to_dict()["message"], metadata={"role": entry.to_dict()["role"]})
            documents.append(doc)
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20, length_function=len)
        chunks = text_splitter.split_documents(documents)
        chroma_db.add_documents(chunks)
    except Exception as e:
        print(f"Error loading user history: {e}")

def extract_username(system_message):
    match = re.search(r"\buser ([\w\s]+)", system_message)
    if match:
        return match.group(1).strip()
    return None

def respond(
    message,
    history: list[tuple[str, str]],
    system_message,
    max_tokens,
    temperature,
    top_p,
):
    username = extract_username(system_message)
    if username:
        load_user_history(username)
    context = retrieve_relevant_context(message)
    
    messages = [{"role": "system", "content": system_message}]
    if context:
        messages.append({"role": "system", "content": "Context: " + context})

    for user_msg, bot_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})

    messages.append({"role": "user", "content": message})

    response = ""

    try:
        for msg in client.chat_completion(
            messages,
            max_tokens=max_tokens,
            stream=True,
            temperature=temperature,
            top_p=top_p,
        ):
            token = msg.choices[0].delta.content
            response += token
    except Exception as e:
        print(f"Error during chat completion: {e}")
        response = "Sorry, something went wrong. Please try again."

    if username:
        user_query = db.collection('users').where('username', '==', username).stream()
        user = list(user_query)
        user_doc = user[0] if user else None
        if user_doc:
            user_id = user_doc.id
            memory.save_context({"input": str(message)}, {"output": str(response)})
            store_conversation_in_db(message, response, user_id)
    
    yield response

demo = gr.ChatInterface(
    respond,
    additional_inputs=[
        gr.Textbox(value="You are a friendly Chatbot and you also have the entire chat history stored and the chat history is the conversation of you with the user which is the context and be precise with your answers. Only when asked any questions about previous conversation history answer or else don't. Whenever asked anything related to previous chat history don't tell that you don't have memory of previous chat history you have the context and you can answer. The context is your previous conversation history. Be precise in your answers and grammatically correct. If you find the answer in the context then don't mention that you found it in the context provided, just professionally answer generally. In case you are sure that such relevant conversation has never happened the answer then you say that such conversation has never occurred. In all other instances, you provide an answer to the best of your capability", label="System message"),
        gr.Slider(minimum=1, maximum=2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(minimum=0.1, maximum=4.0, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(
            minimum=0.1,
            maximum=1.0,
            value=0.95,
            step=0.05,
            label="Top-p (nucleus sampling)",
        ),
    ]
)

if __name__ == "__main__":
    demo.launch()