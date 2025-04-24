# Chatbot-project

Stage 8 - RAG Chatbot(Serverless Backend - CosmosDB and Azure Function)

At this stage, we will move the chat history from files in the Blob Storage to the CosmosDB.

For the database we will Remove the `file_path` column in the `advanced_chats` table:
```
CREATE TABLE IF NOT EXISTS advanced_chats_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    -- file_path TEXT NOT null,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pdf_path TEXT,
    pdf_name TEXT,
    pdf_uuid TEXT
)
```
Or if you want you can create a new table called `advanced_chats_new` using above query.

> **Note:** The codes in this branch is just the showcase that how to interact with CosmosDB, so we **only** store the chat history to the CosmosDB. Actually students can upload all the metadata to the CosmosDB to replace the PostgreSQL. In that case, we also make the database fully serverless.

Since we need to add the CosmosDB connection in the Azure Function, we also need to store the `PROJ-COSMOSDB-ENDPOINT`, `PROJ-COSMOSDB-KEY`, `PROJ-COSMOSDB-DATABASE`, `PROJ-COSMOSDB-CONTAINER` in the **Azure Key Vault**.

When deploy to the Azure function, don't forget to upload the `local.settings.json` to the cloud.

And since the front-end is still running on the instance and it needs to connect to the Azure Function APP, so let's store the Function URL in the Azure KeyVault as well.
In this case, to allow the front-end able to load the URL from secret, we need to update the front-end codes a little bit and store the `KEY_VAULT_NAME` in the `.env` file on the instance where we run the front-end.
Please make sure your instance has the permission to load the secret from the KeyVault.

Now, the following secrets should be created in your Azure KeyVault:

```
PROJ-DB-NAME
PROJ-DB-USER
PROJ-DB-PASSWORD
PROJ-DB-HOST
PROJ-DB-PORT
PROJ-OPENAI-API-KEY
PROJ-AZURE-STORAGE-SAS-URL
PROJ-AZURE-STORAGE-CONTAINER
PROJ-CHROMADB-HOST
PROJ-CHROMADB-PORT
PROJ-BASE-ENDPOINT-URL
PROJ-COSMOSDB-ENDPOINT
PROJ-COSMOSDB-KEY
PROJ-COSMOSDB-DATABASE
PROJ-COSMOSDB-CONTAINER
```
