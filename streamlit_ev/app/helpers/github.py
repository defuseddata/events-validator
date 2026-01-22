"""
GitHub API helper for schema repository operations.

This module provides functions to interact with a separate GitHub repository
that stores event validation schemas. It supports:
- Reading schemas from any branch
- Listing available branches
- Creating/updating files via commits
- Creating pull requests for schema changes
"""

import os
import json
import base64
import requests
import streamlit as st
from typing import Optional, Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SCHEMA_REPO_OWNER = os.getenv("SCHEMA_REPO_OWNER")
SCHEMA_REPO_NAME = os.getenv("SCHEMA_REPO_NAME")
SCHEMA_REPO_PATH = os.getenv("SCHEMA_REPO_PATH", "schemas")  # Path within repo where schemas live
DEFAULT_BRANCH = os.getenv("SCHEMA_REPO_DEFAULT_BRANCH", "main")

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

# Cache for GitHub client
_github_headers = None


def _get_headers() -> Dict[str, str]:
    """Get headers for GitHub API requests."""
    global _github_headers
    if _github_headers is None:
        _github_headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if GITHUB_TOKEN:
            _github_headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return _github_headers


def is_configured() -> bool:
    """Check if GitHub integration is properly configured."""
    return bool(SCHEMA_REPO_OWNER and SCHEMA_REPO_NAME)


def get_repo_url() -> str:
    """Get the full repository URL."""
    return f"https://github.com/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}"


def list_branches() -> List[str]:
    """
    List all branches in the schema repository.

    Returns:
        List of branch names, with default branch first.
    """
    if not is_configured():
        return [DEFAULT_BRANCH]

    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/branches"

    try:
        response = requests.get(url, headers=_get_headers(), timeout=10)
        response.raise_for_status()

        branches = [b["name"] for b in response.json()]

        # Put default branch first
        if DEFAULT_BRANCH in branches:
            branches.remove(DEFAULT_BRANCH)
            branches.insert(0, DEFAULT_BRANCH)

        return branches
    except requests.exceptions.RequestException as e:
        print(f"Error listing branches: {e}")
        return [DEFAULT_BRANCH]


def list_schemas(branch: str = DEFAULT_BRANCH) -> List[str]:
    """
    List all schema files in the repository for a given branch.

    Args:
        branch: The branch name to list schemas from.

    Returns:
        List of schema filenames (e.g., ["purchase.json", "add_to_cart.json"]).
    """
    if not is_configured():
        return []

    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/contents/{SCHEMA_REPO_PATH}"
    params = {"ref": branch}

    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()

        files = response.json()
        schema_files = [
            f["name"] for f in files
            if f["type"] == "file" and f["name"].endswith(".json") and f["name"] != "repo.json"
        ]
        return sorted(schema_files)
    except requests.exceptions.RequestException as e:
        print(f"Error listing schemas: {e}")
        return []


def read_schema(schema_name: str, branch: str = DEFAULT_BRANCH) -> Dict[str, Any]:
    """
    Read a single schema file from the repository.

    Args:
        schema_name: The schema filename (e.g., "purchase.json").
        branch: The branch to read from.

    Returns:
        The parsed JSON schema as a dictionary, or empty dict on error.
    """
    if not is_configured():
        return {}

    # Ensure .json extension
    if not schema_name.endswith(".json"):
        schema_name = f"{schema_name}.json"

    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/contents/{SCHEMA_REPO_PATH}/{schema_name}"
    params = {"ref": branch}

    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content)
    except requests.exceptions.RequestException as e:
        print(f"Error reading schema {schema_name}: {e}")
        return {}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing schema {schema_name}: {e}")
        return {}


def read_schemas_parallel(schema_names: List[str], branch: str = DEFAULT_BRANCH) -> Dict[str, Dict[str, Any]]:
    """
    Read multiple schemas in parallel.

    Args:
        schema_names: List of schema filenames to read.
        branch: The branch to read from.

    Returns:
        Dictionary mapping schema names to their contents.
    """
    def fetch_one(name: str) -> Tuple[str, Dict[str, Any]]:
        return (name, read_schema(name, branch))

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_one, schema_names))

    return dict(results)


