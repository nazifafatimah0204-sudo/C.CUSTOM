"""A small shared notebook the background worker writes to and the UI reads from."""
import threading
import time


class RunState:
    def __init__(self, n_agents: int):
        self.lock = threading.Lock()
        self.n_agents = n_agents
        self.current = 0          # index of the agent working right now
        self.outputs = {}         # agent index -> its finished output text
        self.events = []          # (time, message) activity log
        self.status = "Starting..."
        self.done = False
        self.error = None
        self.final = ""
        self.risk = None          # dict set by the risk-score tool
        self.started = time.time()

    def log(self, message: str):
        with self.lock:
            self.events.append((time.strftime("%H:%M:%S"), message))

    def set_status(self, text: str):
        with self.lock:
            self.status = text

    def finish_task(self, idx: int, text: str):
        with self.lock:
            self.outputs[idx] = text
            self.current = idx + 1
            self.events.append((time.strftime("%H:%M:%S"), f"Agent {idx + 1} finished its task"))

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "current": self.current,
                "outputs": dict(self.outputs),
                "events": list(self.events),
                "status": self.status,
                "done": self.done,
                "error": self.error,
                "final": self.final,
                "risk": self.risk,
                "elapsed": int(time.time() - self.started),
            }
