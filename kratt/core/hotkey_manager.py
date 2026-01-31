"""
System-wide hotkey detection using pynput.
"""

from typing import Callable, Set
from pynput import keyboard


class HotkeyManager:
    """
    Listens for a specific combination of keys to trigger a callback.
    """

    def __init__(
        self, hotkey_set: Set[keyboard.Key], callback: Callable[[], None]
    ) -> None:
        self.hotkey_set = hotkey_set
        self.callback = callback
        self.current_keys: Set[keyboard.Key] = set()
        self.listener = None
        self._setup_listener()

    def _setup_listener(self) -> None:
        """Starts the background keyboard listener."""

        def on_press(key: keyboard.Key) -> None:
            self.current_keys.add(key)
            if all(k in self.current_keys for k in self.hotkey_set):
                self.callback()

        def on_release(key: keyboard.Key) -> None:
            try:
                self.current_keys.remove(key)
            except KeyError:
                pass

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def stop(self) -> None:
        """Stops the listener thread."""
        if self.listener:
            self.listener.stop()