def read_repo_json(branch: str = DEFAULT_BRANCH) -> Dict[str, Any]:
    """
    Read the repo.json file (parameter repository) from the schema repo.

    Args:
        branch: The branch to read from.

    Returns:
        The parsed repo.json as a dictionary, or empty dict if not found.
    """
    if not is_configured():
        return {}

    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/contents/{SCHEMA_REPO_PATH}/repo.json"
    params = {"ref": branch}

    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if response.status_code == 404:
            return {}
        response.raise_for_status()

        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content)
    except requests.exceptions.RequestException as e:
        print(f"Error reading repo.json: {e}")
        return {}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing repo.json: {e}")
        return {}


def get_file_sha(file_path: str, branch: str = DEFAULT_BRANCH) -> Optional[str]:
    """
    Get the SHA of a file (required for updates).

    Args:
        file_path: Path to the file within the repo.
        branch: The branch to check.

    Returns:
        The file SHA or None if file doesn't exist.
    """
    if not is_configured():
        return None

    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/contents/{file_path}"
    params = {"ref": branch}

    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("sha")
    except requests.exceptions.RequestException:
        return None


def write_schema(
    schema_name: str,
    content: Dict[str, Any],
    branch: str = DEFAULT_BRANCH,
    commit_message: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Write/update a schema file in the repository.

    Args:
        schema_name: The schema filename (e.g., "purchase.json").
        content: The schema content as a dictionary.
        branch: The branch to write to.
        commit_message: Optional commit message.

    Returns:
        Tuple of (success: bool, message: str).
    """
    if not is_configured():
        return False, "GitHub integration not configured"

    if not GITHUB_TOKEN:
        return False, "GitHub token required for write operations"

    # Ensure .json extension
    if not schema_name.endswith(".json"):
        schema_name = f"{schema_name}.json"

    file_path = f"{SCHEMA_REPO_PATH}/{schema_name}"
    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/contents/{file_path}"

    # Get existing file SHA if updating
    sha = get_file_sha(file_path, branch)

    # Prepare content
    json_content = json.dumps(content, indent=2)
    encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

    # Prepare request body
    body = {
        "message": commit_message or f"Update {schema_name}",
        "content": encoded_content,
        "branch": branch,
    }

    if sha:
        body["sha"] = sha

    try:
        response = requests.put(url, headers=_get_headers(), json=body, timeout=30)
        response.raise_for_status()
        return True, f"Successfully saved {schema_name}"
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_msg = e.response.json().get("message", str(e))
            except:
                pass
        return False, f"Error saving {schema_name}: {error_msg}"


def write_repo_json(
    content: Dict[str, Any],
    branch: str = DEFAULT_BRANCH,
    commit_message: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Write/update the repo.json file in the repository.

    Args:
        content: The repo.json content as a dictionary.
        branch: The branch to write to.
        commit_message: Optional commit message.

    Returns:
        Tuple of (success: bool, message: str).
    """
    if not is_configured():
        return False, "GitHub integration not configured"

    if not GITHUB_TOKEN:
        return False, "GitHub token required for write operations"

    file_path = f"{SCHEMA_REPO_PATH}/repo.json"
    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/contents/{file_path}"

    # Get existing file SHA if updating
    sha = get_file_sha(file_path, branch)

    # Prepare content
    json_content = json.dumps(content, indent=2)
    encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

    # Prepare request body
    body = {
        "message": commit_message or "Update repo.json",
        "content": encoded_content,
        "branch": branch,
    }

    if sha:
        body["sha"] = sha

    try:
        response = requests.put(url, headers=_get_headers(), json=body, timeout=30)
        response.raise_for_status()
        return True, "Successfully saved repo.json"
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_msg = e.response.json().get("message", str(e))
            except:
                pass
        return False, f"Error saving repo.json: {error_msg}"


def write_multiple_schemas(
    schemas: Dict[str, Dict[str, Any]],
    branch: str = DEFAULT_BRANCH,
    commit_message: Optional[str] = None
) -> Tuple[int, List[str]]:
    """
    Write multiple schemas in a batch (sequential commits).

    Note: For true atomic batch updates, consider using the Git Data API
    to create a single commit with multiple file changes.

    Args:
        schemas: Dict mapping schema names to their content.
        branch: The branch to write to.
        commit_message: Base commit message.

    Returns:
        Tuple of (success_count: int, errors: List[str]).
    """
    success_count = 0
    errors = []

    for schema_name, content in schemas.items():
        msg = commit_message or f"Update {schema_name}"
        success, error = write_schema(schema_name, content, branch, msg)
        if success:
            success_count += 1
        else:
            errors.append(error)

    return success_count, errors


def create_branch(new_branch: str, from_branch: str = DEFAULT_BRANCH) -> Tuple[bool, str]:
    """
    Create a new branch from an existing branch.

    Args:
        new_branch: Name of the new branch to create.
        from_branch: The branch to create from.

    Returns:
        Tuple of (success: bool, message: str).
    """
    if not is_configured():
        return False, "GitHub integration not configured"

    if not GITHUB_TOKEN:
        return False, "GitHub token required for branch creation"

    # Get the SHA of the source branch
    ref_url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/git/refs/heads/{from_branch}"

    try:
        response = requests.get(ref_url, headers=_get_headers(), timeout=10)
        response.raise_for_status()
        sha = response.json()["object"]["sha"]
    except requests.exceptions.RequestException as e:
        return False, f"Error getting source branch: {e}"

    # Create new branch
    create_url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/git/refs"
    body = {
        "ref": f"refs/heads/{new_branch}",
        "sha": sha,
    }

    try:
        response = requests.post(create_url, headers=_get_headers(), json=body, timeout=10)
        if response.status_code == 422:
            return False, f"Branch '{new_branch}' already exists"
        response.raise_for_status()
        return True, f"Successfully created branch '{new_branch}'"
    except requests.exceptions.RequestException as e:
        return False, f"Error creating branch: {e}"


def create_pull_request(
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = DEFAULT_BRANCH
) -> Tuple[bool, str, Optional[str]]:
    """
    Create a pull request.

    Args:
        title: PR title.
        body: PR description.
        head_branch: The branch with changes.
        base_branch: The branch to merge into.

    Returns:
        Tuple of (success: bool, message: str, pr_url: Optional[str]).
    """
    if not is_configured():
        return False, "GitHub integration not configured", None

    if not GITHUB_TOKEN:
        return False, "GitHub token required for PR creation", None

    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/pulls"

    pr_body = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch,
    }

    try:
        response = requests.post(url, headers=_get_headers(), json=pr_body, timeout=30)
        response.raise_for_status()
        pr_data = response.json()
        return True, "Pull request created", pr_data.get("html_url")
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_msg = e.response.json().get("message", str(e))
            except:
                pass
        return False, f"Error creating PR: {error_msg}", None


