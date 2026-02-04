"""
System-wide hotkey detection using keyboard library.

Provides global hotkey detection across all applications on Linux/Fedora
without requiring window focus or elevated privileges.
"""
from pynput import keyboard as pynput_keyboard
from typing import Callable, Set, Optional
import keyboard


class HotkeyManager:
    """
    Manages system-wide hotkey detection and callback invocation.

    Uses the 'keyboard' library for global hotkey detection on Linux.

    Attributes:
        hotkey_set: Set of pynput Key objects representing the hotkey.
        callback: Function to invoke when the hotkey is pressed.
    """

    def __init__(
            self, hotkey_set: Set, callback: Callable[[], None]
    ) -> None:
        """
        Initialize the hotkey manager.

        Args:
            hotkey_set: Set of pynput Key objects (e.g., {Key.ctrl_l, Key.alt_r}).
            callback: Function to call when hotkey is triggered.
        """
        self.hotkey_set = hotkey_set
        self.callback = callback
        self._hotkey_id: Optional[int] = None
        self._setup()

    def _setup(self) -> None:
        """Register the global hotkey."""
        try:
            key_names = self._convert_keys_to_hotkey_string()
            self._hotkey_id = keyboard.add_hotkey(
                key_names,
                self._on_hotkey_pressed,
                suppress=False
            )
        except Exception as e:
            print(f"Hotkey registration failed: {e}")

    def _convert_keys_to_hotkey_string(self) -> str:
        """
        Convert pynput Key objects to keyboard library hotkey format.

        The keyboard library supports modifier keys: ctrl, alt, shift.

        Returns:
            A hotkey string in format "ctrl+alt+..." compatible with
            the keyboard library's add_hotkey() method.

        Raises:
            ValueError: If no valid keys can be mapped.
        """
        key_map = {
            pynput_keyboard.Key.ctrl_l: "ctrl",
            pynput_keyboard.Key.ctrl_r: "ctrl",
            pynput_keyboard.Key.alt_l: "alt",
            pynput_keyboard.Key.alt_r: "alt",
            pynput_keyboard.Key.shift_l: "shift",
            pynput_keyboard.Key.shift_r: "shift",
        }

        key_names = []
        for key in self.hotkey_set:
            name = key_map.get(key)
            if name and name not in key_names:
                key_names.append(name)

        if not key_names:
            raise ValueError("No valid keys found in hotkey set")

        return "+".join(sorted(key_names))

    def _on_hotkey_pressed(self) -> None:
        """Invoke the callback when hotkey is detected."""
        try:
            self.callback()
        except Exception:
            pass

    def stop(self) -> None:
        """Stop the hotkey listener and clean up resources."""
        try:
            if self._hotkey_id is not None:
                keyboard.remove_hotkey(self._hotkey_id)
        except Exception:
            pass