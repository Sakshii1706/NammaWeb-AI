from pathlib import Path

# ------------------------------------------------------------
# 1. Remove temporary RAG diagnostics from rag_service.py
# ------------------------------------------------------------

path = Path("src/reach/ai/rag/rag_service.py")
text = path.read_text(encoding="utf-8")

diagnostic_block = """        print(
            f"[PERFORMANCE] Context characters: "
            f"{len(context_result.context):,}"
        )
        print(
            f"[PERFORMANCE] Prompt characters: "
            f"{len(prompt):,}"
        )
        print(
            f"[PERFORMANCE] Query characters: "
            f"{len(query):,}"
        )

"""

if diagnostic_block in text:
    text = text.replace(diagnostic_block, "", 1)
    print("RAG diagnostics removed.")
else:
    print("RAG diagnostics already absent.")

path.write_text(text, encoding="utf-8")


# ------------------------------------------------------------
# 2. Remove temporary LLM token diagnostics
# ------------------------------------------------------------

path = Path("src/reach/ai/rag/llm_generator.py")
text = path.read_text(encoding="utf-8")

diagnostic_block = """        usage = getattr(response, "usage_metadata", None)

        if usage:
            print(
                f"[PERFORMANCE] LLM usage: "
                f"input_tokens={usage.get('input_tokens')}, "
                f"output_tokens={usage.get('output_tokens')}, "
                f"total_tokens={usage.get('total_tokens')}"
            )

        response_metadata = getattr(response, "response_metadata", None)

        if response_metadata:
            print(
                f"[PERFORMANCE] LLM metadata: "
                f"prompt_eval_count={response_metadata.get('prompt_eval_count')}, "
                f"eval_count={response_metadata.get('eval_count')}, "
                f"eval_duration={response_metadata.get('eval_duration')}"
            )

"""

if diagnostic_block in text:
    text = text.replace(diagnostic_block, "", 1)
    print("LLM diagnostics removed.")
else:
    print("LLM diagnostics already absent.")

path.write_text(text, encoding="utf-8")


# ------------------------------------------------------------
# 3. Remove temporary patch scripts
# ------------------------------------------------------------

temporary_scripts = [
    Path("scripts/add_rag_diagnostics.py"),
    Path("scripts/add_llm_diagnostics.py"),
]

for script in temporary_scripts:
    if script.exists():
        script.unlink()
        print(f"Removed {script}")
    else:
        print(f"Already absent: {script}")

print("CLEANUP: PASS")
