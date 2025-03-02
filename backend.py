from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from openai import OpenAI
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import json
import psycopg2
import os
from psycopg2.extras import RealDictCursor
from typing import List

load_dotenv()

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST"),
    "port": os.environ.get("DB_PORT"),
}

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
model = "gpt-3.5-turbo"

app = FastAPI()

# Request models
class ChatRequest(BaseModel):
    messages: List[dict]

class SaveChatRequest(BaseModel):
    chat_id: str
    chat_name: str
    messages: List[dict]

class DeleteChatRequest(BaseModel):
    chat_id: str

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
        stream = client.chat.completions.create(
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
            cursor.execute("SELECT id, name, file_path FROM chats ORDER BY last_update DESC")
            rows = cursor.fetchall()

        records = []
        for row in rows:
            chat_id, name, file_path = row["id"], row["name"], row["file_path"]
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    messages = json.load(f)
                records.append({"id": chat_id, "chat_name": name, "messages": messages})

        return records

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/save_chat/")
async def save_chat(request: SaveChatRequest, db: psycopg2.extensions.connection = Depends(get_db)):
    try:
        file_path = f"chat_logs/{request.chat_id}.json"
        os.makedirs("chat_logs", exist_ok=True)
        
        # Save messages to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(request.messages, f, ensure_ascii=False, indent=4)
        
        # Insert or update database record
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chats (id, name, file_path, last_update)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id)
                DO UPDATE SET name = EXCLUDED.name, file_path = EXCLUDED.file_path, last_update = CURRENT_TIMESTAMP
                """,
                (request.chat_id, request.chat_name, file_path),
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
        file_path = None
        with db.cursor() as cursor:
            cursor.execute("SELECT file_path FROM chats WHERE id = %s", (request.chat_id,))
            result = cursor.fetchone()
            if result:
                file_path = result[0]
            else:
                raise HTTPException(status_code=404, detail="Chat not found")

        # Delete the record from the database
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM chats WHERE id = %s", (request.chat_id,))
        db.commit()

        # Delete the associated file, if it exists
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        return {"message": "Chat deleted successfully"}

    except HTTPException:
        # Reraise known exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
