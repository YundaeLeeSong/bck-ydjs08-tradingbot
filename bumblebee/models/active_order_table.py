import json
from dataclasses import asdict
from typing import Dict, List, Optional
from .active_order_dto import ActiveOrderDTO

class ActiveOrderTable:
    """
    An abstraction for holding a collection of ActiveOrderDTO objects.
    Maps order IDs to their corresponding DTOs.
    """
    def __init__(self):
        self._data: Dict[str, ActiveOrderDTO] = {}

    def add(self, dto: ActiveOrderDTO) -> None:
        if not dto or not getattr(dto, 'id', None):
            return
        self._data[dto.id] = dto

    def get(self, order_id: str) -> Optional[ActiveOrderDTO]:
        if not order_id or not isinstance(order_id, str):
            return None
        return self._data.get(order_id)

    def get_all(self) -> List[ActiveOrderDTO]:
        return list(self._data.values())

    def remove(self, order_id: str) -> None:
        if order_id and isinstance(order_id, str) and order_id in self._data:
            del self._data[order_id]

    def __repr__(self) -> str:
        return json.dumps({k: asdict(v) for k, v in self._data.items()}, indent=2)
