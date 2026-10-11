import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


from reach.config import settings


def main():
    print("=" * 70)
    print("NAMMAWEB AI - CONFIGURATION VALIDATION")
    print("=" * 70)

    print(f"App name       : {settings.app_name}")
    print(f"Environment    : {settings.app_env}")
    print(f"Host           : {settings.host}")
    print(f"Port           : {settings.port}")

    print(f"Documents      : {settings.documents_path}")
    print(f"FAISS          : {settings.faiss_path}")

    print(f"Embedding      : {settings.embedding_model}")
    print(f"Top-K          : {settings.rag_top_k}")
    print(f"Chunk size     : {settings.chunk_size}")
    print(f"Chunk overlap  : {settings.chunk_overlap}")

    print(f"Ollama model   : {settings.ollama_model}")
    print(f"Temperature    : {settings.llm_temperature}")
    print(f"Max predict    : {settings.llm_num_predict}")
    print(f"Keep alive     : {settings.llm_keep_alive}")

    settings.validate()
    settings.ensure_directories()

    print()
    print("CONFIGURATION VALIDATION: PASS")


if __name__ == "__main__":
    main()
