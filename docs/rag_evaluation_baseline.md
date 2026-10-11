# NammaWeb AI - RAG Evaluation Baseline

Date: 2026-09-25

## Retrieval evaluation

Evaluation set: 6 questions  
Top-K: 4

Result:

- Retrieval hits: 6/6
- Retrieval hit rate: 100%

The expected page was retrieved for all six questions.

## Generation evaluation

Evaluation set: 6 questions  
Model: `llama3.2:3b`  
Top-K: 4  
Temperature: 0  
Max output tokens: 128

Initial generation result:

- 5/6 passed
- 83.3%

The only failure was Geography. Retrieval was correct, but the generated answer was too compressed for the evaluator's completeness criteria.

After the RAG prompt was strengthened to request the core definition plus important supporting points:

- 6/6 passed
- 100%

The out-of-document test also passed:

Question:
"What is the capital of Japan?"

Expected behavior:
"The information was not found in the document."

Observed behavior:
"The information was not found in the document."

## Current architecture status

- FAISS retrieval: working
- Lazy embeddings: working
- ContextBuilder: working
- Llama generation: working
- Grounded refusal: working
- Retrieval evaluation: 100%
- Generation evaluation: 100%

## Known observation

Some generated answers can approach the `num_predict=128` limit. The evaluation currently passes, but answer truncation should be monitored before increasing output limits or optimizing latency.

## Baseline policy

Do not change the RAG prompt, retrieval parameters, embedding model, or LLM settings without rerunning:

1. `evaluate_rag.py`
2. `evaluate_generation.py`
3. `test_rag_components.py`
