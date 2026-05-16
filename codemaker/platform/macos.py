"""macOS keyboard hook using Quartz CGEventTap + CGEventPost.

Strategy:
    CGEventTap (intercept) ──► Process ──► CGEventPost (inject) ──► Apps

Works on all macOS versions with Accessibility permissions.
Requires: pyobjc-framework-Quartz, Accessibility access in System Settings.
"""

import atexit
import logging
import signal
import sys
from typing import Optional

from Quartz import (
    CGEventTapCreate,
    CGEventTapEnable,
    CGEventGetIntegerValueField,
    CGEventSetIntegerValueField,
    CGEventGetFlags,
    CGEventSetFlags,
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSourceCreate,
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFRunLoopStop,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionDefault,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGEventFlagsChanged,
    CGEventMaskBit,
    kCGKeyboardEventKeycode,
    kCGEventSourceUserData,
    kCGHIDEventTap,
    kCFRunLoopDefaultMode,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventSourceStateHIDSystemState,
    kCGEventSourceStatePrivate,
)

from .base import PlatformHook, KeyAction, KeyEventType, KeyCallback

logger = logging.getLogger("codemaker.platform.macos")

# ── macOS virtual keycodes (US-QWERTY layout) ──
# Char → (keycode, needs_shift) mapping
CHAR_TO_KEY: dict[str, tuple[int, bool]] = {}

# Letters
_LETTER_KEYCODES = {
    'a': 0x00, 'b': 0x0B, 'c': 0x08, 'd': 0x02, 'e': 0x0E,
    'f': 0x03, 'g': 0x05, 'h': 0x04, 'i': 0x22, 'j': 0x26,
    'k': 0x28, 'l': 0x25, 'm': 0x2E, 'n': 0x2D, 'o': 0x1F,
    'p': 0x23, 'q': 0x0C, 'r': 0x0F, 's': 0x01, 't': 0x11,
    'u': 0x20, 'v': 0x09, 'w': 0x0D, 'x': 0x07, 'y': 0x10,
    'z': 0x06,
}
for c, kc in _LETTER_KEYCODES.items():
    CHAR_TO_KEY[c] = (kc, False)
    CHAR_TO_KEY[c.upper()] = (kc, True)

# Digits
_DIGIT_KEYCODES = {
    '1': 0x12, '2': 0x13, '3': 0x14, '4': 0x15, '5': 0x17,
    '6': 0x16, '7': 0x1A, '8': 0x1C, '9': 0x19, '0': 0x1D,
}
for d, kc in _DIGIT_KEYCODES.items():
    CHAR_TO_KEY[d] = (kc, False)

# Symbols
_SYMBOLS = {
    '!': (0x12, True), '@': (0x13, True), '#': (0x14, True),
    '$': (0x15, True), '%': (0x17, True), '^': (0x16, True),
    '&': (0x1A, True), '*': (0x1C, True), '(': (0x19, True),
    ')': (0x1D, True), '-': (0x1B, False), '=': (0x18, False),
    '_': (0x1B, True), '+': (0x18, True),
    '[': (0x21, False), ']': (0x1E, False),
    '{': (0x21, True), '}': (0x1E, True),
    '\\': (0x2A, False), '|': (0x2A, True),
    ';': (0x29, False), ':': (0x29, True),
    "'": (0x27, False), '"': (0x27, True),
    ',': (0x2B, False), '<': (0x2B, True),
    '.': (0x2F, False), '>': (0x2F, True),
    '/': (0x2C, False), '?': (0x2C, True),
    '`': (0x32, False), '~': (0x32, True),
    ' ': (0x31, False), '\n': (0x24, False),
    '\t': (0x30, False),
}
CHAR_TO_KEY.update(_SYMBOLS)

# ── Keycode → name mapping for trigger detection ──
KEYCODE_TO_NAME: dict[int, str] = {
    0x30: "tab", 0x33: "backspace", 0x24: "enter",
    0x31: "space", 0x35: "escape",
    0x38: "shift", 0x3C: "shift",       # Left/Right Shift
    0x3B: "ctrl", 0x3E: "ctrl",          # Left/Right Control
    0x3A: "alt", 0x3D: "alt",            # Left/Right Option
    0x37: "meta", 0x36: "meta",          # Left/Right Command
    0x39: "capslock", 0x75: "delete",    # Caps Lock, Forward Delete
    0x7E: "up", 0x7D: "down", 0x7B: "left", 0x7C: "right",
    0x73: "home", 0x77: "end",
    0x74: "pageup", 0x79: "pagedown",
}
# Add letters
for c, kc in _LETTER_KEYCODES.items():
    KEYCODE_TO_NAME[kc] = c
# Add digits
for d, kc in _DIGIT_KEYCODES.items():
    KEYCODE_TO_NAME[kc] = d
# Add function keys (F1=0x7A, F2=0x78, F3=0x63, F4=0x76, ...)
_FKEY_KEYCODES = {
    1: 0x7A, 2: 0x78, 3: 0x63, 4: 0x76, 5: 0x60, 6: 0x61,
    7: 0x62, 8: 0x64, 9: 0x65, 10: 0x6D, 11: 0x67, 12: 0x6F,
}
for i, kc in _FKEY_KEYCODES.items():
    KEYCODE_TO_NAME[kc] = f"f{i}"

# Modifier keycode sets for flag-changed events
_MODIFIER_KEYCODES = {
    0x38, 0x3C,  # Shift
    0x3B, 0x3E,  # Control
    0x3A, 0x3D,  # Option/Alt
    0x37, 0x36,  # Command/Meta
    0x39,        # Caps Lock
}

# Marker value stamped into kCGEventSourceUserData on injected events
# so the tap callback can identify and pass through our own keystrokes
_INJECTED_MARKER = 0xC0DE_CAFE


