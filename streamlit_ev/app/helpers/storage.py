"""
Storage abstraction layer for schema management.

This module provides a unified interface for reading and writing schemas,
abstracting the underlying storage backend (GitHub or GCS).

When GitHub integration is configured:
- UI reads/writes schemas to/from GitHub repository
- GitHub Actions syncs changes to GCS for the validator function

When GitHub is not configured (fallback mode):
- UI reads/writes directly to/from GCS (legacy behavior)
"""

import os
import streamlit as st
from typing import Dict, List, Any, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

# Check which storage backend to use
GITHUB_CONFIGURED = bool(os.getenv("SCHEMA_REPO_OWNER") and os.getenv("SCHEMA_REPO_NAME"))


def is_github_mode() -> bool:
    """Check if GitHub storage mode is enabled."""
    return GITHUB_CONFIGURED


def get_storage_info() -> Dict[str, Any]:
    """Get information about the current storage configuration."""
    if GITHUB_CONFIGURED:
        from helpers.github import SCHEMA_REPO_OWNER, SCHEMA_REPO_NAME, get_repo_url
        return {
            "mode": "github",
            "owner": SCHEMA_REPO_OWNER,
            "repo": SCHEMA_REPO_NAME,
            "url": get_repo_url(),
            "branches_supported": True,
        }
    else:
        bucket = os.getenv("BUCKET_NAME", "not configured")
        return {
            "mode": "gcs",
            "bucket": bucket,
            "branches_supported": False,
        }


# Branch management (GitHub mode only)
def list_branches() -> List[str]:
    """List available branches (GitHub mode) or return single default (GCS mode)."""
    if GITHUB_CONFIGURED:
        from helpers.github import list_branches as gh_list_branches
        return gh_list_branches()
    return ["main"]


def get_current_branch() -> str:
    """Get the currently selected branch."""
    if GITHUB_CONFIGURED:
        from helpers.github import get_current_branch as gh_get_current_branch
        return gh_get_current_branch()
    return "main"


def set_current_branch(branch: str):
    """Set the current branch (GitHub mode only)."""
    if GITHUB_CONFIGURED:
        from helpers.github import set_current_branch as gh_set_current_branch
        gh_set_current_branch(branch)


# Schema operations
def list_schemas(branch: Optional[str] = None) -> List[str]:
    """
    List all schema files.

    Args:
        branch: Branch to list from (GitHub mode only).

    Returns:
        List of schema filenames.
    """
    if GITHUB_CONFIGURED:
        from helpers.github import list_schemas as gh_list_schemas, get_current_branch
        branch = branch or get_current_branch()
        return gh_list_schemas(branch)
    else:
        from helpers.gcp import listAllSchemas
        all_files = listAllSchemas()
        repo_file = os.getenv("REPO_JSON_FILE", "repo.json")
        return [f for f in all_files if f != repo_file]


