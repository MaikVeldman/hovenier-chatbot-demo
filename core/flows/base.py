from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class BaseFlow(ABC):
    @abstractmethod
    def get_question(self) -> str: ...

    @abstractmethod
    def handle(self, user_text: str) -> Tuple[str, bool]: ...

    @abstractmethod
    def to_answers(self) -> Dict[str, Any]: ...