class MacOSHook(PlatformHook):
    def __init__(self):
        self._callback: Optional[KeyCallback] = None
        self._tap = None
        self._run_loop_source = None
        self._run_loop = None
        self._running = False
        self._held_modifiers: set[str] = set()
        # Create a custom event source for injected events
        self._inject_source = CGEventSourceCreate(kCGEventSourceStatePrivate)

    def start(self, callback: KeyCallback) -> None:
        self._callback = callback

        # Create event tap to intercept keyboard events
        event_mask = (
            CGEventMaskBit(kCGEventKeyDown)
            | CGEventMaskBit(kCGEventKeyUp)
            | CGEventMaskBit(kCGEventFlagsChanged)
        )

        self._tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            event_mask,
            self._event_callback,
            None,
        )

        if self._tap is None:
            raise RuntimeError(
                "Failed to create CGEventTap. Ensure Accessibility access is "
                "enabled:\n"
                "  System Settings → Privacy & Security → Accessibility\n"
                "  Add your terminal app (e.g., Terminal.app, iTerm2) to the list."
            )

        self._run_loop_source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
        self._run_loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(
            self._run_loop, self._run_loop_source, kCFRunLoopDefaultMode
        )
        CGEventTapEnable(self._tap, True)

        logger.info("CGEventTap installed — keyboard interception active")
        atexit.register(self._cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self._running = True
        try:
            CFRunLoopRun()
        except Exception:
            logger.exception("Run loop crashed")
        finally:
            self._cleanup()

    def _event_callback(self, proxy, event_type, event, refcon):
        """CGEventTap callback — invoked for every keyboard event."""
        if not self._running:
            return event

        # Skip our own injected events (identified by userData marker)
        try:
            user_data = CGEventGetIntegerValueField(event, kCGEventSourceUserData)
            if user_data == _INJECTED_MARKER:
                return event
        except Exception:
            pass

        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)

        # Handle modifier-only events (kCGEventFlagsChanged)
        if event_type == kCGEventFlagsChanged:
            key_name = KEYCODE_TO_NAME.get(keycode, f"unknown_{keycode}")
            if keycode in _MODIFIER_KEYCODES:
                flags = CGEventGetFlags(event)
                self._update_modifiers_from_flags(flags)
            return event  # Always pass modifier events through

        # Map event type
        if event_type == kCGEventKeyDown:
            evt = KeyEventType.KEY_DOWN
        elif event_type == kCGEventKeyUp:
            evt = KeyEventType.KEY_UP
        else:
            return event

        key_name = KEYCODE_TO_NAME.get(keycode, f"unknown_{keycode}")

        action = self._callback(key_name, evt)

        if action == KeyAction.BLOCK:
            return None  # Returning None suppresses the key
        return event  # Pass through

    def _update_modifiers_from_flags(self, flags: int) -> None:
        """Update held modifiers based on current CGEvent flags."""
        self._held_modifiers = set()
        if flags & kCGEventFlagMaskShift:
            self._held_modifiers.add("shift")
        if flags & kCGEventFlagMaskControl:
            self._held_modifiers.add("ctrl")
        if flags & kCGEventFlagMaskAlternate:
            self._held_modifiers.add("alt")
        if flags & kCGEventFlagMaskCommand:
            self._held_modifiers.add("meta")

    def get_held_modifiers(self) -> frozenset[str]:
        return frozenset(self._held_modifiers)

    def _stamp_event(self, event) -> None:
        """Mark an event as ours so the tap callback passes it through."""
        CGEventSetIntegerValueField(event, kCGEventSourceUserData, _INJECTED_MARKER)

    def inject_char(self, char: str) -> None:
        mapping = CHAR_TO_KEY.get(char)
        if not mapping:
            logger.warning("No mapping for char: %r", char)
            return
        keycode, shift = mapping

        # Explicitly set flags on every event — CGEventCreateKeyboardEvent
        # inherits the current system modifier state, so without this,
        # letters come out uppercase if any stale shift/modifier is active.
        flags = kCGEventFlagMaskShift if shift else 0

        # Key down
        event_down = CGEventCreateKeyboardEvent(
            self._inject_source, keycode, True
        )
        self._stamp_event(event_down)
        CGEventSetFlags(event_down, flags)
        CGEventPost(kCGHIDEventTap, event_down)

        # Key up
        event_up = CGEventCreateKeyboardEvent(
            self._inject_source, keycode, False
        )
        self._stamp_event(event_up)
        CGEventSetFlags(event_up, flags)
        CGEventPost(kCGHIDEventTap, event_up)

    def inject_backspace(self) -> None:
        backspace_kc = 0x33  # macOS backspace keycode
        event_down = CGEventCreateKeyboardEvent(
            self._inject_source, backspace_kc, True
        )
        self._stamp_event(event_down)
        CGEventSetFlags(event_down, 0)
        CGEventPost(kCGHIDEventTap, event_down)

        event_up = CGEventCreateKeyboardEvent(
            self._inject_source, backspace_kc, False
        )
        self._stamp_event(event_up)
        CGEventSetFlags(event_up, 0)
        CGEventPost(kCGHIDEventTap, event_up)

    def stop(self) -> None:
        self._running = False
        if self._tap:
            CGEventTapEnable(self._tap, False)
        if self._run_loop:
            CFRunLoopStop(self._run_loop)

    def _cleanup(self) -> None:
        if self._tap:
            try:
                CGEventTapEnable(self._tap, False)
                logger.info("Event tap disabled")
            except Exception:
                pass
            self._tap = None

    def _signal_handler(self, signum, frame):
        logger.info("Signal %d, shutting down", signum)
        self.stop()
        self._cleanup()
        sys.exit(0)
