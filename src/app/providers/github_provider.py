
import httpx
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GitHubProvider:
    """
    Fetches data from GitHub API:
    - Assigned issues
    - Pull requests
    - Recent notifications
    """
    
    def __init__(self, settings):
        self.settings = settings
        if not self.settings.github_token:
            raise ValueError("GITHUB_TOKEN not configured in .env")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    def fetch(self, limit: int = 10, data_type: str = "all") -> Dict[str, Any]:
        """
        Fetch GitHub data
        
        Args:
            limit: Maximum number of items to return
            data_type: Type of data to fetch: "issues", "prs", "notifications", "all"
        
        Returns:
            Dict with provider name, count, and items
        """
        items = []
        
        try:
            if data_type in ["issues", "all"]:
                items.extend(self._fetch_issues(limit))
            
            if data_type in ["prs", "all"]:
                items.extend(self._fetch_pull_requests(limit))
            
            if data_type in ["notifications", "all"]:
                items.extend(self._fetch_notifications(limit))
            
            # Sort by date and apply limit
            items.sort(key=lambda x: x.get("metadata", {}).get("created_at", ""), reverse=True)
            items = items[:limit]
            
            return {
                "provider": "GitHubProvider",
                "count": len(items),
                "items": items
            }
        
        except Exception as e:
            logger.error(f"GitHub fetch error: {e}")
            raise
    
    def _fetch_issues(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch assigned issues"""
        try:
            response = httpx.get(
                f"{self.base_url}/issues",
                headers=self.headers,
                params={
                    "filter": "assigned",
                    "state": "open",
                    "per_page": limit,
                    "sort": "updated",
                    "direction": "desc"
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            issues = response.json()
            return [self._format_issue(issue) for issue in issues if "pull_request" not in issue]
        
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch issues: {e}")
            return []
    
    def _fetch_pull_requests(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch user's pull requests"""
        try:
            # Get authenticated user
            user_response = httpx.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=10.0
            )
            user_response.raise_for_status()
            username = user_response.json()["login"]
            
            # Search for user's PRs
            response = httpx.get(
                f"{self.base_url}/search/issues",
                headers=self.headers,
                params={
                    "q": f"is:pr author:{username} is:open",
                    "sort": "updated",
                    "order": "desc",
                    "per_page": limit
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            prs = response.json().get("items", [])
            return [self._format_pr(pr) for pr in prs]
        
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch PRs: {e}")
            return []
    
    def _fetch_notifications(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch recent notifications"""
        try:
            response = httpx.get(
                f"{self.base_url}/notifications",
                headers=self.headers,
                params={
                    "per_page": limit,
                    "participating": "true"
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            notifications = response.json()
            return [self._format_notification(notif) for notif in notifications]
        
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch notifications: {e}")
            return []
    
    def _format_issue(self, issue: Dict) -> Dict[str, Any]:
        """Format issue data"""
        return {
            "source": "github_issue",
            "title": f"Issue: {issue['title']}",
            "snippet": f"#{issue['number']} in {issue['repository_url'].split('/')[-1]} - {issue['state']}",
            "url": issue["html_url"],
            "metadata": {
                "number": issue["number"],
                "state": issue["state"],
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "labels": [label["name"] for label in issue.get("labels", [])],
                "repository": issue["repository_url"].split("/")[-1]
            }
        }
    
    def _format_pr(self, pr: Dict) -> Dict[str, Any]:
        """Format pull request data"""
        return {
            "source": "github_pr",
            "title": f"PR: {pr['title']}",
            "snippet": f"#{pr['number']} - {pr['state']}",
            "url": pr["html_url"],
            "metadata": {
                "number": pr["number"],
                "state": pr["state"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "draft": pr.get("draft", False)
            }
        }
    
    def _format_notification(self, notif: Dict) -> Dict[str, Any]:
        """Format notification data"""
        return {
            "source": "github_notification",
            "title": f"Notification: {notif['subject']['title']}",
            "snippet": f"{notif['subject']['type']} - {notif['reason']}",
            "url": notif["subject"].get("url", ""),
            "metadata": {
                "type": notif["subject"]["type"],
                "reason": notif["reason"],
                "updated_at": notif["updated_at"],
                "unread": notif["unread"]
            }
        }
    
    def diagnostics(self) -> Dict[str, Any]:
        """Run diagnostics on GitHub API connection"""
        try:
            response = httpx.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                user = response.json()
                return {
                    "ok": True,
                    "authenticated_user": user["login"],
                    "rate_limit": response.headers.get("x-ratelimit-remaining"),
                    "api_version": response.headers.get("x-github-api-version")
                }
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}",
                    "message": response.text
                }
        
        except Exception as e:
            return {
                "ok": False,
                "error": str(e)
            }
