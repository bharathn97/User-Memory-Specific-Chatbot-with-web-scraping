## User-Memory-Specific-Chatbot-with-web-scraping

This project implements a user-specific chatbot integrated with web scraping capabilities. The chatbot utilizes several APIs and technology stacks to enhance its functionality.

## APIs Used

## 1.Gemini AI API
Used for natural language processing and generating responses based on historical chat data.
## 2.Hugging Face API
Provides models for conversational AI, enhancing the chatbot's ability to understand and respond to user queries.
## 3.Firecrawl API
Enables web scraping functionality to extract structured data from web pages specified by the user.

## Technology Stacks

1.Python: Programming language used for backend development and integrating APIs.

2.Streamlit: Framework used for building and deploying the web application interface.

3.Firebase Firestore: NoSQL database used for storing user chat history and other relevant data.

4.Gradio: Provides an interactive UI for the chatbot, enhancing user interaction experience.

LangChain Community Libraries: Used for natural language processing tasks such as text splitting and vector embedding.

Google Generative AI (GenAI): Utilized for content generation and text extraction tasks within the application.

Functionality

The chatbot maintains a memory of previous conversations with users.Users can interact with the chatbot by asking questions or inputting URLs for web scraping operations. The extracted data is processed and presented back to the user in a structured format.
