"""Run one connector as a child process: start it, watch it, restart it.

A connector that exits, fails to start, sends a fatal error, says nothing within
the hello timeout or stops answering pings is started again after a pause that
doubles from 1 s to 30 s while it keeps failing, and is back to 1 s after it ran
for 30 s from its hello without failing. A program that speaks another protocol
is stopped for good. Everything happens through QProcess signals, so the window
never waits.
"""

from __future__ import annotations

import sys
import time
from typing import Any

from PySide6.QtCore import QCoreApplication, QObject, QProcess, QTimer, Signal

from app import connector_protocol as cp

FIRST_PAUSE_MS = 1000
LONGEST_PAUSE_MS = 30_000
STEADY_MS = 30_000


def next_pause(previous_ms: int | None, ran_ms: int) -> int:
    """The pause before the next start, after a run of ran_ms that ended badly."""
    if previous_ms is None or ran_ms >= STEADY_MS:
        return FIRST_PAUSE_MS
    return min(previous_ms * 2, LONGEST_PAUSE_MS)


def _dispose(process: QProcess, kill_after_ms: int = 0) -> None:
    """Cut a process we are done with off our handlers, free it once it has ended.

    Freed only after it has finished: deleting a QProcess whose child still runs
    kills the child and makes its destructor wait, and this can run inside one of
    its own handlers. So it also leaves its host for the application, as the
    window may free a stopped host at once. A child still running after
    kill_after_ms is killed.
    """
    for signal in (
        process.readyReadStandardOutput,
        process.readyReadStandardError,
        process.finished,
        process.errorOccurred,
    ):
        signal.disconnect()
    if process.state() == QProcess.ProcessState.NotRunning:
        process.deleteLater()
        return
    process.setParent(QCoreApplication.instance())
    process.finished.connect(process.deleteLater)
    if kill_after_ms:
        QTimer.singleShot(kill_after_ms, process, process.kill)
    else:
        process.kill()


