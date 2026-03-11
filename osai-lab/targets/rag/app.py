# FastAPI RAG app - intentionally vulnerable
# Vulns: prompt injection via doc ingestion, path traversal on upload,
#        no output sanitization, full doc content returned in context

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import chromadb
import httpx
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable RAG API")

chroma_client = None
collection = None


@app.on_event("startup")
async def startup():
    global chroma_client, collection

    # Retry connection to ChromaDB (may still be starting)
    for attempt in range(30):
        try:
            chroma_client = chromadb.HttpClient(
                host=os.getenv("CHROMADB_HOST", "localhost"),
                port=int(os.getenv("CHROMADB_PORT", "8000")),
            )
            collection = chroma_client.get_or_create_collection("docs")
            logger.info("Connected to ChromaDB")
            break
        except Exception as e:
            logger.info(f"Waiting for ChromaDB (attempt {attempt + 1}/30): {e}")
            time.sleep(2)
    else:
        raise RuntimeError("Could not connect to ChromaDB after 30 attempts")

    # Ingest seed documents on startup
    docs_dir = os.getenv("DOCS_DIR", "/app/docs")
    if os.path.isdir(docs_dir):
        for fname in os.listdir(docs_dir):
            fpath = os.path.join(docs_dir, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r", errors="ignore") as f:
                    content = f.read()
                try:
                    collection.add(documents=[content], ids=[fname])
                    logger.info(f"Ingested seed doc: {fname}")
                except Exception:
                    logger.info(f"Seed doc already exists: {fname}")


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    logger.info(f"Ingest request: filename={file.filename}")

    # VULN: No file type validation
    # VULN: Path traversal - filename used directly
    save_path = f"/app/uploads/{file.filename}"
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Ingest raw content - no sanitization
    collection.add(
        documents=[content.decode("utf-8", errors="ignore")], ids=[file.filename]
    )
    return {"status": "ingested", "path": save_path}


@app.post("/query")
async def query(payload: dict):
    user_query = payload.get("query", "")
    logger.info(f"Query request: {user_query}")

    # VULN: User input injected directly into LLM prompt
    # VULN: Retrieved docs injected without sanitization
    results = collection.query(query_texts=[user_query], n_results=5)
    context = "\n".join(results["documents"][0]) if results["documents"] else ""

    prompt = f"""Context from documents:
{context}

User question: {user_query}

Answer:"""

    # Forward to Ollama - no output filtering
    ollama_host = os.getenv("OLLAMA_HOST", "localhost")
    ollama_port = os.getenv("OLLAMA_PORT", "11434")
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"http://{ollama_host}:{ollama_port}/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
        )
    return resp.json()


@app.get("/documents")
async def list_documents():
    """VULN: Exposes all document IDs and metadata"""
    results = collection.get()
    return {"documents": results}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "rag-app"}
