import time
import asyncio
from typing import (
    Union
)


class SnowflakeGenerator:
    def __init__(self, worker_id: int, process_id: int, epoch: int = 1609459200000):
        self.worker_id = worker_id & 0b11111
        self.process_id = process_id & 0b11111
        self.epoch = epoch
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = asyncio.Lock()

    def _current_timestamp(self):
        return int(time.time() * 1000)

    async def _wait_for_next_millis(self, last_timestamp):
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            await asyncio.sleep(0)
            timestamp = self._current_timestamp()
        return timestamp

    async def generate(self) -> int:
        async with self.lock:
            timestamp = self._current_timestamp()

            if timestamp < self.last_timestamp:
                raise Exception("Clock moved backwards. Refusing to generate snowflake.")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & 0b111111111111
                if self.sequence == 0:
                    timestamp = await self._wait_for_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            snowflake = (
                ((timestamp - self.epoch) << 22) |
                (self.worker_id << 17) |
                (self.process_id << 12) |
                self.sequence
            )

            return snowflake