"""GitHub MCP Server — exposes GitHub REST API as MCP tools."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_DEFAULT_OWNER = os.getenv("GITHUB_DEFAULT_OWNER", "")

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN is not set. Copy .env.example to .env and add your token.")

mcp = FastMCP("github")

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get(path: str, params: dict | None = None) -> Any:
    url = f"{GITHUB_API_URL}{path}"
    with httpx.Client() as client:
        resp = client.get(url, headers=_headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()


def _post(path: str, body: dict) -> Any:
    url = f"{GITHUB_API_URL}{path}"
    with httpx.Client() as client:
        resp = client.post(url, headers=_headers(), json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()


def _patch(path: str, body: dict) -> Any:
    url = f"{GITHUB_API_URL}{path}"
    with httpx.Client() as client:
        resp = client.patch(url, headers=_headers(), json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()


def _delete(path: str) -> int:
    url = f"{GITHUB_API_URL}{path}"
    with httpx.Client() as client:
        resp = client.delete(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        return resp.status_code


# ---------------------------------------------------------------------------
# Repository tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_repository(owner: str, repo: str) -> dict:
    """Get information about a GitHub repository."""
    return _get(f"/repos/{owner}/{repo}")


@mcp.tool()
def list_repositories(username: str, repo_type: str = "all", per_page: int = 30) -> list:
    """
    List repositories for a user or organization.

    Args:
        username: GitHub username or organization name.
        repo_type: One of 'all', 'owner', 'member', 'public', 'private'.
        per_page: Number of results per page (max 100).
    """
    return _get(f"/users/{username}/repos", {"type": repo_type, "per_page": per_page})


@mcp.tool()
def search_repositories(query: str, sort: str = "best match", per_page: int = 10) -> dict:
    """
    Search GitHub repositories.

    Args:
        query: Search query (supports GitHub search syntax).
        sort: Sort by 'stars', 'forks', 'help-wanted-issues', or 'updated'.
        per_page: Number of results (max 100).
    """
    params: dict[str, Any] = {"q": query, "per_page": per_page}
    if sort != "best match":
        params["sort"] = sort
    return _get("/search/repositories", params)


# ---------------------------------------------------------------------------
# Issue tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str = "",
    per_page: int = 20,
) -> list:
    """
    List issues in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: 'open', 'closed', or 'all'.
        labels: Comma-separated label names to filter by.
        per_page: Number of results (max 100).
    """
    params: dict[str, Any] = {"state": state, "per_page": per_page}
    if labels:
        params["labels"] = labels
    return _get(f"/repos/{owner}/{repo}/issues", params)


@mcp.tool()
def get_issue(owner: str, repo: str, issue_number: int) -> dict:
    """Get a single issue by number."""
    return _get(f"/repos/{owner}/{repo}/issues/{issue_number}")


@mcp.tool()
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """
    Create a new issue in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: Issue title.
        body: Issue body (markdown supported).
        labels: List of label names to apply.
        assignees: List of usernames to assign.
    """
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees
    return _post(f"/repos/{owner}/{repo}/issues", payload)


@mcp.tool()
def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: str = "",
    body: str = "",
    state: str = "",
) -> dict:
    """
    Update an existing issue.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number to update.
        title: New title (leave empty to keep current).
        body: New body (leave empty to keep current).
        state: 'open' or 'closed' (leave empty to keep current).
    """
    payload: dict[str, Any] = {}
    if title:
        payload["title"] = title
    if body:
        payload["body"] = body
    if state:
        payload["state"] = state
    return _patch(f"/repos/{owner}/{repo}/issues/{issue_number}", payload)


# ---------------------------------------------------------------------------
# Pull request tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 20,
) -> list:
    """
    List pull requests in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: 'open', 'closed', or 'all'.
        per_page: Number of results (max 100).
    """
    return _get(f"/repos/{owner}/{repo}/pulls", {"state": state, "per_page": per_page})


@mcp.tool()
def get_pull_request(owner: str, repo: str, pr_number: int) -> dict:
    """Get a single pull request by number."""
    return _get(f"/repos/{owner}/{repo}/pulls/{pr_number}")


@mcp.tool()
def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    draft: bool = False,
) -> dict:
    """
    Create a pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: PR title.
        head: Branch to merge from (e.g. 'feature/my-branch').
        base: Branch to merge into (e.g. 'main').
        body: PR description (markdown supported).
        draft: Create as a draft PR.
    """
    return _post(
        f"/repos/{owner}/{repo}/pulls",
        {"title": title, "head": head, "base": base, "body": body, "draft": draft},
    )


# ---------------------------------------------------------------------------
# File / content tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_file_contents(owner: str, repo: str, path: str, ref: str = "") -> dict:
    """
    Get the contents of a file in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path within the repository.
        ref: Branch, tag, or commit SHA (defaults to the repo's default branch).
    """
    params = {"ref": ref} if ref else {}
    return _get(f"/repos/{owner}/{repo}/contents/{path}", params)


@mcp.tool()
def list_directory(owner: str, repo: str, path: str = "", ref: str = "") -> list:
    """
    List files and directories at a path in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: Directory path (empty string for root).
        ref: Branch, tag, or commit SHA.
    """
    params = {"ref": ref} if ref else {}
    result = _get(f"/repos/{owner}/{repo}/contents/{path}", params)
    if isinstance(result, list):
        return result
    return [result]


# ---------------------------------------------------------------------------
# Branch / commit tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_branches(owner: str, repo: str, per_page: int = 30) -> list:
    """List branches in a repository."""
    return _get(f"/repos/{owner}/{repo}/branches", {"per_page": per_page})


@mcp.tool()
def get_branch(owner: str, repo: str, branch: str) -> dict:
    """Get details for a specific branch."""
    return _get(f"/repos/{owner}/{repo}/branches/{branch}")


@mcp.tool()
def list_commits(
    owner: str,
    repo: str,
    sha: str = "",
    path: str = "",
    per_page: int = 20,
) -> list:
    """
    List commits in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        sha: Branch name, tag, or commit SHA to start listing from.
        path: Filter commits touching this file path.
        per_page: Number of results (max 100).
    """
    params: dict[str, Any] = {"per_page": per_page}
    if sha:
        params["sha"] = sha
    if path:
        params["path"] = path
    return _get(f"/repos/{owner}/{repo}/commits", params)


# ---------------------------------------------------------------------------
# User tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_authenticated_user() -> dict:
    """Get the currently authenticated GitHub user."""
    return _get("/user")


@mcp.tool()
def get_user(username: str) -> dict:
    """Get public information about a GitHub user."""
    return _get(f"/users/{username}")


# ---------------------------------------------------------------------------
# Release tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_releases(owner: str, repo: str, per_page: int = 10) -> list:
    """List releases for a repository."""
    return _get(f"/repos/{owner}/{repo}/releases", {"per_page": per_page})


@mcp.tool()
def get_latest_release(owner: str, repo: str) -> dict:
    """Get the latest release for a repository."""
    return _get(f"/repos/{owner}/{repo}/releases/latest")


# ---------------------------------------------------------------------------
# Label tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_labels(owner: str, repo: str) -> list:
    """List all labels for a repository."""
    return _get(f"/repos/{owner}/{repo}/labels")


@mcp.tool()
def create_label(owner: str, repo: str, name: str, color: str, description: str = "") -> dict:
    """
    Create a label in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        name: Label name.
        color: 6-character hex color code without the '#' (e.g. 'ff0000').
        description: Short description of the label.
    """
    return _post(
        f"/repos/{owner}/{repo}/labels",
        {"name": name, "color": color, "description": description},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
