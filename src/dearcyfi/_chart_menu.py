"""DearCyGui snapshot dialog; workers never read or write GUI objects."""

import logging
import os
from _thread import LockType
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

import dearcygui as dcg

from ._chart_document import ChartPersistenceError, read_document, write_document
from ._chart_state import capture_chart, restore_validated_chart

log = logging.getLogger(__name__)
_file_workers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dearcyfi-snapshot")


class _Cancelled(Exception):
    pass


@dataclass
class _Request:
    path: Path
    overwrite: bool = False
    _lock: LockType = field(default_factory=Lock)
    _cancelled: bool = False
    _committing: bool = False

    def publish(self, action):
        with self._lock:
            if self._cancelled:
                raise _Cancelled
            self._committing = True
        action()

    def cancel(self) -> bool:
        with self._lock:
            if self._committing:
                return False
            self._cancelled = True
            return True


def _save_file(request, document):
    if not request.overwrite and os.path.lexists(request.path):
        raise FileExistsError(str(request.path))
    write_document(request.path, document, overwrite=request.overwrite, publish=request.publish)


class ChartFileMenu:
    def __init__(self, chart):
        self.chart = chart
        self.window = None
        self.request = None
        self.confirm_path = None

    def show(self, *, save: bool) -> None:
        if self.window is not None:
            self.window.focus()
            return
        self.save = save
        self.action_label = "Save Chart" if save else "Open Chart"
        context = self.chart.context
        with dcg.Window(
            context, parent=context.viewport, label=self.action_label, modal=True,
            has_close_button=False, width=480, autosize=True,
        ) as self.window:
            dcg.Text(context, value="Enter a local snapshot path.")
            self.path_input = dcg.InputText(context, width="fillx", hint="Path to chart.json")
            self.status = dcg.Text(context, value="", wrap=450)
            self.action = dcg.Button(context, label=self.action_label, callback=self._submit)
            self.cancel = dcg.Button(context, label="Cancel", callback=self._cancel)
        context.viewport.wake(full_refresh=True)

    def _submit(self) -> None:
        if self.window is None or self.request is not None:
            return
        confirmed = self.confirm_path is not None
        if confirmed:
            target = self.confirm_path
        else:
            value = self.path_input.value.strip()
            if not value:
                self._error("Enter a path to the snapshot file.")
                return
            try:
                target = Path(os.path.abspath(Path(value).expanduser()))
                if self.save and not target.suffix:
                    target = target.with_suffix(".json")
            except (OSError, ValueError, RuntimeError) as exc:
                self._error(f"Invalid path: {exc}")
                return
            if not self.save:
                self._confirm(target, "Replace this chart?", "Replace Chart")
                return
        request = _Request(target, overwrite=self.save and confirmed)
        self.request = request
        self.action.enabled = False
        self.path_input.enabled = False
        self.status.value = f"{'Saving' if self.save else 'Reading'} {target}..."
        queue = self.chart.context.queue
        try:
            if self.save:
                document = capture_chart(self.chart, validate=False)
                future = _file_workers.submit(_save_file, request, document)
            else:
                future = _file_workers.submit(read_document, target)
        except Exception as exc:
            self._failed(exc)
            return
        future.add_done_callback(lambda result: queue.submit(self._finish, request, result))
        self.chart.context.viewport.wake(full_refresh=True)

    def _finish(self, request, result) -> None:
        if self.window is None or self.request is not request:
            return
        try:
            document = result.result()
            if not self.save:
                restore_validated_chart(self.chart, document, publish=request.publish)
        except FileExistsError as exc:
            if self.save and not request.overwrite:
                self.request = None
                self._confirm(request.path, "Overwrite the existing file?", "Overwrite")
            else:
                self._failed(exc)
            return
        except _Cancelled:
            return
        except Exception as exc:
            self._failed(exc)
            return
        self._dismiss()
        self.chart._set_status(f"{'Saved' if self.save else 'Opened'} chart: {request.path}")

    def _confirm(self, target, question, action):
        self.confirm_path = target
        self.path_input.enabled = False
        self.action.enabled = True
        self.action.label = action
        self.status.value = f"{question}\n{target}"
        self.chart.context.viewport.wake(full_refresh=True)

    def _failed(self, exc):
        if not isinstance(exc, (ChartPersistenceError, OSError, ValueError)):
            log.error("Chart snapshot operation failed", exc_info=exc)
        self.request = None
        self.confirm_path = None
        self.path_input.enabled = True
        self.action.enabled = True
        self.action.label = self.action_label
        self._error(f"Could not {'save' if self.save else 'open'} chart: {exc}")

    def _error(self, message):
        self.status.value = message
        self.chart.context.viewport.wake(full_refresh=True)
        self.chart._set_status(message)

    def _cancel(self) -> None:
        if self.window is None:
            return
        if self.request is not None and not self.request.cancel():
            self.status.value = "Finishing the chart operation..."
            self.chart.context.viewport.wake(full_refresh=True)
            return
        self._dismiss()
        self.chart._set_status(f"{self.action_label} canceled.")

    def _dismiss(self):
        self.window.delete_item()
        self.window = self.request = self.confirm_path = None
        self.path_input = self.status = self.action = self.cancel = None
        self.chart.context.viewport.wake(full_refresh=True)
