"""
Reusable UI components for the Events Validator application.
"""

import streamlit as st
from typing import Optional, Callable
from helpers.storage import (
    is_github_mode,
    list_branches,
    get_current_branch,
    set_current_branch,
    get_storage_info,
    create_branch,
    clear_cache,
)


def render_branch_selector(
    key: str = "branch_selector",
    on_change: Optional[Callable] = None,
    show_create: bool = True,
    compact: bool = False
):
    """
    Render a branch selector dropdown with optional create branch functionality.

    Args:
        key: Unique key for the widget.
        on_change: Optional callback when branch changes.
        show_create: Whether to show the create branch button.
        compact: Whether to use compact layout.
    """
    if not is_github_mode():
        # In GCS mode, just show a note
        if not compact:
            st.caption("Storage: GCS (single branch)")
        return

    branches = list_branches()
    current = get_current_branch()

    # Ensure current branch is in the list
    if current not in branches:
        branches.insert(0, current)

    current_idx = branches.index(current) if current in branches else 0

    if compact:
        col1, col2 = st.columns([3, 1])
        with col1:
            new_branch = st.selectbox(
                "Branch",
                branches,
                index=current_idx,
                key=key,
                label_visibility="collapsed",
            )
        with col2:
            if show_create:
                if st.button("New", key=f"{key}_create", help="Create new branch"):
                    _show_create_branch_dialog()
    else:
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            new_branch = st.selectbox(
                "Branch",
                branches,
                index=current_idx,
                key=key,
                help="Select the branch to work with",
            )
        with col2:
            if st.button("Refresh", key=f"{key}_refresh", use_container_width=True):
                clear_cache()
                st.rerun()
        with col3:
            if show_create:
                if st.button("Create Branch", key=f"{key}_create_btn", use_container_width=True):
                    _show_create_branch_dialog()

    # Handle branch change
    if new_branch != current:
        set_current_branch(new_branch)
        if on_change:
            on_change(new_branch)
        st.rerun()


@st.dialog("Create New Branch")
def _show_create_branch_dialog():
    """Dialog for creating a new branch."""
    current = get_current_branch()

    st.markdown(f"Creating a new branch from **{current}**")

    new_name = st.text_input(
        "Branch name",
        placeholder="feature/my-new-schema",
        help="Use lowercase letters, numbers, and hyphens. Slashes are allowed for organization.",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("Create", type="primary", use_container_width=True, disabled=not new_name):
            if new_name:
                # Validate branch name
                import re
                if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9/_-]*$', new_name):
                    st.error("Invalid branch name. Use letters, numbers, hyphens, underscores, and slashes.")
                    return

                success, message = create_branch(new_name, current)
                if success:
                    st.success(message)
                    set_current_branch(new_name)
                    clear_cache()
                    st.rerun()
                else:
                    st.error(message)


def render_storage_status(detailed: bool = False):
    """
    Render a status indicator showing the current storage configuration.

    Args:
        detailed: Whether to show detailed information.
    """
    info = get_storage_info()

    if info["mode"] == "github":
        if detailed:
            st.markdown(f"""
            **Storage Mode:** GitHub Repository

            - **Repository:** [{info['owner']}/{info['repo']}]({info['url']})
            - **Current Branch:** {get_current_branch()}
            - **Multi-branch Support:** Yes

            Changes are committed to GitHub and synced to GCS via GitHub Actions.
            """)
        else:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown("**GitHub**")
            with col2:
                st.caption(f"{info['owner']}/{info['repo']} @ {get_current_branch()}")
    else:
        if detailed:
            st.markdown(f"""
            **Storage Mode:** Google Cloud Storage (Direct)

            - **Bucket:** `{info['bucket']}`
            - **Multi-branch Support:** No

            Changes are saved directly to GCS. Consider configuring GitHub integration for version control.
            """)
        else:
            st.caption(f"Storage: GCS ({info['bucket']})")


def render_commit_history(file_path: Optional[str] = None, limit: int = 5):
    """
    Render recent commit history for a file or the whole schema directory.

    Args:
        file_path: Optional file path to filter commits.
        limit: Maximum number of commits to show.
    """
    if not is_github_mode():
        st.info("Commit history requires GitHub mode")
        return

    from helpers.storage import get_commit_history

    commits = get_commit_history(file_path, limit=limit)

    if not commits:
        st.info("No commit history available")
        return

    st.markdown("**Recent Changes**")
    for commit in commits:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                # Truncate long messages
                msg = commit["message"].split("\n")[0]
                if len(msg) > 60:
                    msg = msg[:57] + "..."
                st.markdown(f"[`{commit['sha']}`]({commit['url']}) {msg}")
            with col2:
                st.caption(commit["date"][:10])


def render_sync_status():
    """
    Render the sync status between GitHub and GCS.

    This shows whether the current branch schemas are synced to GCS.
    """
    if not is_github_mode():
        return

    current = get_current_branch()

    if current == "main":
        st.success("Schemas are automatically synced to GCS on push to main")
    elif current == "staging":
        st.info("Staging branch schemas are synced to GCS with 'staging/' prefix")
    else:
        st.warning(f"Feature branch '{current}' schemas are synced to GCS with 'branches/' prefix. Merge to main for production sync.")
