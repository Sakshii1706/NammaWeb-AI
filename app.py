import streamlit as st
from pathlib import Path
import hashlib
import shutil
import sys
import time

from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from reach.config import settings
from reach.storage.workspace_storage import WorkspaceStorage

from reach.auth import (
    get_authenticated_user,
    logout,
    render_auth_gate,
)

from reach.db import (
    get_session,
    init_db,
)

from reach.services import DocumentService
from reach.db.identity_models import Workspace
from reach.ai.rag.context_builder import ContextBuilder
from reach.ai.rag.embedding_service import EmbeddingService
from reach.ai.rag.faiss_store import FAISSVectorStore
from reach.ai.rag.llm_generator import LLMGenerator
from reach.ai.rag.pdf_loader import PDFDocumentLoader
from reach.ai.rag.rag_service import RAGService
from reach.ai.rag.retriever import Retriever


# ============================================================
# CONFIGURATION
# ============================================================

DOCUMENTS_PATH = settings.documents_path
FAISS_PATH = settings.faiss_path

EMBEDDING_MODEL = settings.embedding_model
OLLAMA_MODEL = settings.ollama_model

CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap

TOP_K = settings.rag_top_k

DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
FAISS_PATH.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

init_db()


def get_default_workspace_id() -> int:
    # Temporary default workspace until authentication is added.
    with get_session() as session:
        workspace = (
            session.query(Workspace)
            .filter(Workspace.slug == "nammaweb-default")
            .first()
        )

        if workspace is None:
            workspace = Workspace(
                name="NammaWeb Workspace",
                slug="nammaweb-default",
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)

        return workspace.id


DEFAULT_WORKSPACE_ID = get_default_workspace_id()


# ============================================================
# AUTHENTICATION
# ============================================================

if not render_auth_gate(DEFAULT_WORKSPACE_ID):
    st.stop()

authenticated_user = get_authenticated_user()
WORKSPACE_ID = authenticated_user.workspace_id


# ============================================================
# WORKSPACE-SCOPED STORAGE
# ============================================================

workspace_storage = WorkspaceStorage(
    project_root=PROJECT_ROOT,
    workspace_id=WORKSPACE_ID,
)

workspace_storage.ensure()

DOCUMENTS_PATH = workspace_storage.documents_path
FAISS_PATH = workspace_storage.faiss_path




# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="NammaWeb AI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HTML-SAFE MARKDOWN HELPER
# ============================================================

_original_markdown = st.markdown


def _html_safe_markdown(body, *args, **kwargs):

    if (
        kwargs.get("unsafe_allow_html")
        and isinstance(body, str)
    ):

        body = "\n".join(
            line.lstrip()
            for line in body.split("\n")
        )

    return _original_markdown(
        body,
        *args,
        **kwargs
    )


st.markdown = _html_safe_markdown


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background:
        radial-gradient(
            circle at 15% 10%,
            rgba(99, 102, 241, 0.10),
            transparent 30%
        ),
        radial-gradient(
            circle at 85% 90%,
            rgba(139, 92, 246, 0.08),
            transparent 30%
        ),
        #08090d;

    color: #f5f5f7;
}

.main .block-container {
    max-width: 1500px;
    padding-top: 2.2rem;
    padding-bottom: 5rem;
}

#MainMenu,
footer {
    visibility: hidden;
}

header {
    background: transparent !important;
}


/* ========================================================
   SIDEBAR
======================================================== */

section[data-testid="stSidebar"] {
    background: #0b0c11;
    border-right: 1px solid rgba(255,255,255,0.07);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.8rem;
}

.brand {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.7px;
    color: #f5f5f7;
}

.brand-icon {
    color: #a5b4fc;
}

.brand-sub {
    color: #707583;
    font-size: 11px;
    margin-top: 5px;
    margin-bottom: 25px;
}

.side-title {
    color: #666b79;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.7px;
    margin-top: 25px;
    margin-bottom: 10px;
}

.side-document,
.system-card {
    background: #11131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 13px;
    padding: 14px;
    margin-bottom: 8px;
}

.side-document-name {
    font-size: 13px;
    font-weight: 700;
    color: #e7e8ed;
}

