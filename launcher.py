"""

Chainlit System Tray Launcher (Windows)

This script implements a lightweight Windows system tray launcher for a
Chainlit application. It is designed to run the Chainlit server headlessly,
expose a simple tray-based UI, and ensure that only a single instance of the
launcher is active at any given time.

This script is compiled into an executable ─ launcher.exe using the command:

    pyinstaller --onefile --noconsole --icon=templates\chainlit.ico launcher.py

"""

import subprocess
import threading
import webbrowser
import signal
import sys
import ctypes
from pystray import Icon, Menu, MenuItem
from PIL import Image

CHAINLIT_CMD = ["chainlit", "run", "app.py", "--headless"]
APP_URL = "http://localhost:8080"
ICON_PATH = "templates/chainlit.ico"
MUTEX_NAME = "Global\\ChainlitPersonaLauncher"

process = None


# ---------------- SINGLE INSTANCE CHECK ----------------

def already_running():
    mutex = ctypes.windll.kernel32.CreateMutexW(
        None, False, MUTEX_NAME
    )
    ERROR_ALREADY_EXISTS = 183

    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return True
    return False


# ---------------- CHAINLIT PROCESS ----------------

def start_chainlit():
    global process
    process = subprocess.Popen(
        CHAINLIT_CMD,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    process.wait()


# ---------------- TRAY ACTIONS ----------------

def open_browser():
    webbrowser.open(APP_URL)


def exit_app(icon):
    global process
    icon.stop()

    if process and process.poll() is None:
        process.send_signal(signal.CTRL_BREAK_EVENT)
        process.terminate()

    sys.exit(0)


def on_activate(icon):
    open_browser(icon)


# ---------------- MAIN ----------------

def main():
    # 🔒 Single-instance logic
    if already_running():
        open_browser()
        sys.exit(0)

    # Start Chainlit in background
    threading.Thread(target=start_chainlit, daemon=True).start()

    # Open browser on first launch
    webbrowser.open(APP_URL)

    image = Image.open(ICON_PATH)
    menu = Menu(
        MenuItem("Open", open_browser, default=True),
        MenuItem("Exit", exit_app)
    )

    icon = Icon(
        "Chainlit Launcher",
        image,
        "Chainlit App",
        menu=menu,
        on_activate=on_activate
    )

    icon.run()


if __name__ == "__main__":
    main()
