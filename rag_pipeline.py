import time

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama


# ============================================================
# CONFIGURATION
# ============================================================

PDF_PATH = "documents/sample.pdf"

CHROMA_PATH = "data/chroma_db"

EMBEDDING_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

OLLAMA_MODEL = "llama3.2:3b"

COLLECTION_NAME = "oop_manual"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 100
TOP_K = 4


# ============================================================
# LOAD EMBEDDING MODEL ONCE
# ============================================================

print("Loading embedding model...")

embedding_start = time.perf_counter()

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)

embedding_model_time = (
    time.perf_counter()
    - embedding_start
)

print(
    f"Embedding model loaded in "
    f"{embedding_model_time:.3f}s"
)


# ============================================================
# LOAD OLLAMA ONCE
# ============================================================

print("Loading Ollama model...")

llm_start = time.perf_counter()

llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=0,
    keep_alive="10m",
)

llm_load_time = (
    time.perf_counter()
    - llm_start
)

print(
    f"Ollama model initialized in "
    f"{llm_load_time:.3f}s"
)


# ============================================================
# LOAD PDF
# ============================================================

print("\nLoading PDF...")

pdf_start = time.perf_counter()

loader = PyPDFLoader(
    PDF_PATH
)

pages = loader.load()

pdf_time = (
    time.perf_counter()
    - pdf_start
)

print(
    f"Pages loaded: {len(pages)}"
)

print(
    f"PDF processing: "
    f"{pdf_time:.3f}s"
)


# ============================================================
# CREATE CHUNKS
# ============================================================

print("\nCreating chunks...")

chunk_start = time.perf_counter()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)

chunks = text_splitter.split_documents(
    pages
)

for chunk in chunks:

    chunk.metadata["page_number"] = (
        chunk.metadata.get("page", 0) + 1
    )

chunk_time = (
    time.perf_counter()
    - chunk_start
)

print(
    f"Chunks created: {len(chunks)}"
)

print(
    f"Chunking: "
    f"{chunk_time:.3f}s"
)


# ============================================================
# LOAD CHROMADB
# ============================================================

print("\nLoading ChromaDB...")

chroma_start = time.perf_counter()

vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings,
)

existing_count = (
    vectorstore._collection.count()
)


# ============================================================
# CREATE DOCUMENT EMBEDDINGS ONLY IF REQUIRED
# ============================================================

if existing_count == 0:

    print(
        "No existing vectors found."
    )

    print(
        "Creating document embeddings..."
    )

    document_embedding_start = (
        time.perf_counter()
    )

    vectorstore.add_documents(
        documents=chunks
    )

    document_embedding_time = (
        time.perf_counter()
        - document_embedding_start
    )

    print(
        f"Document embedding: "
        f"{document_embedding_time:.3f}s"
    )

else:

    print(
        f"Existing ChromaDB found "
        f"({existing_count} vectors)."
    )

    print(
        "Reusing existing embeddings."
    )


chroma_time = (
    time.perf_counter()
    - chroma_start
)

print(
    f"ChromaDB initialization: "
    f"{chroma_time:.3f}s"
)


# ============================================================
# QUESTION
# ============================================================

query = (
    "What experiments are included "
    "in the OOP laboratory manual?"
)

print(
    f"\nQuery: {query}"
)


# ============================================================
# QUESTION EMBEDDING
# ============================================================

print(
    "\nCreating question embedding..."
)

question_embedding_start = (
    time.perf_counter()
)

query_embedding = embeddings.embed_query(
    query
)

question_embedding_time = (
    time.perf_counter()
    - question_embedding_start
)

print(
    f"Question embedding: "
    f"{question_embedding_time:.3f}s"
)


# ============================================================
# CHROMADB RETRIEVAL
# ============================================================

print(
    "\nRetrieving relevant chunks..."
)

retrieval_start = time.perf_counter()

results = vectorstore._collection.query(
    query_embeddings=[query_embedding],
    n_results=TOP_K,
    include=[
        "documents",
        "metadatas",
        "distances",
    ],
)

retrieval_time = (
    time.perf_counter()
    - retrieval_start
)

documents = []

result_documents = (
    results.get("documents", [[]])[0]
)

result_metadatas = (
    results.get("metadatas", [[]])[0]
)

for content, metadata in zip(
    result_documents,
    result_metadatas,
):

    metadata = metadata or {}

    page_number = metadata.get(
        "page_number",
        metadata.get("page", 0) + 1,
    )

    documents.append(
        {
            "content": content,
            "page": page_number,
        }
    )


print(
    f"Retrieved {len(documents)} chunks."
)

print(
    f"ChromaDB retrieval: "
    f"{retrieval_time:.3f}s"
)


# ============================================================
# BUILD CONTEXT
# ============================================================

prompt_start = time.perf_counter()

context_parts = []

for i, doc in enumerate(
    documents,
    start=1,
):

    context_parts.append(
        f"""
--- Source {i} ---
Page: {doc["page"]}

{doc["content"]}
"""
    )

context = "\n".join(
    context_parts
)

prompt = f"""
You are a document question-answering assistant.

Answer the user's question using ONLY the
information provided in the context.

If the answer cannot be found in the context,
say that the information is not available
in the document.

Keep the answer clear and concise.

Always mention the relevant page number
when possible.

Context:
{context}

User Question:
{query}

Answer:
"""

prompt_time = (
    time.perf_counter()
    - prompt_start
)

print(
    f"Prompt preparation: "
    f"{prompt_time:.3f}s"
)


# ============================================================
# LLAMA GENERATION
# ============================================================

print(
    "\nGenerating answer using Llama..."
)

llm_start = time.perf_counter()

response = llm.invoke(
    prompt
)

llm_time = (
    time.perf_counter()
    - llm_start
)


# ============================================================
# FINAL RESULT
# ============================================================

print(
    "\n========== RAG ANSWER =========="
)

print(
    response.content
)


# ============================================================
# SOURCES
# ============================================================

print(
    "\n========== SOURCES =========="
)

for i, doc in enumerate(
    documents,
    start=1,
):

    print(
        f"{i}. Page {doc['page']}"
    )


# ============================================================
# PERFORMANCE
# ============================================================

print(
    "\n========== PERFORMANCE =========="
)

print(
    f"PDF processing: "
    f"{pdf_time:.3f}s"
)

print(
    f"Document embedding/indexing: "
    f"{locals().get('document_embedding_time', 0):.3f}s"
)

print(
    f"Question embedding: "
    f"{question_embedding_time:.3f}s"
)

print(
    f"ChromaDB retrieval: "
    f"{retrieval_time:.3f}s"
)

print(
    f"Prompt preparation: "
    f"{prompt_time:.3f}s"
)

print(
    f"Llama generation: "
    f"{llm_time:.3f}s"
)

print(
    "\nRAG + ChromaDB + Ollama "
    "performance test completed."
)