"""
Background task handler for non-blocking operations
"""
import threading
from queue import Queue
from typing import Callable, Optional
from .models import ExportProgress


class TaskRunner:
    """Handles background tasks with progress reporting"""

    def __init__(self):
        """Initialize task runner"""
        self.current_task: Optional[threading.Thread] = None
        self.progress_queue: Queue = Queue()
        self.cancel_flag = threading.Event()

    def is_running(self) -> bool:
        """Check if a task is currently running"""
        return self.current_task is not None and self.current_task.is_alive()

    def cancel(self):
        """Request cancellation of current task"""
        self.cancel_flag.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested"""
        return self.cancel_flag.is_set()

    def run_task(self, task_func: Callable, *args, **kwargs):
        """
        Run a task in background thread

        Args:
            task_func: Function to execute
            *args, **kwargs: Arguments to pass to function
        """
        if self.is_running():
            raise RuntimeError("A task is already running")

        self.cancel_flag.clear()
        self.current_task = threading.Thread(
            target=task_func,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        self.current_task.start()

    def report_progress(self, progress: ExportProgress):
        """Report progress from background task"""
        self.progress_queue.put(progress)

    def get_progress(self) -> Optional[ExportProgress]:
        """Get latest progress update (non-blocking)"""
        if not self.progress_queue.empty():
            return self.progress_queue.get_nowait()
        return None
