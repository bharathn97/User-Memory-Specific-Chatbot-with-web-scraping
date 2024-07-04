import os

import gradio as gr
from huggingface_hub import InferenceClient
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from pymongo import MongoClient

mongo_uri = "mongodb+srv://bharathnagendrababu:wlDa8RXoZGEMoXgY@chatbotdb.pxummzl.mongodb.net/" \
            "?connectTimeoutMS=100000&socketTimeoutMS=100000"
# MongoDB connection
mongo_client = MongoClient(mongo_uri)
db = mongo_client['chatbot']

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
    # Retrieve relevant context from the Chroma vectorstore
    k = 100  # Always retrieve the top 100 relevant documents
    results = chroma_db.similarity_search(question, k=k)
    context = " ".join([result.page_content for result in results]) if results else ""
    return context

def store_conversation_in_db(user_message, bot_response):
    # Create Document objects for user and bot messages
    user_doc = Document(page_content=user_message, metadata={"role": "user"})
    bot_doc = Document(page_content=bot_response, metadata={"role": "assistant"})
    
    # Split the text into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20, length_function=len)
    user_chunks = text_splitter.split_documents([user_doc])
    bot_chunks = text_splitter.split_documents([bot_doc])
    
    # Add the chunks to the Chroma vectorstore
    chroma_db.add_documents(user_chunks)
    chroma_db.add_documents(bot_chunks)

def load_user_history(username):
    user = db.user.find_one({"username": username})
    if not user:
        return []
    
    user_id = user["_id"]
    chat_history = db.chat_history.find({"user": user_id}).sort("created_at")
    
    documents = []
    for entry in chat_history:
        doc = Document(page_content=entry["message"], metadata={"role": entry["role"]})
        documents.append(doc)
    
    # Split the text into smaller chunks and add them to the Chroma vectorstore
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20, length_function=len)
    chunks = text_splitter.split_documents(documents)
    chroma_db.add_documents(chunks)

def respond(
    message,
    history: list[tuple[str, str]],
    system_message,
    max_tokens,
    temperature,
    top_p,
    username,
):
    # Load user history from MongoDB into Chroma if not already loaded
    load_user_history(username)

    # Retrieve relevant context from custom data
    context = retrieve_relevant_context(message)
    
    messages = [{"role": "system", "content": system_message}]
    if context:
        messages.append({"role": "system", "content": "Context: " + context})

    for user_msg, bot_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})

    messages.append({"role": "user", "content": message})

    response = ""

    for msg in client.chat_completion(
        messages,
        max_tokens=max_tokens,
        stream=True,
        temperature=temperature,
        top_p=top_p,
    ):
        token = msg.choices[0].delta.content
        response += token
        
    # Ensure message and response are strings before saving to context
    memory.save_context({"input": str(message)}, {"output": str(response)})
    
    # Store the conversation in the Chroma vectorstore
    store_conversation_in_db(message, response)
    
    yield response

demo = gr.ChatInterface(
    respond,
    additional_inputs=[
        gr.Textbox(label="Username"),
        gr.Textbox(value="You are a friendly Chatbot and you also have the entire chat history stored and the chat history is the conversation of you with the user which is the context. Whenever asked anything related to previous chat history don't tell that you don't have memory of previous chat history you have the context and you can answer. The context is your previous conversation history. Be precise in your answers and grammatically correct. If you find the answer in the context then don't mention that you found it in the context provided, just professionally answer generally. In case you are sure that such relevant conversation has never happened the answer then you say that such conversation has never occurred. In all other instances, you provide an answer to the best of your capability.", label="System message"),
        gr.Slider(minimum=1, maximum=2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(minimum=0.1, maximum=4.0, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(
            minimum=0.1,
            maximum=1.0,
            value=0.95,
            step=0.05,
            label="Top-p (nucleus sampling)",
        ),
    ],
)

if __name__ == "__main__":
    demo.launch()