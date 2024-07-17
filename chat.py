import json
import os
import textwrap
from datetime import datetime

import google.generativeai as genai
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from gradio_client import Client
from streamlit_option_menu import option_menu

from database import (get_chat_history, get_user, register_user,
                      save_chat_history)

load_dotenv()

# Configure the Gemini AI model
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")
chat = model.start_chat(history=[])

# Initialize the Hugging Face API client
hf_client = Client("bharathn97/hi")

def get_huggingface_response(question, username):
    result = hf_client.predict(
        message=question,
        system_message=(
            f"You are a friendly Chatbot and you also have the entire chat history remembered "
            f"and the chat history is the conversation of you with the user {username} which is the context and try to keep mentioning the user. "
            "Whenever asked anything related to previous chat history don't tell that you don't have memory of previous chat history "
            "you have the context and you can answer. "
            "Be precise in your answers and grammatically correct. If you find the answer in the context then don't mention that you found it in the context provided, "
            "just professionally answer generally. In case you are sure that such relevant conversation has never happened the answer then you say that such conversation has never occurred. "
            "In all other instances, you provide an answer to the best of your capability."
        ),
        max_tokens=512,
        temperature=0.7,
        top_p=0.95,
        api_name="/chat"
    )
    return result

def scrape_data(url):
    app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_API_KEY'))
    scraped_data = app.scrape_url(url, {'pageOptions': {'onlyMainContent': True}})
    if 'markdown' in scraped_data:
        return scraped_data['markdown']
    else:
        raise KeyError("The key 'markdown' does not exist in the scraped data.")

def save_raw_data(raw_data, timestamp, output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)
    raw_output_path = os.path.join(output_folder, f'rawData_{timestamp}.md')
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    return raw_output_path

def format_data(data):
    GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    system_message = """You are an intelligent text extraction and conversion assistant. Your task is to extract structured information 
                        from the given text and convert it into useful information. Please generate full detailed information and get all the key points."""

    user_message = f"Extract the following information from the provided text:\nPage content:\n\n{data}\n\n"
    prompt = system_message + "\n\n" + user_message

    response = model.generate_content(prompt)
    return response.text

# Streamlit app
st.set_page_config(page_title="Q&A and Web Scraping Demo")
st.header("Gemini LLM Application with Web Scraping")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['chat_history'] = []
    st.session_state['current_session_history'] = []

if not st.session_state['logged_in']:
    st.text_input("Username", key="username")
    st.text_input("Password", type="password", key="password")
    login_button = st.button("Login")
    register_button = st.button("Register")

    if login_button:
        user = get_user(st.session_state['username'], st.session_state['password'])
        if user:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user.id
            st.session_state['username_input'] = user.get('username') 
            chat_history = get_chat_history(user.id)
            st.session_state['chat_history'] = [(ch['role'], ch['message']) for ch in chat_history]
        else:
            st.error("Invalid username or password")

    if register_button:
        if register_user(st.session_state['username'], st.session_state['password']):
            st.success("User registered successfully!")
        else:
            st.error("Username already exists!")
else:
    # Place logout button at the side
    col1, col2 = st.columns([9, 1])
    with col2:
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['chat_history'] = []  # Clear chat history
            st.session_state['current_session_history'] = []  # Clear current session history
            st.session_state['username'] = ""
            st.session_state['password'] = ""

    with col1:
        input = st.text_input("Ask a question or input a URL:", key="input")
        url = st.text_input("Input URL:", key="url")

        col1_1, col1_2 = st.columns([1, 1])
        with col1_1:
            if st.button("Ask Question"):
                if input:
                    response = get_huggingface_response(input, st.session_state['username_input'])
                    st.session_state['current_session_history'].append(("assistant", response))
                    save_chat_history(st.session_state['user_id'], "assistant", response)
                    st.session_state['current_session_history'].append(("user", input))
                    save_chat_history(st.session_state['user_id'], "user", input)

        with col1_2:
            if st.button("Scrape URL"):
                if url:
                    try:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        raw_data = scrape_data(url)
                        save_raw_data(raw_data, timestamp)
                        formatted_data = format_data(raw_data)
                        st.session_state['current_session_history'].append(("assistant", formatted_data))
                        save_chat_history(st.session_state['user_id'], "assistant", formatted_data)
                        st.session_state['current_session_history'].append(("user", url))
                        save_chat_history(st.session_state['user_id'], "user", url)
                    except Exception as e:
                        st.session_state['current_session_history'].append(("assistant", f"An error occurred: {e}"))
                        save_chat_history(st.session_state['user_id'], "assistant", f"An error occurred: {e}")

    st.subheader("Chat History")
    if st.session_state['current_session_history']:
        st.markdown("### Current Session")
        for role, text in reversed(st.session_state['current_session_history']):
            if role == "assistant":
                st.markdown(f"<h4 style='color: green;'>{role}:</h4> {text}", unsafe_allow_html=True)
            else:
                st.markdown(f"<h4 style='color: red;'>{role}:</h4> {text}", unsafe_allow_html=True)
    if st.session_state['chat_history']:
        st.markdown("### Previous Sessions")
        for role, text in reversed(st.session_state['chat_history']):
            if role == "assistant":
                st.markdown(f"<h4 style='color: green;'>{role}:</h4> {text}", unsafe_allow_html=True)
            else:
                st.markdown(f"<h4 style='color: red;'>{role}:</h4> {text}", unsafe_allow_html=True)
