import os
import toml
import shutil
import platform
import subprocess
import sys

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

if IS_WINDOWS:
    CONFIG_DIR = os.path.join(os.environ.get(
        "APPDATA", os.path.expanduser("~")), "timemap")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/timemap")

CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")

if IS_WINDOWS:
    DEFAULT_EDITOR = "notepad"
    DEFAULT_OPENER = "start"
else:
    DEFAULT_EDITOR = "nvim" if shutil.which("nvim") else "vim"
    DEFAULT_OPENER = "open" if IS_MAC else "xdg-open"

DEFAULT_CONFIG = f"""
# TimeMap Configuration
# Uncomment lines to override system defaults

# editor = "{DEFAULT_EDITOR}"

[defaults]
# pdf = "zathura"
# md = "{DEFAULT_EDITOR}"
# txt = "{DEFAULT_EDITOR}"
# html = "firefox"
# jpg = "feh"
"""


def get_system_env():
    """
    Removes PyInstaller's library paths so external apps (nvim, sh) 
    don't crash with 'symbol lookup error'.
    """
    env = os.environ.copy()
    if 'LD_LIBRARY_PATH_ORIG' in env:
        env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
    elif 'LD_LIBRARY_PATH' in env and getattr(sys, 'frozen', False):
        del env['LD_LIBRARY_PATH']
    return env


def ensure_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            f.write(DEFAULT_CONFIG.strip())


def load_config():
    ensure_config()
    try:
        return toml.load(CONFIG_PATH)
    except Exception:
        return {}


def get_editor():
    """Returns the preferred editor from config ->env -> default."""
    config = load_config()
    if "editor" in config:
        return config["editor"]
    return os.environ.get("EDITOR", DEFAULT_EDITOR)


def get_open_command(filepath: str):
    """Returns the configured command for a file extension, or 'xdg-open'."""
    config = load_config()
    defaults = config.get("defaults", {})

    ext = os.path.splitext(filepath)[1].lower().strip('.')

    if ext in defaults:
        return defaults[ext]

    return DEFAULT_OPENER


def edit_config():
    ensure_config()
    editor = get_editor()
    try:
        subprocess.call(f"{editor} {CONFIG_PATH}",
                        shell=True, env=get_system_env())
    except Exception as e:
        print(f"Error opening editor: {e}")
