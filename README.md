# Chatbot Project

## RAG Chatbot with Chat History

### Stage Introduction

A **RAG (Retrieval-Augmented Generation) chatbot** using Streamlit and FastAPI. At this stage, we introduce the ability for users to upload PDF files in addition to regular chatting. This allows them to ask questions specifically about the content of those documents.

![stage1-4](https://weclouddata.s3.us-east-1.amazonaws.com/cloud/project-stages/stage1-4.png)

Under the hood, the system uses a **vector store (Chroma)** to retrieve the most relevant context from uploaded PDFs. This retrieval step enhances the chatbot’s ability to provide accurate, context-aware answers, bridging the gap between simple conversation and document-focused queries.

This enhancement integrates seamlessly with our existing setup—Streamlit for the user interface, FastAPI for business logic, and PostgreSQL for data storage—while laying the foundation for further expansion.

> **Note:** Some LLM-related concepts introduced in this stage may seem complex. However, our main goal is to get the project running, and fully understanding the LLM integration is **optional**. If you’re interested, feel free to explore the code and additional resources to enhance your project, but don’t worry if you don’t grasp everything right away.

---

### How to Get Started

In this stage, we will create a **new** table called `advanced_chats` in the database using the following schema:

```sql
CREATE TABLE IF NOT EXISTS advanced_chats (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pdf_path TEXT,
    pdf_name TEXT,
    pdf_uuid TEXT
);
```

Alternatively, you can **add the extra columns** to the `chats` table created in Stage 3 instead of creating a new table.

#### **Step 1: Set Up Environment Variables**
Store your `OPENAI_API_KEY` and **Database Credentials** in a `.env` file.

Your `.env` file should look like this:

```env
OPENAI_API_KEY=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
AZURE_STORAGE_SAS_URL=
AZURE_STORAGE_CONTAINER=
```

#### **Step 2: Install Dependencies**
To use **ChromaDB**, install it via `pip`. The necessary packages are listed in `requirements.txt`, so you can install everything by running:

```bash
pip install -r requirements.txt
```

#### **Step 3: Start ChromaDB**
To enable retrieval, we need to start ChromaDB. Use the following command to start the Chroma server:

```bash
chroma run --path /db_path
```

Replace `/db_path` with the directory where you want to store the data, e.g., `chromadb`.

#### **Step 4: Start the Backend**
Next, start the FastAPI backend:

```bash
uvicorn backend:app --reload --port 5000
```

> **Note:** Compared to the last stage, we have added the `--port 5000` parameter. Since ChromaDB uses port **8000** by default, this prevents a port conflict.

#### **Step 5: Start the Streamlit App**
Finally, run the Streamlit app:

```bash
streamlit run chatbot.py
```