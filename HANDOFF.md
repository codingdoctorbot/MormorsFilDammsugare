# 🔁 HANDOFF — MormorsFilDammsugare

> **Read this first** (developers and AI coding agents alike). Then consult **`docs/SESSIONS.md`** (chronological work log), **`TODO.md`** (desktop testing and roadmap items), **`CHANGELOG.md`** (version history), and **`ATTRIBUTIONS.md`** (upstream algorithms).
>
> **At the end of every work session**: update this file's *Current Status*, update `TODO.md`, record a summary in `docs/SESSIONS.md`, and log visible changes in `CHANGELOG.md`.

---

## 🧭 What This Application Is

**MormorsFilDammsugare** ("*Grandma's File Vacuum Cleaner*") is a unified, native Linux / SteamOS backup triage and filesystem vacuum suite built in Python 3.14 + PyQt6.

It consolidates four previously separate tools into a single, cohesive application with both a rich desktop GUI (KDE Plasma 6 native) and a headless terminal CLI:
1. **Module 0 — Survey & Sampler**: Ultra-fast folder dump probe; magic-byte sniffer, size histograms, and duplicate waste estimation.
2. **Module 1 — Photo & Video Sorter**: Extracts media, deduplicates by streaming SHA-256, and sorts into `Continent / Country / Year` using offline polygon raycasting (`countries.gz`).
3. **Module 2 — Document Devourer**: Ingests PDFs, Office docs, e-books, and emails, categorizing by semantic topics (`Economy`, `Legal`, `Career`, `Work`, `Manuals`).
4. **Module 3 — Privacy & Loaner Audit**: Offline YOLOv8 AI model running locally on CPU via ONNX Runtime to audit explicit/sensitive media before lending a PC. Includes an isolated quarantine Vault.
5. **Module 4 — Czkawka Cleaner Toolkit**: High-speed exact duplicate finder (3-stage filter), 128-bit perceptual image similarity, bottom-up empty folder pruner, space hogs inspector, and mismatched extension fixer.

---

## 🏛️ Project Directory Structure

```
MormorsFilDammsugare/
├── mormor                             # Main executable bash entrypoint (auto-venv + PYTHONPATH)
├── install-desktop-menu.sh            # KDE Plasma desktop menu & hicolor icon installer
├── icon.png                           # 256x256 application icon
├── mormorsfildammsugare/              # Core Python package
│   ├── __init__.py
│   ├── cli.py                         # Rich terminal CLI interface (argparse + rich tables)
│   ├── catalog/                       # SQLite WAL database for runs, media, source tracking
│   │   ├── __init__.py
│   │   └── db.py
│   ├── cleaner/                       # Module 4: Czkawka cleaner algorithms
│   │   ├── __init__.py
│   │   ├── bad_extensions.py          # Sniff binary magic bytes vs declared extensions
│   │   ├── duplicates.py              # 3-stage duplicate finder (Size -> 64KB Probe -> SHA-256)
│   │   ├── empty_dirs.py              # Bottom-up empty directory pruner
│   │   ├── perceptual.py              # 128-bit perceptual hash (dHash + aHash)
│   │   └── space_hogs.py              # Top-N file size scanner
│   ├── core/                          # Fundamental filesystem utilities
│   │   ├── __init__.py
│   │   ├── hasher.py                  # Full SHA-256 streaming & 64KB head/tail fingerprinting
│   │   ├── sniffer.py                 # Magic byte sniffing for images, video, docs, archives
│   │   └── walker.py                  # High-speed directory scanner (skips .git, AppData, etc.)
│   ├── documents/                     # Module 2: Document parsing & categorization
│   │   ├── __init__.py
│   │   ├── categories.py              # Semantic category keywords (Economy, Legal, Career, Work)
│   │   ├── dates.py                   # Date parser waterfall (metadata, filename, folder)
│   │   └── metadata.py                # Parsers for PDF, DOCX, XLSX, EML
│   ├── geo/                           # Module 1: Offline GIS geocoding
│   │   ├── __init__.py
│   │   ├── countries.gz               # PSGEO3 binary polygon spatial index
│   │   └── locator.py                 # Raycasting point-in-polygon engine (resolves Swedish län)
│   ├── gui/                           # Desktop GUI application
│   │   ├── __init__.py
│   │   ├── app.py                     # PyQt6 QMainWindow with 6 tab views & worker threads
│   │   ├── theme.py                   # KDE Plasma 6 Breeze theme & kdeglobals palette engine
│   │   └── assets/                    # Application icons (.png, .svg)
│   ├── media/                         # Module 1: Media metadata extractors
│   │   ├── __init__.py
│   │   └── metadata.py                # EXIF dates & GPS, QuickTime mvhd/moov & ISO 6709 parsing
│   ├── modules/                       # High-level engine orchestrators
│   │   ├── __init__.py
│   │   ├── document_devourer.py
│   │   ├── photo_sorter.py
│   │   ├── privacy_scanner.py
│   │   └── sampler.py
│   └── privacy/                       # Module 3: AI model & quarantine vault
│       ├── __init__.py
│       ├── detector.py                # YOLOv8 ONNX inference, letterboxing, NMS
│       ├── vault.py                   # Quarantine manager ({id}.bin + {id}.json metadata)
│       └── models/                    # Bundled ONNX models (320n.onnx, 640m.onnx)
├── docs/
│   └── SESSIONS.md                    # Detailed chronological work log
├── ATTRIBUTIONS.md                    # Upstream project and algorithmic attributions
├── CHANGELOG.md                       # Release notes and version history
├── HANDOFF.md                         # This document
├── README.md                          # Public documentation and usage guide
└── TODO.md                            # Testing checklist & roadmap
```

