import asyncio
import json
import time

from src.streamer import stream_rl


async def test_consumer(queue: "asyncio.Queue") -> None:
    """Consumer de test qui lit la queue et affiche les events."""
    try:
        while True:
            obj = await queue.get()
            try:
                print("[QUEUE]", json.dumps(obj, ensure_ascii=False), flush=True)
            finally:
                queue.task_done()
    except asyncio.CancelledError:
        return


async def main() -> None:
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    producer = asyncio.create_task(stream_rl(queue, host="127.0.0.1", port=49123))
    consumer = asyncio.create_task(test_consumer(queue))

    try:
        await asyncio.gather(producer, consumer)
    except asyncio.CancelledError:
        producer.cancel()
        consumer.cancel()
        await asyncio.gather(producer, consumer, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping.")
