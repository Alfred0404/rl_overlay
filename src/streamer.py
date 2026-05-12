import asyncio
import json
import re
import os


async def stream_rl(
    queue: "asyncio.Queue",
    host: str = "127.0.0.1",
    port: int = 49123,
    recv_buf: int = 8192,
    test_mode: bool = False,
) -> None:
    """Connecte au flux TCP Rocket League, découpe les JSON collés et pousse les événements bruts dans une queue.

    Si test_mode=True, charge depuis data/test_event.json et broacast toutes les 0.5s.
    """
    if test_mode:
        print("TEST MODE: Broadcasting events from data/test_event.json", flush=True)
        test_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "test_event.json"
        )
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                test_event = json.load(f)
            while True:
                await queue.put(test_event)
                await asyncio.sleep(0.5)  # Broadcast toutes les 0.5s
        except FileNotFoundError:
            print(f"ERROR: Test event file not found: {test_file}", flush=True)
            return
        except Exception as e:
            print(f"ERROR in test mode: {e}", flush=True)
            return

    # Mode normal: connexion TCP réelle
    reconnect_delay = 1.0
    boundary_re = re.compile(r"\}\s*\{")
    rl_buffer = ""

    while True:
        reader = None
        writer = None

        try:
            print(f"Connecting to {host}:{port}...", flush=True)
            reader, writer = await asyncio.open_connection(host, port)
            print("Connected to RL stats TCP server.", flush=True)
            reconnect_delay = 1.0

            while True:
                data = await reader.read(recv_buf)
                if not data:
                    print("Connection closed by remote.", flush=True)
                    break

                rl_buffer += data.decode(errors="replace")
                rl_buffer = boundary_re.sub("}\n{", rl_buffer)
                parts = rl_buffer.split("\n")
                rl_buffer = parts.pop()

                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        await queue.put(json.loads(part))
                    except json.JSONDecodeError:
                        continue

        except (ConnectionRefusedError, OSError) as exc:
            print(f"Connection error: {exc}", flush=True)
        finally:
            if writer is not None:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

        print(f"Reconnecting in {reconnect_delay}s...", flush=True)
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 1.5, 30)
