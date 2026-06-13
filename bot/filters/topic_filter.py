from aiogram.filters import BaseFilter
from aiogram.types import Message


class ForumTopicFilter(BaseFilter):
    """Filter messages by forum topic thread_id."""

    def __init__(
        self,
        thread_id: int | None = None,
        thread_ids: list[int] | None = None,
    ):
        self.thread_ids: set[int] = set()
        if thread_id is not None:
            self.thread_ids.add(thread_id)
        if thread_ids is not None:
            self.thread_ids.update(thread_ids)
        # 0 znamena "nenakonfigurovany topic" -> ignorovat
        self.thread_ids.discard(0)

    async def __call__(self, message: Message) -> bool:
        # Bez nakonfigurovaneho topicu je handler neaktivny (predchadza konfliktom).
        if not self.thread_ids:
            return False
        return message.message_thread_id in self.thread_ids
