from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel
from openai import OpenAI
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import json
import psycopg2
import os
import uuid
from psycopg2.extras import RealDictCursor
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage
from azure.storage.blob import BlobClient
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import chromadb

load_dotenv()

keyVaultName = os.environ.get("KEY_VAULT_NAME")
KVUri = f"https://{keyVaultName}.vault.azure.net"

credential = DefaultAzureCredential()
kv_client = SecretClient(vault_url=KVUri, credential=credential)

DB_NAME = kv_client.get_secret('PROJ-DB-NAME').value
DB_USER = kv_client.get_secret('PROJ-DB-USER').value
DB_PASSWORD = kv_client.get_secret('PROJ-DB-PASSWORD').value
DB_HOST = kv_client.get_secret('PROJ-DB-HOST').value
DB_PORT = kv_client.get_secret('PROJ-DB-PORT').value
OPENAI_API_KEY = kv_client.get_secret('PROJ-OPENAI-API-KEY').value
AZURE_STORAGE_SAS_URL = kv_client.get_secret('PROJ-AZURE-STORAGE-SAS-URL').value
AZURE_STORAGE_CONTAINER = kv_client.get_secret('PROJ-AZURE-STORAGE-CONTAINER').value
CHROMADB_HOST = kv_client.get_secret('PROJ-CHROMADB-HOST').value
CHROMADB_PORT = kv_client.get_secret('PROJ-CHROMADB-PORT').value
cosmos_endpoint = kv_client.get_secret('PROJ-COSMOSDB-ENDPOINT').value
cosmos_key = kv_client.get_secret('PROJ-COSMOSDB-KEY').value
cosmos_database = kv_client.get_secret('PROJ-COSMOSDB-DATABASE').value
cosmos_container = kv_client.get_secret('PROJ-COSMOSDB-CONTAINER').value


DB_CONFIG = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
}

chat_client = OpenAI(api_key=OPENAI_API_KEY)
model = "gpt-3.5-turbo"

llm = ChatOpenAI(model=model, api_key=OPENAI_API_KEY)

# LangChain setup
embedding_function = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
collection = chroma_client.get_or_create_collection("langchain")
vectorstore = Chroma(
    client=chroma_client,
    collection_name="langchain",
    embedding_function=embedding_function,
)

storage_account_sas_url = AZURE_STORAGE_SAS_URL
storage_container_name = AZURE_STORAGE_CONTAINER
storage_resource_uri = storage_account_sas_url.split('?')[0]
token = storage_account_sas_url.split('?')[1]

app = FastAPI()

# Request models
class ChatRequest(BaseModel):
    messages: List[dict]

class SaveChatRequest(BaseModel):
    chat_id: str
    chat_name: str
    messages: List[dict]
    pdf_name: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_uuid: Optional[str] = None

class DeleteChatRequest(BaseModel):
    chat_id: str

class RAGChatRequest(BaseModel):
    messages: List[dict]
    pdf_uuid: str

# Dependency to manage database connection
def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

@app.post("/chat/")
async def chat(request: ChatRequest):
    try:
        stream = chat_client.chat.completions.create(
            model=model,
            messages=request.messages,
            stream=True,
        )

        # if you don't want to stream the output
        # set the stream parameter to False in above function
        # and uncommnet the belowing line
        # return {"reply": response.choices[0].message.content}

        # Function to send out the stream data
        def stream_response():
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        # Use StreamingResponse to return
        return StreamingResponse(stream_response(), media_type="text/plain")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/load_chat/")
