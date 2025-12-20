# TimeMap ⏳🗺️

**TimeMap** is a terminal-based personal knowledge management tool that combines a **Calendar**, **Diary**, **Todo List**, **Quick Note**, **File Manager** and **Tags** into a single, cohesive TUI (Text User Interface).

It helps you map your life by linking files, notes, and tasks to specific dates, visualizing connections through tags, and exploring your data.

## Table of Contents

* [✨ Features](#-features)
* [Installation](#installation)
  * [Binary version (Recommended)](#binary-version-recommended)
  * [Python version](#python-version)
* [Terminal Commands](#terminal-commands)
* [TimeMap TUI](#timemap-tui)
* [Uninstall](#uninstall)

## ✨ Features

* **📅 Calendar TUI**: Navigate your history with `vim`-like keys (`h/j/k/l`).
* **📝 Diary & Mood Tracking**: Write daily entries with mood indicators (😊, 😐, 🌧️).
* **✅ Task Management**: Integrated Todo lists with progress tracking.
* **🔗 File Linking**: Link external files (PDFs, Images) to dates for easy retrieval.
* **🏷️ Tagging System**: Tag any item and filter by context.
<!-- * **🌌 Knowledge Constellation**: Visualize your tags and items as an interactive 3D star graph in your browser. -->
* **📊 Statistics**: View yearly trends for your productivity and moods.
<!-- * **📤 Import/Export**: Full backup support to Markdown/Folder structures (Hard/Soft copy). -->

## Installation
### Binary version (Recommended)


For **Archlinux** users, one can also install as AUR, via `yay`, `paru` etc. or manually install as AUR repository. The AUR page is at [https://aur.archlinux.org/packages/timemap-bin](https://aur.archlinux.org/packages/timemap-bin).

For other distributions of linux or macOS or windows, follow the instructions in next subsections.
#### Mac/Linux Users

1. Download the corresponding binary

**Method 1:**

**Linux:**

```bash
# linux
sudo curl -L https://github.com/srliu3264/timemap/releases/download/v1.0/timemap-linux -o /usr/local/bin/timemap
```

**Mac:**

```bash
# Mac
sudo curl -L https://github.com/srliu3264/timemap/releases/download/v1.0/timemap-macos`` -o /usr/local/bin/timemap
```

Here the link above is for `v1.0`, one should check the latest version.

**Method 2:**

One can go to [Release Page (https://github.com/srliu3264/timemap/releases)](https://github.com/srliu3264/timemap/releases),dowload the corresponding binary (called `timemap-linux` or `timemap-macos`).

Then rename the file as `timemap` and move it to `/usr/local/bin` (reaplce `~/Downloads/timemap-macos` with path to your downloaded file):

```bash 
sudo mv ~/Downloads/timemap-macos /usr/local/bin/timemap
```

2. Make it executable

```bash
sudo chmod +x /usr/local/bin/timemap
```

3. Run
```bash
timemap
```
to start the TUI.

#### Windows Users

1. Download `timemap-windows.exe`.
2. Place it in a folder (e.g., `C:\Program Files\TimeMap`).
3. Add that folder to your System `PATH` environment variable.
4. Open PowerShell/CMD and type timemap.

### Python version
#### Option 1: Install with `uv` (Recommended)

```bash
# Install globally as a tool
uv tool install git+[https://github.com/srliu3264/timemap.git](https://github.com/srliu3264/timemap.git)

# Run it!
timemap
```

#### Option2: Install via Pip

```bash
pip install git+[https://github.com/srliu3264/timemap.git](https://github.com/srliu3264/timemap.git)
```

## Terminal Commands
- `timemap --help` help menu.
- `timemap --default` config default apps to open/edit files.
- `timemap add <path-to-your-file>` link to a file to current date.
- `timemap addnote <content>` add a note for today.
- `timemap add2do <content>` add a to-do for today.
- `timemap emptytrash` empty trash bin.
- `timemap output --config` configure templates for output files.
- `timemap output` output notes and diaries.
- `timemap output --note` only output notes.
- `timemap output --diary` only output diary.

## TimeMap TUI

### How to use

Press `?` for a full list a hot key commands.

### Item type
There are four types of items:

1. `file`: link to file on your device. Press `o` to open with default app (configured by `timemap --default`) and `O` to open with selected app.
2. `diary`: consists of `title` + `mood` + `content`, exportable to markdown files with configurable front matter/template.
3. `note`: consists of `content`, exportable to markdown files with configurable template.
4. `to do list`: consists of `content` and `checkbox`. If content has links (`[things](link)`), then press `O` will open the link with default browser.

## Uninstall

You only need to 
- delete the `exe` or binary file or python program, 
- delete the configuration file,
- delete the database (be careful, you can not recover your diary or notes. You can `timemap --output` and backup first. Note that to-do-lists can not be exported.)

For example, for mac/linux users:

1. Uninstall the app

```bash
sudo rm /usr/local/bin/timemap
```

2. Remove configuration

```bash
rm -rf ~/.config/timemap
```

3. Remove Database (Your Diary/Notes/Todo). Be careful, this process is not reversible.

```bash
rm ~/.local/share/timemap.db
```



