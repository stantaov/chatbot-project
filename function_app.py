import azure.functions as func
from openai import OpenAI
import os
import json
import logging
import psycopg2
import uuid
from azure.storage.blob import BlobClient
from psycopg2.extras import RealDictCursor
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import chromadb


keyVaultName = os.environ.get("KEY_VAULT_NAME")
KVUri = f"https://{keyVaultName}.vault.azure.net"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=KVUri, credential=credential)

DB_NAME = client.get_secret('PROJ-DB-NAME').value
DB_USER = client.get_secret('PROJ-DB-USER').value
DB_PASSWORD = client.get_secret('PROJ-DB-PASSWORD').value
DB_HOST = client.get_secret('PROJ-DB-HOST').value
DB_PORT = client.get_secret('PROJ-DB-PORT').value
OPENAI_API_KEY = client.get_secret('PROJ-OPENAI-API-KEY').value
AZURE_STORAGE_SAS_URL = client.get_secret('PROJ-AZURE-STORAGE-SAS-URL').value
AZURE_STORAGE_CONTAINER = client.get_secret('PROJ-AZURE-STORAGE-CONTAINER').value
CHROMADB_HOST = client.get_secret('PROJ-CHROMADB-HOST').value
CHROMADB_PORT = client.get_secret('PROJ-CHROMADB-PORT').value

client = OpenAI(api_key=OPENAI_API_KEY)
model = "gpt-3.5-turbo"

DB_CONFIG = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
}

storage_account_sas_url = AZURE_STORAGE_SAS_URL
storage_container_name = AZURE_STORAGE_CONTAINER
storage_resource_uri = storage_account_sas_url.split('?')[0]
token = storage_account_sas_url.split('?')[1]


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="chat", methods=[func.HttpMethod.POST])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    stream = client.chat.completions.create(
        model=model,
        messages=req.get_json()['messages'],
        # stream=True,
    )

    return func.HttpResponse(stream.choices[0].message.content)


@app.route(route="load_chat", methods=[func.HttpMethod.GET])
async def load_chat(req: func.HttpRequest) -> func.HttpResponse:
    db = psycopg2.connect(**DB_CONFIG)
    try:
        
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, name, file_path, pdf_name, pdf_path, pdf_uuid FROM advanced_chats ORDER BY last_update DESC")
            rows = cursor.fetchall()

        records = []
        for row in rows:
            chat_id, name, file_path, pdf_name, pdf_path, pdf_uuid= row["id"], row["name"], row["file_path"], row["pdf_name"], row["pdf_path"], row["pdf_uuid"]

            blob_sas_url = f"{storage_resource_uri}/{storage_container_name}/{file_path}?{token}"
            blob_client = BlobClient.from_blob_url(blob_sas_url)

            if blob_client.exists():
                blob_data = blob_client.download_blob().readall()
                messages = json.loads(blob_data)
                records.append({"id": chat_id, "chat_name": name, "messages": messages, "pdf_name":pdf_name, "pdf_path":pdf_path, "pdf_uuid":pdf_uuid})
        db.close()
        return func.HttpResponse(body=json.dumps(records), status_code=200)

    except Exception as e:
        db.close()
        logging.error(e)
        response = {"detail": f"An error occurred: {str(e)}"}
        return func.HttpResponse(body=json.dumps(response), status_code=500)
    

