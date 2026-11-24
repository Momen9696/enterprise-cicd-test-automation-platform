from __future__ import annotations

import httpx

from app.config import get_settings


def github_status() -> dict:
    settings = get_settings()
    if not settings.github_token or not settings.github_repository:
        return {
            "provider": "github_actions",
            "configured": False,
            "reachable": None,
            "detail": "GitHub token or repository is not configured. Local templates remain available.",
            "remote_count": 0,
        }
    url = f"https://api.github.com/repos/{settings.github_repository}/actions/workflows"
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cicd-test-automation-platform",
    }
    try:
        response = httpx.get(url, headers=headers, timeout=10.0)
    except httpx.HTTPError:
        return {
            "provider": "github_actions",
            "configured": True,
            "reachable": False,
            "detail": "GitHub API request failed",
            "remote_count": 0,
        }
    if response.status_code != 200:
        return {
            "provider": "github_actions",
            "configured": True,
            "reachable": False,
            "detail": f"GitHub API status {response.status_code}",
            "remote_count": 0,
        }
    workflows = response.json().get("workflows", [])
    return {
        "provider": "github_actions",
        "configured": True,
        "reachable": True,
        "detail": "Listed remote workflows",
        "remote_count": len(workflows),
    }


def azure_status() -> dict:
    settings = get_settings()
    if not settings.azure_org or not settings.azure_project or not settings.azure_pat:
        return {
            "provider": "azure_devops",
            "configured": False,
            "reachable": None,
            "detail": "Azure organization, project, or PAT is not configured. Local templates remain available.",
            "remote_count": 0,
        }
    url = (
        f"https://dev.azure.com/{settings.azure_org}/{settings.azure_project}"
        "/_apis/pipelines?api-version=7.1"
    )
    try:
        response = httpx.get(url, auth=("", settings.azure_pat), timeout=10.0)
    except httpx.HTTPError:
        return {
            "provider": "azure_devops",
            "configured": True,
            "reachable": False,
            "detail": "Azure DevOps request failed",
            "remote_count": 0,
        }
    if response.status_code != 200:
        return {
            "provider": "azure_devops",
            "configured": True,
            "reachable": False,
            "detail": f"Azure DevOps status {response.status_code}",
            "remote_count": 0,
        }
    items = response.json().get("value", [])
    return {
        "provider": "azure_devops",
        "configured": True,
        "reachable": True,
        "detail": "Listed remote pipelines",
        "remote_count": len(items),
    }
