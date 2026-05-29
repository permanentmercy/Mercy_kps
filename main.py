import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTranslator, QLibraryInfo
from core.key_listener import KeyListener
from windows.display_window import DisplayWindow
from windows.control_window import ControlWindow
from core.i18n import Trans

def main():
    import traceback
    def excepthook(exc_type, exc_value, exc_tb):
        with open("crash.txt", "w") as f:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = excepthook

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Set AppUserModelID so Windows taskbar displays the custom window icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mercy.kps_plus.editor.v1")
        except Exception:
            pass

    # Create and set application icon (black background, white "M")
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(QColor(255, 255, 255))
    font = painter.font()
    font.setFamily("Century Gothic")
    font.setBold(True)
    font.setPointSize(24)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "M")
    painter.end()
    app_icon = QIcon(pixmap)
    app.setWindowIcon(app_icon)

    # Enable high DPI scaling
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Load stylesheet
    style_path = Path("assets/styles/dark_theme.qss")
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding='utf-8'))

    # Initialize key listener
    listener = KeyListener()
    listener.start()
    
    # Initialize windows and configuration
    from core.config_manager import ConfigManager
    config = ConfigManager.load()
    associated_enabled = config.get("associated_startup_enabled", False)
    associated_paths = config.get("associated_app_paths", [])
    if not associated_paths and config.get("associated_app_path"):
        associated_paths = [config.get("associated_app_path")]

    display_win = DisplayWindow()
    control_win = ControlWindow(display_win, listener)
    
    # System Tray Icon Setup
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
    
    tray_icon = QSystemTrayIcon(app.windowIcon(), app)
    tray_menu = QMenu()
    
    action_show_gui = tray_menu.addAction(Trans.t("tray_open_settings", "打开设置 (Open Settings)"))
    action_show_gui.triggered.connect(lambda: (control_win.show(), control_win.raise_(), control_win.activateWindow()))
    
    action_exit = tray_menu.addAction(Trans.t("tray_exit", "退出 (Exit)"))
    def on_exit():
        control_win._force_close = True
        display_win.close()
        control_win.close()
        # Stop audio capture and release resources if started
        try:
            from core.audio_capture import AudioCapture
            if AudioCapture._instance is not None:
                AudioCapture._instance.stop()
            AudioCapture.terminate_global_pa()
        except Exception:
            pass
        app.quit()
    action_exit.triggered.connect(on_exit)

    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.activated.connect(lambda reason: (
        control_win.show(), control_win.raise_(), control_win.activateWindow()
    ) if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    tray_icon.show()

    control_win.action_show_gui = action_show_gui
    control_win.action_exit = action_exit
    
    is_silent = "--silent" in sys.argv

    if associated_enabled and associated_paths:
        # Setup background process monitor
        from PyQt6.QtCore import QTimer
        from core.startup_helper import is_process_running
        import os
        
        process_names = [os.path.basename(p) for p in associated_paths if p]
        timer = QTimer()
        state = {"was_running": False}
        
        def monitor_process():
            # If the editor window is visible, we should show the keys regardless of whether the game is running,
            # so the user can edit the layout and see the changes.
            if control_win.isVisible():
                if not display_win.isVisible():
                    display_win.show()
                    display_win.raise_()
                return

            running = any(is_process_running(name) for name in process_names)
            if running:
                if not display_win.isVisible():
                    display_win.show()
                display_win.raise_()
                state["was_running"] = True
            else:
                if display_win.isVisible():
                    display_win.hide()
                state["was_running"] = False
        
        # Run once immediately to avoid initial delay
        monitor_process()
        
        timer.timeout.connect(monitor_process)
        timer.start(1000) # Check every 1 second
        app._monitor_timer = timer

    if associated_enabled and associated_paths:
        control_win.hide()
        display_win.hide()
        if not is_silent:
            tray_icon.showMessage(
                Trans.t("tray_running_title", "MercyKPS 关联启动"),
                Trans.t("tray_running_desc", "程序已在后台运行以监测关联应用。双击托盘图标可打开设置界面。"),
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
    else:
        display_win.show()
        control_win.show()
    
    import traceback
    try:
        exit_code = app.exec()
        listener.stop()
        ConfigManager.save()
        sys.exit(exit_code)
    except Exception as e:
        with open("crash.txt", "w") as f:
            traceback.print_exc(file=f)
        raise e

if __name__ == "__main__":
    main()