.side-document-info {
    color: #707583;
    font-size: 11px;
    margin-top: 6px;
}

.system-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.system-title {
    color: #e4e5ea;
    font-size: 12px;
    font-weight: 700;
}

.system-badge {
    color: #6ee7b7;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 0.7px;
}

.system-description {
    color: #707583;
    font-size: 10px;
    line-height: 1.5;
    margin-top: 5px;
}

.system-online {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #8b909d;
    font-size: 11px;
    margin-top: 14px;
}

.online-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #34d399;
    box-shadow: 0 0 10px rgba(52,211,153,0.7);
}


/* ========================================================
   HERO
======================================================== */

.eyebrow {
    color: #8187a0;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 2.2px;
    font-weight: 800;
}

.hero-title {
    font-size: 43px;
    line-height: 1.08;
    font-weight: 800;
    letter-spacing: -2px;
    margin-top: 8px;
    margin-bottom: 9px;
    color: #f5f5f7;
}

.hero-subtitle {
    color: #858a98;
    font-size: 14px;
    line-height: 1.6;
}


/* ========================================================
   DASHBOARD
======================================================== */

.dashboard-card {
    background: rgba(17,19,26,0.92);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 16px;
}

.card-label {
    color: #7d8291;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.7px;
    margin-bottom: 14px;
}

.document-name {
    color: #f0f1f4;
    font-size: 15px;
    font-weight: 700;
}

.document-description {
    color: #777c89;
    font-size: 11px;
    margin-top: 5px;
}

.metric-row {
    display: flex;
    gap: 9px;
    margin-top: 17px;
}

.metric {
    flex: 1;
    background: #0d0f14;
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 11px;
    text-align: center;
}

.metric-number {
    color: #a5b4fc;
    font-size: 20px;
    font-weight: 800;
}

.metric-label {
    color: #666b79;
    font-size: 9px;
    font-weight: 700;
    margin-top: 3px;
    letter-spacing: 0.8px;
}


/* ========================================================
   CHAT
======================================================== */

.welcome-card {
    background:
        linear-gradient(
            145deg,
            rgba(99,102,241,0.09),
            rgba(255,255,255,0.025)
        );

    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 17px;
    padding: 21px;
    margin-top: 28px;
    margin-bottom: 20px;
}

.ai-label {
    color: #a5b4fc;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin-bottom: 11px;
}

.answer {
    color: #e4e5ea;
    font-size: 14px;
    line-height: 1.75;
}

.user-message {
    background: #171922;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 15px;
    padding: 15px 18px;
    margin: 18px 0 12px 12%;
    color: #e7e8ed;
    font-size: 14px;
    line-height: 1.6;
}

.ai-message {
    background:
        linear-gradient(
            145deg,
            rgba(99,102,241,0.08),
            rgba(255,255,255,0.025)
        );

    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 17px;
    padding: 20px;
    margin: 10px 0 20px 0;
}


/* ========================================================
   SUGGESTIONS
======================================================== */

.section-label {
    color: #73798a;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.8px;
    margin-top: 20px;
    margin-bottom: 10px;
}

.suggestion-card {
    background: #11131a;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 13px;
    padding: 15px;
    min-height: 90px;
}

.suggestion-title {
    color: #e1e2e8;
    font-size: 12px;
    font-weight: 700;
}

.suggestion-description {
    color: #6f7482;
    font-size: 10px;
    line-height: 1.5;
    margin-top: 6px;
}


/* ========================================================
   RAG PIPELINE
======================================================== */

.flow-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 5px 0;
}

.flow-number {
    width: 30px;
    height: 30px;
    min-width: 30px;
    border-radius: 9px;
    background: #1c1f29;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #a5b4fc;
    font-size: 9px;
    font-weight: 800;
}

.flow-number-last {
    background: rgba(99,102,241,0.15);
}

.flow-title {
    color: #e1e2e8;
    font-size: 11px;
    font-weight: 600;
}

.flow-description {
    color: #686d7b;
    font-size: 9px;
    margin-top: 2px;
}

.flow-arrow {
    color: #414552;
    font-size: 13px;
    margin: 2px 0 2px 10px;
}


