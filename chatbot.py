import streamlit as st
import requests

st.title("Chatbot basic")

chat_url = "http://127.0.0.1:8000/chat/"

# if "openai_model" not in st.session_state:
#     st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        payload = {
            "messages": [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        } # chat history
        headers = {
            "Content-Type": "application/json"
        }

        # No Stream approach
        stream = requests.post(chat_url, json=payload, headers=headers)
        response = stream.json()["reply"]
        st.markdown(response)

        # Stream approach
        # def get_stream_response():
        #     with requests.post(chat_url, json=payload, headers=headers, stream=True) as r:
        #         for chunk in r:
        #             yield chunk.decode('utf-8')
        # response = st.write_stream(get_stream_response)

    st.session_state.messages.append({"role": "assistant", "content": response})