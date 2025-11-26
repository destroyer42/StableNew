from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

from src.gui.gui_invoker import GuiInvoker

if TYPE_CHECKING:  # pragma: no cover
    from src.gui.prompt_workspace_state import PromptWorkspaceState

Listener = Callable[[], None]


@dataclass
class AppStateV2:
    """Central GUI-facing state container for the V2 application."""

    _listeners: Dict[str, List[Listener]] = field(default_factory=dict)
    _invoker: Optional[GuiInvoker] = None
    _notifications_enabled: bool = True

    prompt: str = ""
    negative_prompt: str = ""
    current_pack: Optional[str] = None
    is_running: bool = False
    status_text: str = "Idle"
    last_error: Optional[str] = None
    prompt_workspace_state: Optional["PromptWorkspaceState"] = None

    def set_invoker(self, invoker: GuiInvoker) -> None:
        """Set an invoker used to marshal notifications onto the GUI thread."""
        self._invoker = invoker

    def disable_notifications(self) -> None:
        """Stop delivering listener callbacks (used during teardown)."""
        self._notifications_enabled = False

    def subscribe(self, key: str, listener: Listener) -> None:
        listeners = self._listeners.setdefault(key, [])
        if listener not in listeners:
            listeners.append(listener)

    def _notify(self, key: str) -> None:
        if not self._notifications_enabled:
            return

        listeners = list(self._listeners.get(key, []))
        if not listeners:
            return

        # If no invoker is set (e.g., unit tests), invoke inline.
        if self._invoker is None:
            for listener in listeners:
                try:
                    listener()
                except Exception:
                    continue
            return

        for listener in listeners:
            try:
                self._invoker.invoke(listener)
            except Exception:
                continue

    def set_prompt(self, value: str) -> None:
        if self.prompt != value:
            self.prompt = value
            self._notify("prompt")

    def set_negative_prompt(self, value: str) -> None:
        if self.negative_prompt != value:
            self.negative_prompt = value
            self._notify("negative_prompt")

    def set_current_pack(self, value: Optional[str]) -> None:
        if self.current_pack != value:
            self.current_pack = value
            self._notify("current_pack")

    def set_running(self, value: bool) -> None:
        if self.is_running != value:
            self.is_running = value
            self._notify("is_running")

    def set_status_text(self, value: str) -> None:
        if self.status_text != value:
            self.status_text = value
            self._notify("status_text")

    def set_last_error(self, value: Optional[str]) -> None:
        if self.last_error != value:
            self.last_error = value
            self._notify("last_error")