def read_schema(schema_name: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """
    Read a single schema file.

    Args:
        schema_name: The schema filename.
        branch: Branch to read from (GitHub mode only).

    Returns:
        The parsed schema as a dictionary.
    """
    if GITHUB_CONFIGURED:
        from helpers.github import read_schema as gh_read_schema, get_current_branch
        branch = branch or get_current_branch()
        return gh_read_schema(schema_name, branch)
    else:
        from helpers.gcp import readSchemaToJson
        return readSchemaToJson(schema_name)


def read_schemas_parallel(schema_names: List[str], branch: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Read multiple schemas in parallel.

    Args:
        schema_names: List of schema filenames.
        branch: Branch to read from (GitHub mode only).

    Returns:
        Dictionary mapping schema names to their contents.
    """
    if GITHUB_CONFIGURED:
        from helpers.github import read_schemas_parallel as gh_read_schemas, get_current_branch
        branch = branch or get_current_branch()
        return gh_read_schemas(schema_names, branch)
    else:
        from helpers.gcp import read_schemas_parallel as gcp_read_schemas
        return gcp_read_schemas(schema_names)


def write_schema(
    schema_name: str,
    content: Dict[str, Any],
    branch: Optional[str] = None,
    commit_message: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Write/update a schema file.

    Args:
        schema_name: The schema filename.
        content: The schema content.
        branch: Branch to write to (GitHub mode only).
        commit_message: Commit message (GitHub mode only).

    Returns:
        Tuple of (success, message).
    """
    if GITHUB_CONFIGURED:
        from helpers.github import write_schema as gh_write_schema, get_current_branch
        branch = branch or get_current_branch()
        return gh_write_schema(schema_name, content, branch, commit_message)
    else:
        from helpers.gcp import uploadJson
        try:
            uploadJson(content, schema_name, silent=True)
            if st.session_state.get("upload_status"):
                return True, f"Successfully saved {schema_name}"
            else:
                return False, st.session_state.get("upload_error", "Unknown error")
        except Exception as e:
            return False, str(e)


def write_multiple_schemas(
    schemas: Dict[str, Dict[str, Any]],
    branch: Optional[str] = None,
    commit_message: Optional[str] = None
) -> Tuple[int, List[str]]:
    """
    Write multiple schemas.

    Args:
        schemas: Dict mapping schema names to their content.
        branch: Branch to write to (GitHub mode only).
        commit_message: Base commit message.

    Returns:
        Tuple of (success_count, errors).
    """
    if GITHUB_CONFIGURED:
        from helpers.github import write_multiple_schemas as gh_write_multiple, get_current_branch
        branch = branch or get_current_branch()
        return gh_write_multiple(schemas, branch, commit_message)
    else:
        success_count = 0
        errors = []
        for name, content in schemas.items():
            success, msg = write_schema(name, content)
            if success:
                success_count += 1
            else:
                errors.append(msg)
        return success_count, errors


# Repo.json operations
def read_repo() -> Dict[str, Any]:
    """
    Read the parameter repository (repo.json).

    Returns:
        The parsed repo.json as a dictionary.
    """
    if GITHUB_CONFIGURED:
        from helpers.github import read_repo_json, get_current_branch
        return read_repo_json(get_current_branch())
    else:
        from helpers.gcp import readRepoFromJson
        return readRepoFromJson()


def write_repo(
    content: Dict[str, Any],
    branch: Optional[str] = None,
    commit_message: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Write the parameter repository (repo.json).

    Args:
        content: The repo content.
        branch: Branch to write to (GitHub mode only).
        commit_message: Commit message (GitHub mode only).

    Returns:
        Tuple of (success, message).
    """
    if GITHUB_CONFIGURED:
        from helpers.github import write_repo_json, get_current_branch
        branch = branch or get_current_branch()
        return write_repo_json(content, branch, commit_message)
    else:
        from helpers.gcp import writeRepoToJson
        try:
            writeRepoToJson(content)
            return True, "Repository updated successfully"
        except Exception as e:
            return False, str(e)


# Branch operations (GitHub mode only)
def create_branch(new_branch: str, from_branch: Optional[str] = None) -> Tuple[bool, str]:
    """
    Create a new branch.

    Args:
        new_branch: Name for the new branch.
        from_branch: Branch to create from.

    Returns:
        Tuple of (success, message).
    """
    if not GITHUB_CONFIGURED:
        return False, "Branch creation requires GitHub mode"

    from helpers.github import create_branch as gh_create_branch, get_current_branch
    from_branch = from_branch or get_current_branch()
    return gh_create_branch(new_branch, from_branch)


def create_pull_request(
    title: str,
    body: str,
    head_branch: str,
    base_branch: Optional[str] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Create a pull request.

    Args:
        title: PR title.
        body: PR description.
        head_branch: Branch with changes.
        base_branch: Branch to merge into.

    Returns:
        Tuple of (success, message, pr_url).
    """
    if not GITHUB_CONFIGURED:
        return False, "PR creation requires GitHub mode", None

    from helpers.github import create_pull_request as gh_create_pr, DEFAULT_BRANCH
    base_branch = base_branch or DEFAULT_BRANCH
    return gh_create_pr(title, body, head_branch, base_branch)


def get_commit_history(
    file_path: Optional[str] = None,
    branch: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get commit history.

    Args:
        file_path: Optional file path to filter.
        branch: Branch to get history for.
        limit: Maximum commits to return.

    Returns:
        List of commit information.
    """
    if not GITHUB_CONFIGURED:
        return []

    from helpers.github import get_commit_history as gh_get_history, get_current_branch
    branch = branch or get_current_branch()
    return gh_get_history(file_path, branch, limit)


# Cache invalidation
def clear_cache():
    """Clear all storage-related caches."""
    if "explorer_cache" in st.session_state:
        st.session_state.explorer_cache = {"schemas": {}, "health": {}, "last_sync": None}
    if "repo" in st.session_state:
        del st.session_state.repo
