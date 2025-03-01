import streamlit as st
import uuid
import requests


# Initialize session state
if "history_chats" not in st.session_state:
    st.session_state["history_chats"] = []
    # [{"id": "chat_id", "messages": [{"role": "user", "content": "message"}, ...]}, ...]
if "current_chat" not in st.session_state:
    st.session_state["current_chat"] = None
    # chat_id
if "chat_names" not in st.session_state:
    st.session_state["chat_names"] = {}
    # {"chat_id": "chat_name", ...}

# Functions to manage chats

def load_chats_from_db():
    response = requests.get("http://127.0.0.1:8000/load_chat/")

    if response.status_code == 200:
        records = response.json()
        for record in records:
            chat_id = record['id']
            messages = record['messages']
            name = record['chat_name']
            st.session_state["history_chats"].append({"id": chat_id, "messages": messages})
            st.session_state["chat_names"][chat_id] = name
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")

def save_chat_to_db(chat_id, chat_name, messages):
    payload = {
                "chat_id": chat_id,
                "chat_name": chat_name,
                "messages": messages
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post("http://127.0.0.1:8000/save_chat/", json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Failed to save data. Status code: {response.status_code}")


def create_chat(chat_name):
    new_chat_id = str(uuid.uuid4())
    new_chat = {"id": new_chat_id, "messages": []}
    st.session_state["history_chats"].insert(0, new_chat)
    st.session_state["chat_names"][new_chat_id] = chat_name
    st.session_state["current_chat"] = new_chat_id
    
    save_chat_to_db(new_chat_id, chat_name, [])
    

def delete_chat():
    if st.session_state["current_chat"]:
        chat_id = st.session_state["current_chat"]
        # Remove chat from history
        st.session_state["history_chats"] = [
            chat for chat in st.session_state["history_chats"] if chat["id"] != chat_id
        ]
        del st.session_state["chat_names"][chat_id]
        # Remove chat from database
        payload = {
                "chat_id": chat_id
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post("http://127.0.0.1:8000/delete_chat/", json=payload, headers=headers)

        if response.status_code != 200:
            print(f"Failed to delete data. Status code: {response.status_code}")
        # Update current chat
        st.session_state["current_chat"] = (
            st.session_state["history_chats"][0]["id"] if st.session_state["history_chats"] else None
        )

def select_chat(chat_id):
    st.session_state["current_chat"] = chat_id

# Load chats from database
load_chats_from_db()

# Sidebar
with st.sidebar:
    st.title("Chat Management")
    chat_name = st.text_input("Enter Chat Name:", key="new_chat_name")
    if st.button("Create New Chat"):
        if chat_name.strip():
            create_chat(chat_name.strip())
        else:
            st.warning("Chat name cannot be empty.")
    if st.session_state["history_chats"]:
        chat_options = {
            chat["id"]: st.session_state["chat_names"][chat["id"]]
            for chat in st.session_state["history_chats"]
        }
        selected_chat = st.radio(
            "Select Chat",
            options=list(chat_options.keys()),
            format_func=lambda x: chat_options[x],
            # index=list(chat_options.keys()).index(st.session_state["current_chat"]),
            key="chat_selector",
            on_change=lambda: select_chat(st.session_state.chat_selector),
        )
        st.session_state["current_chat"] = selected_chat

        st.button("Delete Chat", on_click=delete_chat)

# Main Content
st.title("Chatbot Application")

if st.session_state["current_chat"]:
    chat_id = st.session_state["current_chat"]
    chat_name = st.session_state["chat_names"][chat_id]
    st.subheader(f"Current Chat: {chat_name}")

    # Get current chat
    current_chat = next(
        (chat for chat in st.session_state["history_chats"] if chat["id"] == chat_id),
        None,
    )

    if current_chat:
        for message in current_chat["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Your Message:"):
            current_chat["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                payload = {
                    "messages": [
                        {"role": m["role"], "content": m["content"]}
                        for m in current_chat["messages"]
                    ]
                }
                headers = {"Content-Type": "application/json"}

                # No Stream approach
                # stream = requests.post(chat_url, json=payload, headers=headers)
                # response = stream.json()["reply"]
                # st.markdown(response)

                # Stream approach
                def get_stream_response():
                    with requests.post("http://127.0.0.1:8000/chat/", json=payload, headers=headers, stream=True) as r:
                        for chunk in r:
                            yield chunk.decode("utf-8")

                response = st.write_stream(get_stream_response)
                current_chat["messages"].append({"role": "assistant", "content": response})
                save_chat_to_db(chat_id, chat_name, current_chat["messages"])
else:
    st.write("No chat selected. Use the sidebar to create or select a chat.")