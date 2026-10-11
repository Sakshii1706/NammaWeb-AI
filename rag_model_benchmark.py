from reach.config import settings
from reach.ai.rag.embedding_service import EmbeddingService
from reach.ai.rag.faiss_store import FAISSVectorStore
from reach.ai.rag.retriever import Retriever
from reach.ai.rag.context_builder import ContextBuilder
from reach.ai.rag.llm_generator import LLMGenerator
from reach.ai.rag.rag_service import RAGService

embedding_service = EmbeddingService(
    model_name=settings.embedding_model
)

vector_store = FAISSVectorStore(
    index_path=settings.faiss_path,
    embedding_service=embedding_service
)

vector_store.load()

retriever = Retriever(
    vector_store=vector_store,
    default_top_k=4
)

context_builder = ContextBuilder(
    max_sources=4,
    max_characters_per_source=settings.max_context_characters_per_source
)

llm_generator = LLMGenerator(
    model=settings.ollama_model,
    temperature=settings.llm_temperature,
    num_predict=settings.llm_num_predict,
    keep_alive=settings.llm_keep_alive
)

rag = RAGService(
    retriever=retriever,
    context_builder=context_builder,
    llm_generator=llm_generator
)

queries = [
    "What is social science?",
    "What are the main branches of social science?",
    "Why is social science important?"
]

print()
print("========================================")
print("RAG MODEL BENCHMARK")
print("Model:", settings.ollama_model)
print("Num predict:", settings.llm_num_predict)
print("========================================")

for i, query in enumerate(queries, 1):
    print()
    print("----------------------------------------")
    print(f"QUERY {i}: {query}")
    print("----------------------------------------")

    response = rag.ask(query, top_k=4)

    print("Generation:", f"{response.generation_time:.3f}s")
    print("Total:", f"{response.total_time:.3f}s")
    print("Answer:", response.answer)

print()
print("========================================")
print("BENCHMARK COMPLETE")
print("========================================")
