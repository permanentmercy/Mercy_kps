from pynput import keyboard
from core.events import events

class KeyListener:
    def __init__(self):
        self.listener = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
        self.is_running = True

    def stop(self):
        if not self.is_running:
            return
        if self.listener:
            self.listener.stop()
        self.is_running = False

    def on_press(self, key):
        key_str = self._get_key_str(key)
        if key_str:
            events.key_pressed.emit(key_str)

    def on_release(self, key):
        key_str = self._get_key_str(key)
        if key_str:
            events.key_released.emit(key_str)

    def _get_key_str(self, key):
        try:
            # 1. Handle keyboard.Key (special keys like ctrl, shift, space, etc.)
            if not hasattr(key, 'char') and hasattr(key, 'name'):
                return str(key.name).lower()
                
            # 2. Handle KeyCode where vk is present (using physical virtual key code)
            if hasattr(key, 'vk') and key.vk is not None:
                vk = key.vk
                if 65 <= vk <= 90:
                    return chr(vk).lower()
                if 48 <= vk <= 57:
                    return chr(vk)
                # Common OEM key codes on Windows
                vk_map = {
                    186: ";", 187: "=", 188: ",", 189: "-", 190: ".", 191: "/",
                    192: "`", 219: "[", 220: "\\", 221: "]", 222: "'"
                }
                if vk in vk_map:
                    return vk_map[vk]
                    
            # 3. Handle KeyCode via char as fallback
            if hasattr(key, 'char') and key.char is not None:
                # Handle control characters under Ctrl modifier (ASCII 1-31)
                if len(key.char) == 1:
                    val = ord(key.char)
                    if 1 <= val <= 26:
                        return chr(val + 96) # 'a' - 'z'
                    elif val == 27:
                        return "["
                    elif val == 28:
                        return "\\"
                    elif val == 29:
                        return "]"
                return str(key.char).lower()
                    
            return str(key).replace("'", "").lower()
        except Exception:
            return None
