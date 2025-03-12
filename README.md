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

#### **Step 1: Set Up Environment Variables**
Store your `OPENAI_API_KEY`, **Database Credentials** and **Storage SAS token** in a `.env` file.

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

#### **Step 2: Start Sartup Script**

```bash
chmod +x setup.sh
./setup.sh <PAT_token> <repo_url> <branch_name> <password>
```