async def load_chat(db: psycopg2.extensions.connection = Depends(get_db)):
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, name, pdf_name, pdf_path, pdf_uuid FROM advanced_chats_new ORDER BY last_update DESC")
            rows = cursor.fetchall()

        records = []
        for row in rows:
            chat_id, name, pdf_name, pdf_path, pdf_uuid= row["id"], row["name"], row["pdf_name"], row["pdf_path"], row["pdf_uuid"]

            # Load from CosmosDB
            client = CosmosClient(cosmos_endpoint, cosmos_key)
            database = client.get_database_client(cosmos_database)
            container = database.get_container_client(cosmos_container)

            query = "SELECT * FROM c Where c.id = @chat_id"
            parameters = [{"name": "@chat_id", "value": chat_id}]
            items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

            if items:
                messages = json.loads(items[0]["messages"])

                records.append({"id": chat_id, "chat_name": name, "messages": messages, "pdf_name":pdf_name, "pdf_path":pdf_path, "pdf_uuid":pdf_uuid})

        return records

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/save_chat/")
async def save_chat(request: SaveChatRequest, db: psycopg2.extensions.connection = Depends(get_db)):
    try:
        messages_data = json.dumps(request.messages, ensure_ascii=False, indent=4)

        client = CosmosClient(cosmos_endpoint, cosmos_key)
        database = client.get_database_client(cosmos_database)
        container = database.get_container_client(cosmos_container)

        chat_data = {
            "id": request.chat_id,
            "messages": messages_data,
        }

        container.upsert_item(chat_data)
        
        # Insert or update database record
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO advanced_chats_new (id, name, last_update, pdf_path, pdf_name, pdf_uuid)
                VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET name = EXCLUDED.name, last_update = CURRENT_TIMESTAMP, pdf_path = EXCLUDED.pdf_path, pdf_name = EXCLUDED.pdf_name, pdf_uuid = EXCLUDED.pdf_uuid
                """,
                (request.chat_id, request.chat_name, request.pdf_path, request.pdf_name, request.pdf_uuid),
            )
        db.commit()
        return {"message": "Chat saved successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/delete_chat/")
async def delete_chat(request: DeleteChatRequest, db: psycopg2.extensions.connection = Depends(get_db)):
    try:
        # Retrieve the file path before deleting the record
        with db.cursor() as cursor:
            cursor.execute("SELECT pdf_path FROM advanced_chats_new WHERE id = %s", (request.chat_id,))
            result = cursor.fetchone()
            if result:
                pdf_path = result[0]
            else:
                raise HTTPException(status_code=404, detail="Chat not found")

        # Delete the record from the database
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM advanced_chats_new WHERE id = %s", (request.chat_id,))
        db.commit()

        # Delete the associated file, if it exists
        # if file_path and os.path.exists(file_path):
        #     os.remove(file_path)
        
        client = CosmosClient(cosmos_endpoint, cosmos_key)
        database = client.get_database_client(cosmos_database)
        container = database.get_container_client(cosmos_container)

        container.delete_item(
            item=request.chat_id,           
            partition_key=request.chat_id
        )

        if pdf_path:
            blob_sas_url = f"{storage_resource_uri}/{storage_container_name}/{pdf_path}?{token}"
            blob_client = BlobClient.from_blob_url(blob_sas_url)
            if blob_client.exists():
                blob_client.delete_blob()

        return {"message": "Chat deleted successfully"}

    except HTTPException:
        # Reraise known exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        pdf_uuid = str(uuid.uuid4())
        file_path = f"pdf_store/{pdf_uuid}_{file.filename}"
        os.makedirs("pdf_store", exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(await file.read())
        blob_sas_url = f"{storage_resource_uri}/{storage_container_name}/{file_path}?{token}"
        blob_client = BlobClient.from_blob_url(blob_sas_url)
        blob_client.upload_blob(file_path, overwrite=True)

        # Load and process PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        texts = text_splitter.split_documents(documents)

        # Add to ChromaDB
        vectorstore.add_texts(
            [doc.page_content for doc in texts], 
            ids=[str(uuid.uuid4()) for _ in texts],
            metadatas=[{"pdf_uuid": pdf_uuid} for _ in texts]    
        )

        os.remove(file_path)

        return {"message": "File uploaded successfully", "pdf_path": file_path, "pdf_uuid":pdf_uuid}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/rag_chat/")
async def rag_chat(request: RAGChatRequest):

    retriever = vectorstore.as_retriever(
            search_kwargs={"k": 5, "filter": {"pdf_uuid": request.pdf_uuid}}
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

    user_input = request.messages[-1]
    previous_chat = request.messages[:-1]

    for message in request.messages:
        if message["role"] == "user":
            chat_history.append(HumanMessage(content=message["content"]))
        if message["role"] == "assistant":
            chat_history.append(AIMessage(content=message["content"]))
    
    # response = rag_chain.invoke({
    #     "chat_history":chat_history,
    #     "input":user_input
    # })

    chain = rag_chain.pick("answer")

    stream = chain.stream({
        "chat_history":chat_history,
        "input":user_input
    })

    def stream_response():
            for chunk in stream:
                yield chunk

    # Use StreamingResponse to return
    return StreamingResponse(stream_response(), media_type="text/plain")

