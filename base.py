from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable
from ..models import Listing

class Source(ABC):
    name: str
    @abstractmethod
    def fetch(self) -> Iterable[Listing]: ...