def get_commit_history(
    file_path: Optional[str] = None,
    branch: str = DEFAULT_BRANCH,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get commit history, optionally filtered by file.

    Args:
        file_path: Optional file path to filter commits.
        branch: The branch to get history for.
        limit: Maximum number of commits to return.

    Returns:
        List of commit information dictionaries.
    """
    if not is_configured():
        return []

    url = f"{GITHUB_API_BASE}/repos/{SCHEMA_REPO_OWNER}/{SCHEMA_REPO_NAME}/commits"
    params = {
        "sha": branch,
        "per_page": limit,
    }

    if file_path:
        params["path"] = file_path

    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()

        commits = []
        for c in response.json():
            commits.append({
                "sha": c["sha"][:7],
                "message": c["commit"]["message"],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
                "url": c["html_url"],
            })
        return commits
    except requests.exceptions.RequestException as e:
        print(f"Error getting commit history: {e}")
        return []


# Session state helpers for branch management
def get_current_branch() -> str:
    """Get the currently selected branch from session state."""
    return st.session_state.get("schema_branch", DEFAULT_BRANCH)


def set_current_branch(branch: str):
    """Set the current branch in session state and clear caches."""
    if st.session_state.get("schema_branch") != branch:
        st.session_state.schema_branch = branch
        # Clear caches when branch changes
        if "explorer_cache" in st.session_state:
            st.session_state.explorer_cache = {"schemas": {}, "health": {}, "last_sync": None}
        if "repo" in st.session_state:
            del st.session_state.repo
