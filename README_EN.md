# Together Mod Charts Manager (TMCM)

[中文](README.md) | [한국어](README_KO.md)

> ADOFAI / Together Mod chart management tool – import, browse, play, edit, online lookup, batch export, all in one.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Together Mod Charts Manager (TMCM)** is a desktop chart management utility for the ADOFAI / Together Mod community, built with PyQt5 and featuring a dark Catppuccin theme.
It can batch import `.zip` chart packs, automatically parse `.adofai` metadata, and provide convenient browsing, searching, music playback, and info editing. It also directly queries the TUF database for online chart lookups. When exporting, your edits are written back into the `.adofai` files, making chart management effortless.

---

## Features

- Batch import: select a folder containing `.zip` chart packs, automatically extract and read all level info (song, author, artist, difficulty, BPM, etc.).
- Built-in player: uses `pygame` to play `.ogg` background music; supports play/pause/stop, progress seeking, and auto-stop when finished.
- Powerful search: filter across multiple columns (level name, song, author, artist, tags) with real-time highlighting.
- Info editing: select a single level to modify song name, charter, artist, difficulty (1-10), and description; table and detail panel update instantly.
- TUF online lookup: one-click search via TUF API to check if a chart exists in the database. Multi-creator fields are automatically split into independent search conditions for accuracy. For multiple results, a selection dialog shows PGU difficulty icons and level details, with a jump button to open in browser.
- Batch export: export selected levels to a target folder, with your edits automatically applied (safely written into the exported `.adofai` files).
- Dark theme: Catppuccin color scheme for comfortable long-term use.

---

## Screenshot
<img width="1920" height="1080" alt="screenshot" src="https://github.com/user-attachments/assets/3793549c-65b9-4547-8e8a-e804e6b59abd" />

---

## Quick Start

### Requirements
- Python 3.8 or higher
- pip

### Install dependencies
```bash
pip install PyQt5 pygame
```

### Run
```bash
python main.py
```
On first launch, an `adofai_viewer_cache` folder will be created in the program's directory as a temporary extraction path – no extra configuration needed.

---

## User Guide

### 1. Load Charts
1. Click the **Browse** button in the Path Configuration section and select a folder containing `.zip` chart files.
2. The program will automatically extract and parse all `.adofai` files; the table will display all level info once loading is complete.
3. You can cancel during loading; already loaded levels will remain in the list.

> **Tip**: If you are using Together Mod, its cached charts are located by default at:  
> `%AppData%\Local\Together\CachedCharts`

### 2. Browse & Search
- **Browse**: click any row; the Level Detail panel on the right will show full info (song, author, artist, BPM, difficulty, description, etc.).
- **Search**: type keywords in the search box, choose a search column from the dropdown (All, Level Name, Song, Author, Artist, Tags). Results are filtered instantly.

### 3. Music Playback
- Select a level that contains an `.ogg` music file; the playback bar at the bottom will activate.
- Click the **Play** button to start, then **Pause** or **Stop** at any time.
- Drag the progress bar to seek to any position.
- When playback finishes, it automatically returns to the "Play" state.

### 4. Edit Level Info
- **Single-select** a level in the table, then click the **Edit Info** button at the bottom.
- In the dialog, modify **Song Name, Charter, Artist, Difficulty, Description**.
- After confirming, the table row updates immediately, and a `*` appears in front of the level name to indicate it has been edited.
- The detail panel on the right refreshes accordingly.

### 5. TUF Online Lookup
- **Single-select** a level and click the purple **TUF Lookup** button.
- The program will search the TUF API using the level's song name, artist, and split creator list.
- **Not found**: a dialog appears with possible reasons (incomplete info, chart not on TUF).
- **Single match**: asks whether to open the TUF level page in your browser.
- **Multiple matches**: a selection window appears, each result displayed with a PGU difficulty icon, song, artist, creator, BPM, tile count, and difficulty name. Click the **Jump** button to open that level in your browser.

### 6. Batch Export
- Use `Ctrl` or `Shift` to multi-select levels.
- Click the **Export Selected** button, choose a target folder.
- Your edits are automatically applied during export (written directly into the `.adofai` files in the destination). Folder name format: `SongName-Charter-ZIPName`.

---

## Project Structure

```
.
├── main.py                        # Entry point
└── adofai_viewer/                 # Main package
    ├── __init__.py
    ├── constants.py               # Column definitions, Catppuccin dark theme styles
    ├── utils.py                   # Text processing, color tag conversion, filename sanitization
    ├── settings_parser.py         # .adofai parsing (supports non‑standard JSON & fallback regex)
    ├── level_info.py              # Level data model, edit logic, creator splitting
    ├── load_thread.py             # Background extraction & parsing thread
    ├── edit_dialog.py             # Edit level info dialog
    ├── tuf_searcher.py            # TUF API search, async request, multi‑result selection dialog
    └── main_window.py             # Main window UI & all business logic
```

---

## Technical Details

- **Audio playback**: since Qt5 does not natively support OGG, `pygame.mixer` is used with lazy initialization on first play to avoid startup delay.
- **TUF search**: creator strings like `Nephrolepis & 2seehyun` are automatically split into separate `creator:Nephrolepis, creator:2seehyun` conditions for accurate API matching.
- **Edit export**: edits are applied via regex replacement of JSON fields in `.adofai` (distinguishing strings and numbers), ensuring safety without breaking the file structure.
- **Cross‑platform**: all file operations use `os.path` and case‑insensitive fallback, enabling smooth running on Windows, macOS, and Linux.
- **Dark theme**: a complete QSS stylesheet based on the Catppuccin palette for a consistent and comfortable UI.

---

## FAQ

**Q: Why can’t I play music?**  
A: Ensure `pygame` is installed and the selected level contains an `.ogg` music file. If the file exists but still fails to load, check for special characters in the path or permission issues.

**Q: TUF lookup says “not found” but the chart is on TUF?**  
A: The local level info may be incomplete (missing artist or author). Try using the **Edit Info** function to fill in the actual data and then search again. Also check your internet connection.

**Q: Exported folder names have garbled text or underscores?**  
A: To maintain cross‑OS compatibility, the program converts special characters (like Chinese) to underscores. If you wish to keep original names, modify the `sanitize_filename` function in `utils.py`.

---

## Contributing

Issues and Pull Requests are welcome! Whether feature suggestions, bug reports, or code improvements, all contributions are appreciated.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is open-sourced under the MIT License. See the [LICENSE](LICENSE) file for details.