@app.route(route="save_chat", methods=[func.HttpMethod.POST])
async def save_chat(req: func.HttpRequest) -> func.HttpResponse:
    db = psycopg2.connect(**DB_CONFIG)
    try:
        chat_id = req.get_json()["chat_id"]
        file_path = f"chat_logs/{chat_id}.json" 

        blob_sas_url = f"{storage_resource_uri}/{storage_container_name}/{file_path}?{token}"
        blob_client = BlobClient.from_blob_url(blob_sas_url)
        messages_data = json.dumps(req.get_json()["messages"], ensure_ascii=False, indent=4)
        blob_client.upload_blob(messages_data, overwrite=True)
      
        # Insert or update database record
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO advanced_chats (id, name, file_path, last_update, pdf_path, pdf_name, pdf_uuid)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET name = EXCLUDED.name, file_path = EXCLUDED.file_path, last_update = CURRENT_TIMESTAMP, pdf_path = EXCLUDED.pdf_path, pdf_name = EXCLUDED.pdf_name, pdf_uuid = EXCLUDED.pdf_uuid
                """,
                (req.get_json()["chat_id"], req.get_json()["chat_name"], file_path, req.get_json()["pdf_path"], req.get_json()["pdf_name"], req.get_json()["pdf_uuid"]),
            )
        db.commit()
        db.close()
        response = {"message": "Chat saved successfully"}
        return func.HttpResponse(body=json.dumps(response), status_code=200)
    except Exception as e:
        db.rollback()
        db.close()
        logging.error(e)
        response = {"detail": f"An error occurred: {str(e)}"}
        return func.HttpResponse(body=json.dumps(response), status_code=500)


@app.route(route="delete_chat", methods=[func.HttpMethod.POST])
async def delete_chat(req: func.HttpRequest) -> func.HttpResponse:
    db = psycopg2.connect(**DB_CONFIG)
    try:
        # Retrieve the file path before deleting the record    
        file_path = None
        with db.cursor() as cursor:
            cursor.execute("SELECT file_path, pdf_path FROM advanced_chats WHERE id = %s", (req.get_json()["chat_id"],))
            result = cursor.fetchone()
            if result:
                file_path = result[0]
                pdf_path = result[1]
            else:
                return func.HttpResponse(status_code=404, detail="Chat not found")

        # Delete the record from the database
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM advanced_chats WHERE id = %s", (req.get_json()["chat_id"],))
        db.commit()
        db.close()

        
        if file_path:
            blob_sas_url = f"{storage_resource_uri}/{storage_container_name}/{file_path}?{token}"
            blob_client = BlobClient.from_blob_url(blob_sas_url)
            if blob_client.exists():
                blob_client.delete_blob()

        if pdf_path:
            blob_sas_url = f"{storage_resource_uri}/{storage_container_name}/{pdf_path}?{token}"
            blob_client = BlobClient.from_blob_url(blob_sas_url)
            if blob_client.exists():
                blob_client.delete_blob()

        response = {"message": "Chat delete successfully"}
        return func.HttpResponse(body=json.dumps(response), status_code=200)

    except Exception as e:
        db.rollback()
        db.close()
        logging.error(e)
        response = {"detail": f"An error occurred: {str(e)}"}
        return func.HttpResponse(body=json.dumps(response), status_code=500)
    

@app.route(route="upload_pdf", methods=[func.HttpMethod.POST])
async def upload_pdf(req: func.HttpRequest) -> func.HttpResponse:

    file = req.files.get("file")
    if file.content_type != "application/pdf":
        logging.error(file.filename)
        logging.error(file.content_type)

        return func.HttpResponse(status_code=400, detail="Only PDF files are allowed.")

    try:
        pdf_uuid = str(uuid.uuid4())
        file_path = f"pdf_store/{pdf_uuid}_{file.filename}"
        temp_path = f"/tmp/{file.filename}"

        with open(temp_path, "wb") as f:
            f.write(file.read())
        blob_sas_url = f"{storage_resource_uri}/{storage_container_name}/{file_path}?{token}"
        blob_client = BlobClient.from_blob_url(blob_sas_url)
        blob_client.upload_blob(temp_path, overwrite=True)

        # Load and process PDF
        loader = PyPDFLoader(temp_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        texts = text_splitter.split_documents(documents)

        # Add to ChromaDB
        embedding_function = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = chroma_client.get_or_create_collection("langchain")
        vectorstore = Chroma(
            client=chroma_client,
            collection_name="langchain",
            embedding_function=embedding_function,
        )

        vectorstore.add_texts(
            [doc.page_content for doc in texts], 
            ids=[str(uuid.uuid4()) for _ in texts],
            metadatas=[{"pdf_uuid": pdf_uuid} for _ in texts]    
        )

        os.remove(temp_path)

        response = {"message": "File uploaded successfully", "pdf_path": file_path, "pdf_uuid":pdf_uuid}
        return func.HttpResponse(body=json.dumps(response), status_code=200)
    except Exception as e:
        logging.error(e)
        response = {"detail": f"An error occurred: {str(e)}"}
        return func.HttpResponse(body=json.dumps(response), status_code=500)
    
    
@app.route(route="rag_chat", methods=[func.HttpMethod.POST])
def rag_chat(req: func.HttpRequest) -> func.HttpResponse:

    embedding_function = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    collection = chroma_client.get_or_create_collection("langchain")
    vectorstore = Chroma(
        client=chroma_client,
        collection_name="langchain",
        embedding_function=embedding_function,
    )

    llm = ChatOpenAI(model=model, api_key=OPENAI_API_KEY)

    retriever = vectorstore.as_retriever(
            search_kwargs={"k": 5, "filter": {"pdf_uuid": req.get_json()['pdf_uuid']}}
        )
    
    ### Contextualize question ###
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )


    ### Answer question ###
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise."
        "\n\n"
        "{context}"
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    chat_history = []

    user_input = req.get_json()['messages'][-1]
    previous_chat = req.get_json()['messages'][:-1]

    for message in req.get_json()['messages']:
        if message["role"] == "user":
            chat_history.append(HumanMessage(content=message["content"]))
        if message["role"] == "assistant":
            chat_history.append(AIMessage(content=message["content"]))
    
    chain = rag_chain.pick("answer")

    response = chain.invoke({
        "chat_history":chat_history,
        "input":user_input
    })


    # Use StreamingResponse to return
    return func.HttpResponse(response, status_code=200)
    