/* ========================================================
   STATUS
======================================================== */

.status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

.status-row:last-child {
    border-bottom: none;
}

.status-name {
    color: #9da1ad;
    font-size: 11px;
}

.status-ready {
    color: #6ee7b7;
    font-size: 9px;
    font-weight: 800;
}


/* ========================================================
   BUTTONS
======================================================== */

.stButton > button {
    background: #11131a;
    border: 1px solid rgba(255,255,255,0.07);
    color: #cfd2dc;
    border-radius: 10px;
    font-size: 11px;
    min-height: 38px;
}

.stButton > button:hover {
    background: #171923;
    border-color: rgba(129,140,248,0.4);
    color: white;
}


/* ========================================================
   FILE UPLOADER
======================================================== */

[data-testid="stFileUploader"] {
    background: #11131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 13px;
    padding: 8px;
}

[data-testid="stFileUploader"] section {
    background: transparent;
}

[data-testid="stFileUploaderDropzone"] {
    background: #0d0f14;
    border: 1px dashed rgba(165,180,252,0.25);
    border-radius: 10px;
}


/* ========================================================
   CHAT INPUT
======================================================== */

div[data-testid="stChatInput"] {
    margin-top: 20px;
}

div[data-testid="stChatInput"] textarea {
    background: #11131a !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    color: #f5f5f7 !important;
    border-radius: 15px !important;
}

div[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(129,140,248,0.6) !important;
    box-shadow: 0 0 0 1px rgba(129,140,248,0.15) !important;
}


/* ========================================================
   SCROLLBAR
======================================================== */

::-webkit-scrollbar {
    width: 6px;
}

::-webkit-scrollbar-track {
    background: #08090d;
}

