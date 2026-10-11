# NammaWeb AI

NammaWeb AI is a Python application built with Streamlit that combines document-based question answering using Retrieval-Augmented Generation (RAG) with campaign-management and scheduling components.

## Features

- **Document Q&A:** Load PDF documents, retrieve relevant passages, and generate answers grounded in document context.
- **Local language-model inference:** Supports local models through Ollama.
- **Semantic retrieval:** Uses embedding models to identify relevant document passages.
- **Campaign management:** Includes campaign execution, scheduling, and compliance-related components.
- **Mock messaging:** Includes fake email and WhatsApp providers for development and testing.
- **Automated tests:** Includes tests for RAG components, database functionality, authentication, campaign execution, provider configuration, and workspace storage.

## Technology Stack

- Python 3.11
- Streamlit
- LangChain
- Ollama
- Sentence Transformers
- SQLAlchemy and Alembic
- SQLite
- Pytest

## Prerequisites

Install the following before running the application:

- Python 3.11
- Git
- Ollama, with a compatible local model downloaded
- Windows PowerShell for the supplied Windows launch scripts

The default configuration uses `llama3.2:3b` for the local model. Ensure that the model is available in Ollama before running the application.

## Setup

### 1. Clone the repository

```powershell
git clone <YOUR_PUBLIC_REPOSITORY_URL>
cd <YOUR_REPOSITORY_FOLDER>
```

Replace the placeholders with your public repository URL and folder name.

### 2. Create a virtual environment

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Review `.env` and adjust settings as needed. Do not commit `.env`, credentials, API tokens, or other private configuration.

### 5. Prepare the local model

Install and start Ollama, then download the default model:

```powershell
ollama pull llama3.2:3b
ollama list
```

Keep Ollama running when using features that depend on local inference.

### 6. Start the application

From the project root, run:

```powershell
.\start_nammaweb.bat
```

Alternatively, start Streamlit directly:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m streamlit run .\app.py --server.address 127.0.0.1 --server.port 8502
```

Open `http://localhost:8502` in your browser.

## Testing

Activate the virtual environment and run:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m pytest -q
```

Compile-check the main Streamlit application with:

```powershell
python -m py_compile .\app.py
```

## RAG Evaluation

The repository includes evaluation scripts and a baseline report under `docs/`.

Review `docs/rag_evaluation_baseline.md` for the recorded evaluation setup and results. Actual results can vary with the selected model, document collection, retrieval settings, and prompt configuration.

## Campaign Scheduler — Test Mode

The supplied PowerShell scheduler launcher uses fake providers and explicitly disables real email and WhatsApp sending.

Run it with:

```powershell
.\run_campaign_scheduler.ps1
```

This launcher is intended for local development and testing. Do not assume that real messages are delivered.

## Local Data and Configuration

Local databases, document files, generated indexes, virtual environments, and private configuration should remain outside version control. Check `.gitignore` before adding new data or generated artifacts.

Use `.env.example` as a template; never place real credentials in that file.

## Limitations

- Local LLM features require Ollama and a compatible downloaded model.
- Model output quality and response time depend on the model, hardware, and input documents.
- The campaign scheduler launcher is configured for fake providers; it does not send real email or WhatsApp messages.

## Development Status

This repository is under active development. Verify the setup, configuration, and evaluation results in your own environment before relying on the application for production use.
