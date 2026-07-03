from dataclasses import dataclass
from typing import override


@dataclass(frozen=True, slots=True)
class NotFoundError(Exception):
    entity: str
    entity_id: str

    @override
    def __str__(self) -> str:
        return f"{self.entity} {self.entity_id} not found"
