# TimeMap ⏳🗺️

**TimeMap** is a terminal-based personal knowledge management tool that combines a **Calendar**, **Diary**, **Todo List**, **Quick Note**, **File Manager** and **Tags** into a single, cohesive TUI (Text User Interface).

It helps you map your life by linking files, notes, and tasks to specific dates, visualizing connections through tags, and exploring your data.


## ✨ Features

* **📅 Calendar TUI**: Navigate your history with `vim`-like keys (`h/j/k/l`).
* **📝 Diary & Mood Tracking**: Write daily entries with mood indicators (😊, 😐, 🌧️).
* **✅ Task Management**: Integrated Todo lists with progress tracking.
* **🔗 File Linking**: Link external files (PDFs, Images) to dates for easy retrieval.
* **🏷️ Tagging System**: Tag any item and filter by context.
<!-- * **🌌 Knowledge Constellation**: Visualize your tags and items as an interactive 3D star graph in your browser. -->
* **📊 Statistics**: View yearly trends for your productivity and moods.
<!-- * **📤 Import/Export**: Full backup support to Markdown/Folder structures (Hard/Soft copy). -->

## 🚀 Installation

### Option 1: Install with `uv` (Recommended)

```bash
# Install globally as a tool
uv tool install git+[https://github.com/srliu3264/timemap.git]([https://github.com/yourusername/timemap.git])

# Run it!
timemap
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
