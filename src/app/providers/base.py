from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from ..schemas.query import ContextItem


class Provider(ABC):
    name: str

    @abstractmethod
    async def fetch(self, query: str, limit: int = 5) -> List[ContextItem]:
        ...
