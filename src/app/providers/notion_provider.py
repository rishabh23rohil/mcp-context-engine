"""
Notion Provider - Fetches databases and pages
"""
import httpx
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotionProvider:
    """
    Fetches data from Notion API:
    - Recent pages
    - Database entries
    - Tasks/todos
    """
    
    def __init__(self, settings):
        self.settings = settings
        if not self.settings.notion_token:
            raise ValueError("NOTION_TOKEN not configured in .env")
        
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.settings.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def fetch(self, limit: int = 10) -> Dict[str, Any]:
        """
        Fetch recent Notion pages
        
        Args:
            limit: Maximum number of items to return
        
        Returns:
            Dict with provider name, count, and items
        """
        try:
            # Search for recently edited pages
            response = httpx.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json={
                    "sort": {
                        "direction": "descending",
                        "timestamp": "last_edited_time"
                    },
                    "page_size": limit
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            items = [self._format_item(item) for item in results]
            
            return {
                "provider": "NotionProvider",
                "count": len(items),
                "items": items
            }
        
        except httpx.HTTPError as e:
            logger.error(f"Notion fetch error: {e}")
            raise Exception(f"Failed to fetch from Notion: {e}")
    
    def fetch_database(self, database_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Fetch entries from a specific Notion database
        
        Args:
            database_id: The ID of the database
            limit: Maximum number of items to return
        
        Returns:
            Dict with provider name, count, and items
        """
        try:
            response = httpx.post(
                f"{self.base_url}/databases/{database_id}/query",
                headers=self.headers,
                json={
                    "page_size": limit
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            items = [self._format_database_item(item) for item in results]
            
            return {
                "provider": "NotionProvider",
                "database_id": database_id,
                "count": len(items),
                "items": items
            }
        
        except httpx.HTTPError as e:
            logger.error(f"Notion database fetch error: {e}")
            raise Exception(f"Failed to fetch database from Notion: {e}")
    
    def _format_item(self, item: Dict) -> Dict[str, Any]:
        """Format a Notion page or database item"""
        # Extract title from different property types
        title = self._extract_title(item)
        
        # Get URL
        url = item.get("url", "")
        
        # Create snippet with last edited time
        last_edited = item.get("last_edited_time", "")
        snippet = f"Last edited: {self._format_datetime(last_edited)}"
        
        return {
            "source": "notion",
            "title": title or "Untitled",
            "snippet": snippet,
            "url": url,
            "metadata": {
                "id": item.get("id"),
                "type": item.get("object"),
                "created_time": item.get("created_time"),
                "last_edited_time": last_edited,
                "archived": item.get("archived", False)
            }
        }
    
    def _format_database_item(self, item: Dict) -> Dict[str, Any]:
        """Format a database entry with properties"""
        title = self._extract_title(item)
        
        # Extract key properties
        properties = item.get("properties", {})
        property_summary = []
        
        for prop_name, prop_value in properties.items():
            if prop_name.lower() == "name" or prop_name.lower() == "title":
                continue  # Already in title
            
            prop_type = prop_value.get("type")
            if prop_type == "checkbox":
                val = "✓" if prop_value.get("checkbox") else "☐"
                property_summary.append(f"{prop_name}: {val}")
            elif prop_type == "status":
                status = prop_value.get("status", {}).get("name", "")
                if status:
                    property_summary.append(f"{prop_name}: {status}")
            elif prop_type == "date":
                date_obj = prop_value.get("date", {})
                if date_obj and date_obj.get("start"):
                    property_summary.append(f"{prop_name}: {date_obj['start']}")
        
        snippet = " | ".join(property_summary[:3]) if property_summary else "Database entry"
        
        return {
            "source": "notion_database",
            "title": title or "Untitled",
            "snippet": snippet,
            "url": item.get("url", ""),
            "metadata": {
                "id": item.get("id"),
                "created_time": item.get("created_time"),
                "last_edited_time": item.get("last_edited_time"),
                "properties": list(properties.keys())
            }
        }
    
    def _extract_title(self, item: Dict) -> str:
        """Extract title from various Notion structures"""
        # Try properties first (for database items)
        properties = item.get("properties", {})
        
        # Look for title or name property
        for prop_name in ["Name", "Title", "name", "title"]:
            if prop_name in properties:
                prop = properties[prop_name]
                prop_type = prop.get("type")
                
                if prop_type == "title" and prop.get("title"):
                    text_items = prop["title"]
                    if text_items and len(text_items) > 0:
                        return text_items[0].get("plain_text", "")
        
        # Try page title (for pages)
        if item.get("object") == "page":
            # Check parent
            parent = item.get("parent", {})
            if parent.get("type") == "page_id":
                # This is a child page, try to get title from properties
                pass
        
        return "Untitled"
    
    def _format_datetime(self, dt_str: str) -> str:
        """Format ISO datetime to readable string"""
        if not dt_str:
            return "Unknown"
        
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return dt_str
    
    def diagnostics(self) -> Dict[str, Any]:
        """Run diagnostics on Notion API connection"""
        try:
            # Try to fetch user info
            response = httpx.get(
                f"{self.base_url}/users/me",
                headers=self.headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                user = response.json()
                return {
                    "ok": True,
                    "user_type": user.get("type"),
                    "user_name": user.get("name", "Unknown"),
                    "bot_id": user.get("bot", {}).get("owner", {}).get("workspace")
                }
            else:
                return {
                    "ok": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
        
        except Exception as e:
            return {
                "ok": False,
                "error": str(e)
            }
