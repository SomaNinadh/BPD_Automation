"""
BPD Generator - Streamlit entry point.

Run with: streamlit run app.py
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.document import BPDDocumentBuilder
from src.document.blocks import BlockType
from src.services import auth_service, draft_service, supabase_service
from src.ui import state
from src.ui.components import render_block_card


st.set_page_config(
    page_title="BPD Generator",
    page_icon="📄",
    layout="wide",
)


def _add_block_callback(block_type_value: str) -> None:
    state.add_block(BlockType(block_type_value))


def _persist_identity(identity: auth_service.AuthIdentity) -> None:
    state.set_auth_state(
        {
            "user_id": identity.user_id,
            "email": identity.email,
            "access_token": identity.access_token,
            "refresh_token": identity.refresh_token,
        }
    )


def _restore_identity() -> auth_service.AuthIdentity | None:
    auth_state = state.get_auth_state()
    access_token = auth_state.get("access_token")
    refresh_token = auth_state.get("refresh_token")
    if not access_token or not refresh_token:
        return None
    try:
        identity = auth_service.restore_session(access_token, refresh_token)
    except Exception:
        state.clear_auth_state()
        return None
    _persist_identity(identity)
    return identity


def _render_setup_help() -> None:
    st.title("Business Process Document Generator")
    st.error("Supabase is not configured yet.")
    st.markdown(
        "Add the required secrets in Streamlit and create the database table before using saved drafts."
    )
    st.code(
        "SUPABASE_URL = \"https://your-project-ref.supabase.co\"\n"
        "SUPABASE_ANON_KEY = \"your-anon-key\"\n"
        "SUPABASE_SERVICE_ROLE_KEY = \"your-service-role-key\"",
        language="toml",
    )
    st.markdown("Run the SQL in `supabase/schema.sql` inside your Supabase SQL editor.")


def _render_auth_screen() -> auth_service.AuthIdentity | None:
    st.title("Business Process Document Generator")
    st.caption("Sign in to create, save, and resume BPD drafts from any laptop.")

    login_tab, signup_tab = st.tabs(["Login", "Sign up"])

    with login_tab:
        with st.form("login-form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            try:
                identity = auth_service.sign_in(email.strip(), password)
            except Exception as exc:
                st.error(f"Sign in failed: {exc}")
            else:
                _persist_identity(identity)
                st.rerun()

    with signup_tab:
        with st.form("signup-form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm password", type="password", key="signup_password_confirm")
            submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    identity, message = auth_service.sign_up(email.strip(), password)
                except Exception as exc:
                    st.error(f"Sign up failed: {exc}")
                else:
                    if identity is not None:
                        _persist_identity(identity)
                        st.success(message)
                        st.rerun()
                    else:
                        st.success(message)

    return None


def _save_draft(identity: auth_service.AuthIdentity, *, force_new: bool) -> None:
    draft_name = st.session_state.get("draft_name_input", state.get_current_draft_name()).strip()
    if not draft_name:
        st.error("Enter a draft name before saving.")
        return

    project_snapshot = state.export_project_state()
    try:
        if force_new or not state.get_current_draft_id():
            saved = draft_service.create_draft(draft_name, project_snapshot, identity.user_id)
        else:
            saved = draft_service.update_draft(
                state.get_current_draft_id(),
                draft_name,
                project_snapshot,
                identity.user_id,
            )
    except Exception as exc:
        st.error(f"Draft save failed: {exc}")
        return

    state.set_current_draft(saved.draft_id, saved.name)
    state.set_last_saved_snapshot(project_snapshot)
    st.success(f"Draft saved: {saved.name}")


def _load_selected_draft(selected_draft_id: str) -> None:
    try:
        record = draft_service.get_draft(selected_draft_id)
    except Exception as exc:
        st.error(f"Draft load failed: {exc}")
        return

    state.import_project_state(record.project_json)
    state.set_current_draft(record.summary.draft_id, record.summary.name)
    state.set_last_saved_snapshot(record.project_json)
    st.success(f"Loaded draft: {record.summary.name}")
    st.rerun()


def _delete_selected_draft(selected_draft_id: str) -> None:
    try:
        draft_service.delete_draft(selected_draft_id)
    except Exception as exc:
        st.error(f"Draft delete failed: {exc}")
        return

    if state.get_current_draft_id() == selected_draft_id:
        state.clear_project_state()
    st.success("Draft deleted.")
    st.rerun()


def _render_drafts_panel(identity: auth_service.AuthIdentity) -> None:
    st.subheader("Drafts")
    st.caption(f"Signed in as `{identity.email}`")
    if st.button("Log out", use_container_width=True):
        try:
            auth_service.sign_out(
                state.get_auth_state().get("access_token", ""),
                state.get_auth_state().get("refresh_token", ""),
            )
        except Exception:
            pass
        state.clear_auth_state()
        state.clear_project_state()
        st.rerun()

    st.text_input(
        "Draft name",
        value=state.get_current_draft_name(),
        key="draft_name_input",
        help="Used when creating or overwriting a saved draft.",
    )

    if state.has_unsaved_changes():
        st.warning("Unsaved changes")
    else:
        st.caption("All changes saved")

    allow_replace = st.checkbox(
        "Allow replacing unsaved work when loading a different draft",
        key="allow_replace_unsaved",
    )

    try:
        drafts = draft_service.list_drafts()
    except Exception as exc:
        st.error(f"Could not fetch drafts: {exc}")
        drafts = []

    draft_options = {"": "-- Select a saved draft --"}
    for draft in drafts:
        label = f"{draft.name} ({draft.updated_at[:19]})"
        draft_options[draft.draft_id] = label

    selected_draft_id = st.selectbox(
        "Saved drafts",
        options=list(draft_options.keys()),
        format_func=draft_options.get,
        key="selected_saved_draft",
    )

    if selected_draft_id:
        selected_summary = next((draft for draft in drafts if draft.draft_id == selected_draft_id), None)
        if selected_summary is not None:
            st.caption(
                f"Owner: `{selected_summary.owner_user_id}`  |  Last modified by: "
                f"`{selected_summary.last_modified_by_user_id}`"
            )

    if st.button("Save Draft", type="primary", use_container_width=True):
        _save_draft(identity, force_new=False)

    if st.button("Save As New Draft", use_container_width=True):
        _save_draft(identity, force_new=True)

    if st.button("New Draft", use_container_width=True):
        if state.has_unsaved_changes() and not allow_replace:
            st.error("Enable the replacement checkbox before discarding unsaved work.")
        else:
            state.clear_project_state()
            st.rerun()

    if st.button("Load Selected Draft", use_container_width=True):
        if not selected_draft_id:
            st.error("Select a draft to load.")
        elif state.has_unsaved_changes() and not allow_replace:
            st.error("Enable the replacement checkbox before loading over unsaved work.")
        else:
            _load_selected_draft(selected_draft_id)

    if st.button("Delete Selected Draft", use_container_width=True):
        if not selected_draft_id:
            st.error("Select a draft to delete.")
        elif state.has_unsaved_changes() and state.get_current_draft_id() == selected_draft_id and not allow_replace:
            st.error("Enable the replacement checkbox before deleting the current unsaved draft.")
        else:
            _delete_selected_draft(selected_draft_id)


def main() -> None:
    state.init_state()

    if not supabase_service.is_configured():
        _render_setup_help()
        return

    identity = _restore_identity()
    if identity is None:
        _render_auth_screen()
        return

    doc_meta = state.get_document_meta()

    st.title("Business Process Document Generator")
    st.caption("Build BPDs block-by-block, save drafts, and export a polished .docx.")
    st.caption("Set fixed header logo paths in src/document/header_footer.py.")

    with st.sidebar:
        _render_drafts_panel(identity)

        st.divider()
        st.header("Add a block")
        block_type_choice = st.selectbox(
            "Block type",
            options=[b.value for b in BlockType],
            key="add_block_choice",
        )
        st.button(
            "Add Block",
            type="primary",
            use_container_width=True,
            on_click=_add_block_callback,
            args=(block_type_choice,),
        )

        st.divider()
        st.subheader("Document")
        doc_meta["header_title"] = st.text_input(
            "Header title",
            value=doc_meta.get("header_title", ""),
            key="doc_header_title",
            help="Shown in uppercase between the two logos.",
        )
        doc_meta["module_name"] = st.text_input(
            "Module name",
            value=doc_meta.get("module_name", ""),
            key="doc_module_name",
            help='Used in the footer as "BPD <module name>".',
        )
        doc_meta["project_name"] = st.text_input(
            "Project name",
            value=doc_meta.get("project_name", "S4 HANA SANMAR"),
            key="doc_project_name",
            help='Used on the right side of the footer as "Project: <name>".',
        )

        doc_name = st.text_input(
            "File name",
            value=f"BPD_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
            key="doc_filename",
        )

        blocks = state.get_blocks()
        can_generate = bool(blocks)
        generate_clicked = st.button(
            "Generate Document",
            type="primary",
            disabled=not can_generate,
            use_container_width=True,
        )
        if not can_generate:
            st.caption("Add at least one block to enable generation.")

        st.divider()
        st.caption(
            "Tip: when Word opens the document, accept the prompt to update "
            "fields so the Table of Contents reflects the latest headings."
        )

    st.subheader("Document blocks")
    blocks = state.get_blocks()
    if not blocks:
        st.info("No blocks yet - use Add Block in the sidebar to begin.")
    else:
        total = len(blocks)
        for idx, block in enumerate(blocks):
            render_block_card(idx, block, total)

    if generate_clicked and blocks:
        try:
            builder = BPDDocumentBuilder()
            data = builder.build(
                state.to_domain_blocks(),
                branding=state.to_document_branding(),
            )
        except Exception as exc:
            st.error(f"Failed to generate document: {exc}")
            return

        filename = doc_name.strip() or "BPD.docx"
        if not filename.lower().endswith(".docx"):
            filename += ".docx"

        st.success("Document generated.")
        st.download_button(
            label="Download .docx",
            data=data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
