from typing import (
    Any,
    Optional,
    Union
)


async def indexof(lst: list, value: Any) -> Optional[int]:
    for index, item in enumerate(lst):
        if item == value:
            return index
    return None
