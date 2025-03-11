"""jobs has utilities for working with Pi streaming APIs"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json


from typing import Protocol, Iterator, AsyncIterator, Any

from withpi._resource import AsyncAPIResource, SyncAPIResource


class StatusMessageProtocol(Protocol):
    job_id: str


def stream(
    resource: SyncAPIResource, status: StatusMessageProtocol | str
) -> Iterator[dict[str, Any]]:
    """stream streams data and prints messages given a status."""
    if isinstance(status, str):
        job_id = status
    else:
        job_id = status.job_id

    with ThreadPoolExecutor(max_workers=1) as executor:

        def stream_messages_thread():
            with resource.with_streaming_response.stream_messages(  # type: ignore
                job_id=job_id, timeout=None
            ) as response:
                for line in response.iter_lines():
                    print(line)

        future = executor.submit(stream_messages_thread)

        if hasattr(resource.with_streaming_response, "stream_data"):  # type: ignore
            with resource.with_streaming_response.stream_data(  # type: ignore
                job_id=job_id, timeout=None
            ) as response:
                for line in response.iter_lines():
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield line
        future.result()


async def stream_async(
    resource: AsyncAPIResource, status: StatusMessageProtocol | str
) -> AsyncIterator[dict[str, Any]]:
    """stream streams data and prints messages given a status."""
    if isinstance(status, str):
        job_id = status
    else:
        job_id = status.job_id

    async with asyncio.TaskGroup() as tg:

        async def stream_messages_task():
            async with resource.with_streaming_response.stream_messages(  # type: ignore
                job_id=job_id, timeout=None
            ) as response:
                async for line in response.iter_lines():
                    print(line)

        tg.create_task(stream_messages_task())

        if hasattr(resource.with_streaming_response, "stream_data"):  # type: ignore
            async with resource.with_streaming_response.stream_data(  # type: ignore
                job_id=job_id, timeout=None
            ) as response:
                async for line in response.iter_lines():
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield line