---

## 🔒 Core Invariants & Safety Guarantees

When modifying or extending the codebase, the following safety invariants **must never be violated**:

1. **Source File Immutability**:
   * Source files are **never modified in-place**.
   * By default, all operations **copy** files rather than move them.
2. **Move Mode Verification**:
   * In `--move` mode, an original file is **only** removed from its source location after the destination copy has been verified by comparing byte sizes and SHA-256 hashes.
   * If a copy fails or the destination is on a different filesystem that truncates writes, the original source is left intact.
3. **Safe Waste Disposal**:
   * Duplicate cleaning and file deletions **must route through `send2trash`** (FreeDesktop Trash specification) by default so that operations can be inspected or reversed in KDE Dolphin. Hard deletion (`unlink`) is only permitted when the user explicitly supplies `--permanent`.
4. **Isolated Quarantine**:
   * Quarantined privacy files in the Vault are renamed to encrypted UUIDs (`{id}.bin`) with metadata in `{id}.json`. Source paths are securely wiped so standard gallery scanners cannot discover them, but the user can restore them with 1 click.
5. **Zero Windows / Microsoft Runtime Baggage**:
   * Do not introduce dependencies on .NET, Mono, Wine, or Windows-specific COM/Win32 APIs. The application runs purely native on Linux / SteamOS.

---

## 🛠️ Developer Setup & Commands

### Virtual Environment
The repository contains a self-contained virtualenv at `.venv/` running Python 3.14.6:
```bash
cd /home/deck/developer/MormorsFilDammsugare

# Activate environment
source .venv/bin/activate

# Install development packages if needed
pip install pytest
```

### Running the Application
The `mormor` bash runner automatically ensures `.venv` Python is used and sets `PYTHONPATH`:
```bash
# Launch Desktop GUI
./mormor gui

# Run CLI Survey
./mormor survey /path/to/folder

# Clean exact duplicates (dry run)
./mormor clean-dupes /path/to/folder

# Clean exact duplicates (send to Trash, keep cleanest name)
./mormor clean-dupes /path/to/folder --winner cleanest --trash
```

### KDE Plasma Desktop Integration
To register or update the desktop icon and application launcher in KDE Plasma:
```bash
./install-desktop-menu.sh
```

---

## 🎨 KDE Theme & Styling Guidelines

The GUI uses `mormorsfildammsugare/gui/theme.py` to achieve seamless integration with KDE Plasma:
* It reads `~/.config/kdeglobals` to extract the user's active color scheme (Breeze Dark, Breeze Light, or custom themes).
* Avoid hardcoding static background colors (e.g. `#1e1e2e`) in child widgets. Use palette roles (`QPalette.ColorRole.Window`, `Base`, `Button`, `Highlight`) or subtle border colors generated by `KDETheme`.
* UI operations that scan or hash large files **must always run on a `QThread` worker** (such as `SurveyWorker`, `PhotoWorker`, `DocWorker`, `PrivacyWorker`) so the Qt main event loop remains silky smooth.
