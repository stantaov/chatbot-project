from openai import OpenAI
import streamlit as st
import os
from dotenv import load_dotenv

# Set page title
st.title("Chatbot basic")

# Load environment variables
load_dotenv()

# Create OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Set up session state
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

# Set up chat messages
if "messages" not in st.session_state:
    st.session_state.messages = [] 
    # [{"role": "user" or "assistant", "content": "message"}, ...]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response from OpenAI
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)
    # Display response
    st.session_state.messages.append({"role": "assistant", "content": response})