::-webkit-scrollbar-thumb {
    background: #292c36;
    border-radius: 10px;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


if "active_document" not in st.session_state:

    existing_pdfs = list(
        DOCUMENTS_PATH.glob("*.pdf")
    )

    if existing_pdfs:

        st.session_state.active_document = (
            existing_pdfs[0]
        )

    else:

        st.session_state.active_document = None


if "rag_version" not in st.session_state:

    st.session_state.rag_version = 0


# ============================================================
# RAG SERVICE / DOCUMENT INDEX
# ============================================================
# Streamlit delegates retrieval, context construction and generation
# to the reusable services under src/reach/ai/rag/.
# Existing FAISS indexes still load without loading MiniLM.
# Embeddings and Llama remain lazy-loaded.
# ============================================================

@st.cache_resource(show_spinner=False)
def load_document_rag(pdf_path, rag_version):

    total_start = time.perf_counter()

    pdf_start = time.perf_counter()
    loader = PDFDocumentLoader(pdf_path)
    pages = loader.load()
    pdf_time = time.perf_counter() - pdf_start

    print(f"[PERFORMANCE] PDF processing: {pdf_time:.3f}s")

    embedding_service = EmbeddingService(model_name=EMBEDDING_MODEL)

    # Warm up the embedding model during application startup so the
    # first user query does not pay the model initialization cost.
    embedding_warmup_start = time.perf_counter()
    embedding_service.embed_query("warm up")
    embedding_warmup_time = time.perf_counter() - embedding_warmup_start
    print(
        f"[PERFORMANCE] Embedding warm-up: "
        f"{embedding_warmup_time:.3f}s"
    )

    vector_store = FAISSVectorStore(
        index_path=FAISS_PATH,
        embedding_service=embedding_service,
    )

    if vector_store.exists:

        print("[PERFORMANCE] Existing FAISS index detected.")
        chunk_count = vector_store.load()
        print("[PERFORMANCE] Skipping document chunking and embedding.")

    else:

        print("[PERFORMANCE] No existing FAISS index detected.")
        print("[PERFORMANCE] Creating document chunks...")

        chunk_start = time.perf_counter()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        chunks = splitter.split_documents(pages)

        for chunk in chunks:
            chunk.metadata["page_number"] = (
                chunk.metadata.get("page", 0) + 1
            )

        chunk_time = time.perf_counter() - chunk_start
        print(f"[PERFORMANCE] Chunking: {chunk_time:.3f}s")
        print("[PERFORMANCE] Loading embedding model for new document...")

        embedding_start = time.perf_counter()
        chunk_count = vector_store.build(chunks)
        embedding_time = time.perf_counter() - embedding_start
        print(f"[PERFORMANCE] Document embedding: {embedding_time:.3f}s")

    retriever = Retriever(
        vector_store=vector_store,
        default_top_k=TOP_K,
    )

    context_builder = ContextBuilder(
        max_sources=TOP_K,
        max_characters_per_source=settings.max_context_characters_per_source,
    )

    llm_generator = LLMGenerator(
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
        num_predict=settings.llm_num_predict,
        keep_alive=settings.llm_keep_alive,
    )

    rag_service = RAGService(
        retriever=retriever,
        context_builder=context_builder,
        llm_generator=llm_generator,
    )

    total_time = time.perf_counter() - total_start
    print(f"[PERFORMANCE] Total document loading: {total_time:.3f}s")

    return vector_store, pages, chunk_count, rag_service


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # ========================================================
    # ACCOUNT
    # ========================================================

    st.markdown(
        '<div class="side-title">ACCOUNT</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="side-document">
            <div class="side-document-name">
                {authenticated_user.full_name}
            </div>

            <div class="side-document-info">
                {authenticated_user.email}
            </div>

            <div class="side-document-info">
                Workspace: {authenticated_user.workspace_name}
            </div>

            <div class="side-document-info">
                Role: {authenticated_user.role}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Sign out",
        use_container_width=True,
        key="logout_button",
    ):
        logout()


    st.markdown(
        """
        <div class="brand">
            <span class="brand-icon">◈</span>
            NAMMAWEB AI
        </div>

        <div class="brand-sub">
            Retrieval Intelligence Workspace
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # DOCUMENT MANAGER
    # ========================================================

    st.markdown(
        '<div class="side-title">DOCUMENT MANAGER</div>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Add or replace PDF",
        type=["pdf"],
        help="Upload a PDF to use as the active knowledge base.",
    )

    if uploaded_file is not None:

        # ------------------------------------------------
        # CALCULATE CHECKSUM WITHOUT DEPENDING ON FILENAME
        # ------------------------------------------------

        upload_bytes = uploaded_file.getbuffer()

        uploaded_checksum = hashlib.sha256(
            upload_bytes
        ).hexdigest()

        current_document_path = (
            st.session_state.active_document
        )

        current_document_checksum = None

        if (
            current_document_path is not None
            and current_document_path.exists()
        ):

            current_document_checksum = (
                DocumentService.calculate_checksum(current_document_path)
            )

        # Streamlit reruns after processing. Do not
        # process the exact same uploaded content again.

        upload_is_current = (
            current_document_checksum is not None
            and current_document_checksum
            == uploaded_checksum
        )

        failed_upload_checksum = (
            st.session_state.get(
                "failed_upload_checksum"
            )
        )

        upload_previously_failed = (
            failed_upload_checksum
            == uploaded_checksum
        )

        if (
            not upload_is_current
            and not upload_previously_failed
        ):

            new_document_path = (
                DOCUMENTS_PATH
                / uploaded_file.name
            )

            previous_document_path = (
                current_document_path
                if (
                    current_document_path is not None
                    and current_document_path.exists()
                )
                else None
            )

            # ------------------------------------------------
            # PRESERVE OLD FAISS INDEX
            # ------------------------------------------------

            faiss_backup_path = (
                FAISS_PATH.parent
                / f"{FAISS_PATH.name}_previous"
            )

            if faiss_backup_path.exists():

                shutil.rmtree(
                    faiss_backup_path,
                    ignore_errors=True,
                )

            if FAISS_PATH.exists():

                shutil.move(
                    str(FAISS_PATH),
                    str(faiss_backup_path),
                )

            # ------------------------------------------------
            # PRESERVE OLD PDF IF SAME PATH WILL BE OVERWRITTEN
            # ------------------------------------------------

            previous_pdf_backup_path = None

            if (
                previous_document_path is not None
                and previous_document_path.resolve()
                == new_document_path.resolve()
            ):

                previous_pdf_backup_path = (
                    DOCUMENTS_PATH
                    / (
                        ".previous_"
                        + previous_document_path.name
                    )
                )

                if previous_pdf_backup_path.exists():

                    previous_pdf_backup_path.unlink()

                shutil.copy2(
                    previous_document_path,
                    previous_pdf_backup_path,
                )

            # ------------------------------------------------
            # SAVE NEW DOCUMENT
            # ------------------------------------------------

            with open(
                new_document_path,
                "wb",
            ) as file:

                file.write(upload_bytes)

            # ------------------------------------------------
            # CREATE PROCESSING RECORD
            # ------------------------------------------------

            try:

                with get_session() as session:

                    document_service = DocumentService(session, workspace_id=WORKSPACE_ID)

                    knowledge_base = (
                        document_service.get_or_create_default_knowledge_base()
                    )

                    document_record = (
                        document_service.prepare_processing(
                            knowledge_base_id=knowledge_base.id,
                            filename=uploaded_file.name,
                            file_path=new_document_path,
                            checksum=uploaded_checksum,
                        )
                    )

                    document_service.commit()

            except Exception:

                # Restore overwritten PDF if DB setup fails.

                if (
                    previous_pdf_backup_path is not None
                    and previous_pdf_backup_path.exists()
                ):

                    if new_document_path.exists():

                        new_document_path.unlink()

                    shutil.move(
                        str(previous_pdf_backup_path),
                        str(new_document_path),
                    )

                if (
                    faiss_backup_path.exists()
                    and not FAISS_PATH.exists()
                ):

                    shutil.move(
                        str(faiss_backup_path),
                        str(FAISS_PATH),
                    )

                raise

            # ------------------------------------------------
            # STORE PROCESSING STATE
            # ------------------------------------------------

            st.session_state.active_document = (
                new_document_path
            )

            st.session_state.messages = []

            st.session_state.rag_version += 1

            st.session_state.pop(
                "failed_upload_checksum",
                None,
            )

            st.session_state.upload_faiss_backup = (
                faiss_backup_path
                if faiss_backup_path.exists()
                else None
            )

            st.session_state.previous_document_path = (
                previous_document_path
            )

            st.session_state.previous_pdf_backup_path = (
                previous_pdf_backup_path
            )

            st.success(
                f"Processing "
                f"{uploaded_file.name}..."
            )

            st.rerun()

    # ========================================================
    # LOAD ACTIVE DOCUMENT
    # ========================================================

    if st.session_state.active_document:

        active_pdf = (
            st.session_state.active_document
        )

        with st.spinner(
            "Loading document..."
        ):

            try:

                (
                    vector_store,
                    pages,
                    chunk_count,
                    rag_service,
                ) = load_document_rag(
                    str(active_pdf),
                    st.session_state.rag_version,
                )

                # ------------------------------------------------
                # NEW DOCUMENT PROCESSED SUCCESSFULLY
                # ------------------------------------------------

                with get_session() as session:

                    document_service = DocumentService(session, workspace_id=WORKSPACE_ID)

                    knowledge_base = (
                        document_service.get_or_create_default_knowledge_base()
                    )

                    document_record = (
                        document_service.get_document_by_checksum(
                            knowledge_base_id=knowledge_base.id,
                            checksum=DocumentService.calculate_checksum(active_pdf),
                        )
                    )

                    if document_record is not None:

                        # Only now archive the previous active
                        # document.

                        document_service.mark_processing_success(
                            document=document_record,
                            page_count=len(pages),
                            chunk_count=chunk_count,
                        )

                        document_service.commit()

                # ------------------------------------------------
                # NEW FAISS IS NOW TRUSTED
                # ------------------------------------------------

                faiss_backup_path = (
                    st.session_state.get(
                        "upload_faiss_backup"
                    )
                )

                if (
                    faiss_backup_path is not None
                    and faiss_backup_path.exists()
                ):

                    shutil.rmtree(
                        faiss_backup_path,
                        ignore_errors=True,
                    )

                previous_pdf_backup_path = (
                    st.session_state.get(
                        "previous_pdf_backup_path"
                    )
                )

                if (
                    previous_pdf_backup_path is not None
                    and previous_pdf_backup_path.exists()
                ):

                    previous_pdf_backup_path.unlink()

                st.session_state.upload_faiss_backup = (
                    None
                )

                st.session_state.previous_document_path = (
                    None
                )

                st.session_state.previous_pdf_backup_path = (
                    None
                )

                st.session_state.pop(
                    "failed_upload_checksum",
                    None,
                )

            except Exception:

                # ------------------------------------------------
                # MARK NEW DOCUMENT FAILED
                # ------------------------------------------------

                failed_checksum = None

                if active_pdf.exists():

                    failed_checksum = (
                        DocumentService.calculate_checksum(active_pdf)
                    )

                    with get_session() as session:

                        document_service = DocumentService(session, workspace_id=WORKSPACE_ID)

                        knowledge_base = (
                            document_service.get_or_create_default_knowledge_base()
                        )

                        document_record = (
                            document_service.get_document_by_checksum(
                                knowledge_base_id=knowledge_base.id,
                                checksum=failed_checksum,
                            )
                        )

                        if document_record is not None:

                            document_service.mark_processing_failed(
                                document=document_record,
                            )

                            document_service.commit()

                # ------------------------------------------------
                # RESTORE OLD FAISS
                # ------------------------------------------------

                faiss_backup_path = (
                    st.session_state.get(
                        "upload_faiss_backup"
                    )
                )

                if (
                    faiss_backup_path is not None
                    and faiss_backup_path.exists()
                ):

                    if FAISS_PATH.exists():

                        shutil.rmtree(
                            FAISS_PATH,
                            ignore_errors=True,
                        )

                    shutil.move(
                        str(faiss_backup_path),
                        str(FAISS_PATH),
                    )

                # ------------------------------------------------
                # RESTORE OVERWRITTEN PDF
                # ------------------------------------------------

                previous_pdf_backup_path = (
                    st.session_state.get(
                        "previous_pdf_backup_path"
                    )
                )

                if (
                    previous_pdf_backup_path is not None
                    and previous_pdf_backup_path.exists()
                ):

                    if active_pdf.exists():

                        active_pdf.unlink()

                    shutil.move(
                        str(previous_pdf_backup_path),
                        str(active_pdf),
                    )

                # ------------------------------------------------
                # RESTORE PREVIOUS ACTIVE DOCUMENT
                # ------------------------------------------------

                previous_document_path = (
                    st.session_state.get(
                        "previous_document_path"
                    )
                )

                if previous_document_path is not None:

                    st.session_state.active_document = (
                        previous_document_path
                    )

                st.session_state.upload_faiss_backup = (
                    None
                )

                st.session_state.previous_document_path = (
                    None
                )

                st.session_state.previous_pdf_backup_path = (
                    None
                )

                if failed_checksum is not None:

                    st.session_state.failed_upload_checksum = (
                        failed_checksum
                    )

                st.session_state.rag_version += 1

                st.error(
                    "The new document could not be processed. "
                    "The previous active document has been restored."
                )

    else:

        vector_store = None

        pages = []

        chunk_count = 0

        rag_service = None

        st.info(
            "Upload a PDF above to create "
            "your knowledge base."
        )

    # ========================================================
    # NEW CONVERSATION
    # ========================================================

    if st.button(
        "+ New conversation",
        use_container_width=True,
    ):

        st.session_state.messages = []

        st.rerun()

    # ========================================================
    # WORKSPACE
    # ========================================================

    st.markdown(
        '<div class="side-title">WORKSPACE</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.active_document:

        st.markdown(
            f"""
            <div class="side-document">

                <div class="side-document-name">
                    📄 &nbsp;
                    {st.session_state.active_document.name}
                </div>

                <div class="side-document-info">
                    {len(pages)} pages ·
                    {chunk_count} semantic chunks
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
            <div class="side-document">

                <div class="side-document-name">
                    No document selected
                </div>

                <div class="side-document-info">
                    Upload a PDF to begin
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # AI SYSTEM
    # ========================================================

    st.markdown(
        '<div class="side-title">AI SYSTEM</div>',
        unsafe_allow_html=True,
    )

    system_status = (
        "READY"
        if vector_store is not None
        else "WAITING"
    )

    st.markdown(
        f"""
        <div class="system-card">

            <div class="system-header">

                <div class="system-title">
                    Retrieval Engine
                </div>

                <div class="system-badge">
                    {system_status}
                </div>

            </div>

            <div class="system-description">
                Local document retrieval powered by
                embeddings, FAISS and Llama.
            </div>

            <div class="system-online">

                <span class="online-dot"></span>

                {
                    "All systems operational"
                    if vector_store is not None
                    else "Waiting for document"
                }

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN LAYOUT
# ============================================================

main_col, right_col = st.columns(
    [3.2, 1.15],
    gap="large",
)


# ============================================================
# MAIN CONTENT
# ============================================================

with main_col:

    st.markdown(
        '<div class="eyebrow">DOCUMENT INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="hero-title">Ask your knowledge base.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.active_document:

        st.markdown(
            f"""
            <div class="hero-subtitle">

                Ask questions about

                <strong>
                    {st.session_state.active_document.name}
                </strong>

                and get grounded answers powered by
                local retrieval and Llama.

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
            <div class="hero-subtitle">

                Upload a PDF from the sidebar to create
                your document knowledge base.

            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # CHAT HISTORY
    # ========================================================

    if not st.session_state.messages:

        if vector_store is not None:

            st.markdown(
                """
                <div class="welcome-card">

                    <div class="ai-label">
                        NAMMAWEB AI
                    </div>

                    <div class="answer">

                        Your document is loaded and ready.
                        Ask a question and I'll retrieve the
                        most relevant information from the
                        knowledge base.

                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    else:

        for message in (
            st.session_state.messages
        ):

            if message["role"] == "user":

                st.markdown(
                    f"""
                    <div class="user-message">
                        {message["content"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    f"""
                    <div class="ai-message">

                        <div class="ai-label">
                            NAMMAWEB AI
                        </div>

                        <div class="answer">
                            {message["content"]}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ========================================================
    # SUGGESTIONS
    # ========================================================

    suggestion_query = None

    if vector_store is not None:

        st.markdown(
            '<div class="section-label">TRY ASKING</div>',
            unsafe_allow_html=True,
        )

        suggestion_col1, suggestion_col2 = (
            st.columns(2)
        )

        with suggestion_col1:

            st.markdown(
                """
                <div class="suggestion-card">

                    <div class="suggestion-title">
                        Explore the document
                    </div>

                    <div class="suggestion-description">
                        Get an overview of the topics and
                        information covered in the document.
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "📚 Explore document",
                key="explore_document_button",
                use_container_width=True,
            ):
                suggestion_query = (
                    "What are the main topics covered in this document?"
                )

        with suggestion_col2:

            st.markdown(
                """
                <div class="suggestion-card">

                    <div class="suggestion-title">
                        Find specific information
                    </div>

                    <div class="suggestion-description">
                        Ask about a particular concept,
                        program, experiment or implementation.
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "🔎 Find key information",
                key="find_information_button",
                use_container_width=True,
            ):
                suggestion_query = (
                    "What are the key concepts discussed in this document?"
                )
    # ========================================================
    # CHAT INPUT
    # ========================================================

    query = st.chat_input(
        "Ask something about your document..."
    )

    if query is None and suggestion_query is not None:
        query = suggestion_query

    # ========================================================
    # QUERY PROCESSING
    # ========================================================

    if query:

        if vector_store is None:

            st.error(
                "Please upload a PDF before asking a question."
            )

        else:

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": query,
                }
            )

            # ------------------------------------------------
            # RAG SERVICE
            # ------------------------------------------------
            # Retrieval, context construction and LLM generation
            # are handled by the reusable RAGService.

            with st.spinner(
                "Searching the knowledge base..."
            ):

                result = rag_service.ask(
                    query=query,
                    top_k=TOP_K,
                )

            answer = result.answer

            print("\n========== PERFORMANCE ==========")
            print(f"RAG retrieval: {result.retrieval_time:.3f}s")
            print(f"Llama generation: {result.generation_time:.3f}s")
            print(f"Total response time: {result.total_time:.3f}s")
            print(f"Pages: {result.pages}")
            print(f"Sources: {result.source_count}")
            print("================================\n")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            st.rerun()


# ============================================================
# RIGHT DASHBOARD
# ============================================================

with right_col:

    # ========================================================
    # KNOWLEDGE BASE
    # ========================================================

    st.markdown(
        f"""
        <div class="dashboard-card">

            <div class="card-label">
                KNOWLEDGE BASE
            </div>

            <div class="document-name">

                📄 &nbsp;

                {
                    st.session_state.active_document.name
                    if st.session_state.active_document
                    else "No document"
                }

            </div>

            <div class="document-description">
                Active PDF knowledge base
            </div>

            <div class="metric-row">

                <div class="metric">

                    <div class="metric-number">
                        {len(pages)}
                    </div>

                    <div class="metric-label">
                        PAGES
                    </div>

                </div>

                <div class="metric">

                    <div class="metric-number">
                        {chunk_count}
                    </div>

                    <div class="metric-label">
                        CHUNKS
                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # PIPELINE
    # ========================================================

    st.markdown(
        """
        <div class="dashboard-card">

            <div class="card-label">
                RAG PIPELINE
            </div>

            <div class="flow-item">

                <div class="flow-number">
                    01
                </div>

                <div>

                    <div class="flow-title">
                        Document Loader
                    </div>

                    <div class="flow-description">
                        PDF extraction
                    </div>

                </div>

            </div>

            <div class="flow-arrow">
                ↓
            </div>

            <div class="flow-item">

                <div class="flow-number">
                    02
                </div>

                <div>

                    <div class="flow-title">
                        Text Chunking
                    </div>

                    <div class="flow-description">
                        Semantic splitting
                    </div>

                </div>

            </div>

            <div class="flow-arrow">
                ↓
            </div>

            <div class="flow-item">

                <div class="flow-number">
                    03
                </div>

                <div>

                    <div class="flow-title">
                        Embeddings
                    </div>

                    <div class="flow-description">
                        Vector representation
                    </div>

                </div>

            </div>

            <div class="flow-arrow">
                ↓
            </div>

            <div class="flow-item">

                <div class="flow-number">
                    04
                </div>

                <div>

                    <div class="flow-title">
                        FAISS
                    </div>

                    <div class="flow-description">
                        Vector retrieval
                    </div>

                </div>

            </div>

            <div class="flow-arrow">
                ↓
            </div>

            <div class="flow-item">

                <div class="flow-number flow-number-last">
                    05
                </div>

                <div>

                    <div class="flow-title">
                        Llama
                    </div>

                    <div class="flow-description">
                        Grounded generation
                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # SYSTEM STATUS
    # ========================================================

    st.markdown(
        f"""
        <div class="dashboard-card">

            <div class="card-label">
                SYSTEM STATUS
            </div>

            <div class="status-row">

                <div class="status-name">
                    Document Loader
                </div>

                <div class="status-ready">
                    {
                        "READY"
                        if vector_store
                        else "WAITING"
                    }
                </div>

            </div>

            <div class="status-row">

                <div class="status-name">
                    Embedding Model
                </div>

                <div class="status-ready">
                    {
                        "READY"
                        if vector_store
                        else "WAITING"
                    }
                </div>

            </div>

            <div class="status-row">

                <div class="status-name">
                    FAISS
                </div>

                <div class="status-ready">
                    {
                        "READY"
                        if vector_store
                        else "WAITING"
                    }
                </div>

            </div>

            <div class="status-row">

                <div class="status-name">
                    Llama 3.2
                </div>

                <div class="status-ready">
                    ONLINE
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# CAMPAIGN UI INTEGRATION
from reach.campaigns.streamlit_ui import render_campaigns_ui
render_campaigns_ui(WORKSPACE_ID)


# FOOTER
# ============================================================

st.markdown(
    """
    <div style="
        text-align:center;
        color:#555a68;
        font-size:10px;
        margin-top:30px;
        letter-spacing:1px;
    ">
        NAMMAWEB AI · LOCAL RETRIEVAL INTELLIGENCE
    </div>
    """,
    unsafe_allow_html=True,
)