def builtin_command(name: str) -> list[str]:
    """How the chronometer runs one of its own connectors: itself, with --connector."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--connector", name]
    return [sys.executable, "-m", "app.main", "--connector", name]


class ConnectorHost(QObject):
    """One connector process for one source kind ("chips" or "beam")."""

    received = Signal(object)  # cp.Read, cp.Break, cp.Status or cp.Error
    state_changed = Signal(str)
    log = Signal(str)

    def __init__(
        self,
        kind: str,
        parent: QObject | None = None,
        *,
        hello_timeout_ms: int = 30_000,  # a onefile build unpacks itself first
        ping_ms: int = 5000,
        pong_timeout_ms: int = 15_000,
        grace_ms: int = 3000,
        pause_scale: float = 1.0,
    ) -> None:
        super().__init__(parent)
        self._kind = kind
        self._hello_timeout_ms = hello_timeout_ms
        self._pong_timeout_ms = pong_timeout_ms
        self._grace_ms = grace_ms
        self._pause_scale = pause_scale  # tests shrink the 1-30 s pauses
        self._program: list[str] = []
        self._settings: dict[str, Any] = {}
        self._process: QProcess | None = None
        self._buffer = b""
        self._overlong = False  # dropping a line too long to keep, up to its end
        self._wanted = False
        self._pause_ms: int | None = None
        self._hello_at: float | None = None  # a steady run counts from the hello
        self._ping_id = 0
        self._last_pong = 0.0
        self.state = "stopped"
        self._hello_timer = self._timer(self._on_hello_timeout, single=True)
        self._ping_timer = self._timer(self._on_ping)
        self._ping_timer.setInterval(ping_ms)
        self._restart_timer = self._timer(self._launch, single=True)

    def _timer(self, slot, single: bool = False) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(single)
        timer.timeout.connect(slot)
        return timer

    # -- control -------------------------------------------------------------

    def start(self, program: list[str], settings: dict[str, Any]) -> None:
        """Run program (a command line, split) and keep it running until stop()."""
        self.stop()
        self._program, self._settings = list(program), dict(settings)
        self._wanted, self._pause_ms = True, None
        self._launch()

    def stop(self, wait: bool = False) -> None:
        """Ask the connector to stop, close its input, kill it after the grace time."""
        self._wanted = False
        for timer in (self._hello_timer, self._ping_timer, self._restart_timer):
            timer.stop()
        self._drain()
        process, self._process = self._process, None
        if process is not None and process.state() != QProcess.ProcessState.NotRunning:
            process.write(cp.stop())
            process.closeWriteChannel()
            if wait:
                process.waitForFinished(self._grace_ms)
                _dispose(process)
            else:
                _dispose(process, kill_after_ms=self._grace_ms)
        elif process is not None:
            process.deleteLater()
        self._set_state("stopped")

    # -- the process ------------------------------------------------------------

    def _launch(self) -> None:
        if not self._wanted:
            return
        process = QProcess(self)
        process.readyReadStandardOutput.connect(lambda p=process: self._on_output(p))
        process.readyReadStandardError.connect(lambda p=process: self._on_stderr(p))
        process.finished.connect(lambda *_, p=process: self._on_ended(p, "exited"))
        process.errorOccurred.connect(lambda error, p=process: self._on_error(p, error))
        self._process, self._buffer, self._overlong = process, b"", False
        self._hello_at = None
        self._set_state("starting")
        self._hello_timer.start(self._hello_timeout_ms)
        process.start(self._program[0], self._program[1:])

    def _on_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._on_ended(process, "could not start")

    def _on_ended(self, process: QProcess, why: str) -> None:
        if process is not self._process or not self._wanted:
            return  # an old process, or one we stopped on purpose
        self._process = None
        _dispose(process)
        for timer in (self._hello_timer, self._ping_timer):
            timer.stop()
        ran_ms = (
            0
            if self._hello_at is None
            else round((time.monotonic() - self._hello_at) * 1000)
        )
        self._pause_ms = next_pause(self._pause_ms, ran_ms)
        pause = round(self._pause_ms * self._pause_scale)
        self.log.emit(
            f"connector {why}; starting it again in {self._pause_ms / 1000:g} s"
        )
        self._set_state(f"restarting in {self._pause_ms / 1000:g} s")
        self._restart_timer.start(pause)

    def _drain(self) -> None:
        """Handle what the connector already sent before it is cut off: a stop or a
        restart must not lose a read waiting in the pipe."""
        process = self._process
        if process is None:
            return
        if process.state() != QProcess.ProcessState.NotRunning:
            process.waitForReadyRead(0)
        self._on_output(process)

    def _kill_and_restart(self, why: str) -> None:
        self._drain()
        if self._process is not None:
            self._on_ended(self._process, why)

    def _on_hello_timeout(self) -> None:
        self._drain()  # a hello waiting in the pipe still counts
        if self.state == "starting":
            self._kill_and_restart("said no hello")

    def _silent(self) -> bool:
        return time.monotonic() - self._last_pong > self._pong_timeout_ms / 1000

    def _on_ping(self) -> None:
        if self._silent():
            self._drain()  # a pong waiting in the pipe still counts
            if self._silent():
                self._kill_and_restart("stopped answering")
                return
        self._ping_id += 1
        if self._process is not None:
            self._process.write(cp.ping(self._ping_id))

    def _on_stderr(self, process: QProcess) -> None:
        text = bytes(process.readAllStandardError().data()).decode("utf-8", "replace")
        for line in text.splitlines():
            if line.strip():
                self.log.emit(f"connector: {line.strip()[:200]}")

    def _on_output(self, process: QProcess) -> None:
        if self._process is None or process is not self._process:
            return
        self._buffer += bytes(process.readAllStandardOutput().data())
        *lines, self._buffer = self._buffer.split(b"\n")
        if self._overlong and lines:  # the end of a line already dropped
            lines.pop(0)
            self._overlong = False
        if len(self._buffer) > cp.MAX_LINE:  # never kept whole, however long it gets
            if not self._overlong:
                self.log.emit(
                    f"connector line ignored: longer than {cp.MAX_LINE} bytes"
                )
            self._buffer, self._overlong = b"", True
        gave_up = ""
        for line in lines:
            if line.strip() and self._process is process:
                gave_up = self._handle(cp.decode(line)) or gave_up
        if gave_up and self._process is process:  # after every line it sent with it
            self._kill_and_restart(f"gave up: {gave_up}")

    def _handle(self, message: cp.Event) -> str:
        """Act on one message; the reason a fatal error gives, else ""."""
        if isinstance(message, cp.Hello):
            self._on_hello(message)
        elif isinstance(message, cp.Pong):
            self._last_pong = time.monotonic()
        elif isinstance(message, cp.Ignored):
            self.log.emit(f"connector line ignored: {message.reason}")
        else:
            self.received.emit(message)
            if isinstance(message, cp.Error) and message.fatal:
                return message.message
        return ""

    def _on_hello(self, hello: cp.Hello) -> None:
        if not self._wanted:
            return  # read while stopping: it starts nothing any more
        self._hello_timer.stop()
        problem = (
            f"speaks protocol {hello.protocol}, not {cp.PROTOCOL}"
            if hello.protocol != cp.PROTOCOL
            else f"is a {hello.kind} connector, not {self._kind}"
            if hello.kind != self._kind
            else ""
        )
        if problem:
            # It would only fail again: stopped for good, and said why.
            self.log.emit(f"connector {hello.connector} {problem}")
            self.stop()
            self._set_state(f"failed: {problem}")
            return
        if self._process is None:
            return
        self._process.write(cp.start(self._settings))
        self._last_pong = self._hello_at = time.monotonic()
        self._ping_timer.start()
        self._set_state("running")

    def _set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self.state_changed.emit(state)
