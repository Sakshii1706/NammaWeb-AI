from __future__ import annotations

import streamlit as st

from reach.auth.auth_service import AuthService
from reach.db import get_session
from reach.db.identity_models import Workspace


AUTHENTICATED_USER_KEY = "authenticated_user"


def get_authenticated_user():
    return st.session_state.get(AUTHENTICATED_USER_KEY)


def set_authenticated_user(authenticated_user) -> None:
    st.session_state[AUTHENTICATED_USER_KEY] = authenticated_user


def logout() -> None:
    st.session_state.pop(AUTHENTICATED_USER_KEY, None)
    st.session_state.pop("messages", None)
    st.session_state.pop("active_document", None)
    st.session_state.pop("rag_version", None)
    st.session_state.pop("failed_upload_checksum", None)
    st.session_state.pop("upload_faiss_backup", None)
    st.session_state.pop("previous_document_path", None)
    st.session_state.pop("previous_pdf_backup_path", None)
    st.rerun()


def _render_login() -> bool:
    st.subheader("Sign in")

    email = st.text_input(
        "Email",
        key="login_email",
        placeholder="you@example.com",
    )

    password = st.text_input(
        "Password",
        type="password",
        key="login_password",
    )

    if st.button(
        "Sign in",
        type="primary",
        use_container_width=True,
        key="login_button",
    ):
        email = email.strip()

        if not email:
            st.error("Please enter your email.")
            return False

        if not password:
            st.error("Please enter your password.")
            return False

        try:
            with get_session() as session:
                auth_service = AuthService(session)

                authenticated_user = auth_service.authenticate(
                    email=email,
                    password=password,
                )

        except ValueError as exc:
            st.error(str(exc))
            return False

        except Exception:
            st.error(
                "Unable to sign in right now. Please try again."
            )
            return False

        if authenticated_user is None:
            st.error("Invalid email or password.")
            return False

        set_authenticated_user(authenticated_user)

        st.success("Signed in successfully.")

        st.rerun()

    return False


def _render_register(default_workspace_id: int) -> bool:
    st.subheader("Create account")

    full_name = st.text_input(
        "Full name",
        key="register_full_name",
        placeholder="Your name",
    )

    email = st.text_input(
        "Email",
        key="register_email",
        placeholder="you@example.com",
    )

    password = st.text_input(
        "Password",
        type="password",
        key="register_password",
        help="Use at least 8 characters.",
    )

    confirm_password = st.text_input(
        "Confirm password",
        type="password",
        key="register_confirm_password",
    )

    if st.button(
        "Create account",
        type="primary",
        use_container_width=True,
        key="register_button",
    ):
        full_name = full_name.strip()
        email = email.strip()

        if not full_name:
            st.error("Please enter your full name.")
            return False

        if not email:
            st.error("Please enter your email.")
            return False

        if not password:
            st.error("Please enter a password.")
            return False

        if len(password) < 8:
            st.error("Password must be at least 8 characters.")
            return False

        if password != confirm_password:
            st.error("Passwords do not match.")
            return False

        try:
            with get_session() as session:
                workspace = (
                    session.query(Workspace)
                    .filter(Workspace.id == default_workspace_id)
                    .first()
                )

                if workspace is None:
                    st.error("Default workspace was not found.")
                    return False

                auth_service = AuthService(session)

                auth_service.register_user(
                    email=email,
                    password=password,
                    full_name=full_name,
                    workspace=workspace,
                    role="owner",
                )

                session.commit()

                authenticated_user = auth_service.authenticate(
                    email=email,
                    password=password,
                )

        except ValueError as exc:
            st.error(str(exc))
            return False

        except Exception:
            st.error(
                "Unable to create the account. "
                "The email may already be registered."
            )
            return False

        if authenticated_user is None:
            st.error(
                "Account was created, but automatic sign-in failed. "
                "Please use the Sign in tab."
            )
            return False

        set_authenticated_user(authenticated_user)

        st.success("Account created successfully.")

        st.rerun()

    return False


def render_auth_gate(default_workspace_id: int) -> bool:
    authenticated_user = get_authenticated_user()

    if authenticated_user is not None:
        return True

    st.markdown("# NammaWeb AI")
    st.caption("Retrieval Intelligence Workspace")

    login_tab, register_tab = st.tabs(
        [
            "Sign in",
            "Create account",
        ]
    )

    with login_tab:
        _render_login()

    with register_tab:
        _render_register(default_workspace_id)

    return False
