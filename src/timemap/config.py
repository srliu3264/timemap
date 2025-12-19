import os
import toml
import shutil

CONFIG_DIR = os.path.expanduser("~/.config/timemap")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")

DEFAULT_CONFIG = """
# TimeMap Configuration
# Uncomment lines to override system defaults

# editor = "nvim"

[defaults]
# pdf = "zathura"
# md = "nvim"
# txt = "nvim"
# html = "firefox"
# jpg = "feh"
"""


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
    return os.environ.get("EDITOR", "nvim")


def get_open_command(filepath: str):
    """Returns the configured command for a file extension, or 'xdg-open'."""
    config = load_config()
    defaults = config.get("defaults", {})

    ext = os.path.splitext(filepath)[1].lower().strip('.')

    # Check exact extension match
    if ext in defaults:
        return defaults[ext]

    return "xdg-open"


def edit_config():
    ensure_config()
    editor = os.environ.get("EDITOR", "vim")
    os.system(f"{editor} {CONFIG_PATH}")
