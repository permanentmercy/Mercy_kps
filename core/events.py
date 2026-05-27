from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    # Keyboard events
    key_pressed = pyqtSignal(str)   # key_code
    key_released = pyqtSignal(str)  # key_code
    
    # Config events
    config_changed = pyqtSignal(dict)
    
    # Edit events
    edit_key_requested = pyqtSignal(str)  # key_id
    
events = EventBus()
