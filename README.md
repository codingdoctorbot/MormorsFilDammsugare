<p align="center">
  <img src="icon.png" width="128" height="128" alt="MormorsFilDammsugare Icon"><br>
  <b>MormorsFilDammsugare</b><br>
  <i>The Ultimate Native Linux Backup Triage & File Vacuum Suite.</i><br>
  <sub>🇸🇪 <i>mormor</i> = grandma · <i>fil</i> = file · <i>dammsugare</i> = vacuum cleaner</sub>
</p>

<p align="center">
  <a href="#-the-5-pillars">5 Pillars</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-command-line-reference">CLI Reference</a> •
  <a href="#-developer-guide">Developer Guide</a> •
  <a href="HANDOFF.md">Handoff</a> •
  <a href="CHANGELOG.md">Changelog</a> •
  <a href="ATTRIBUTIONS.md">Attributions</a>
</p>

---

A single, unified, lightweight Linux/SteamOS utility uniting **Mormorskopiadammsugare**, **Arkivslukaren**, **Offline NSFW Scanner**, a built-in **Filedump Sampler**, and the best algorithms from **Czkawka** (Exact Duplicates, Similar Photos, Empty Folders, Space Hogs, Bad Extensions).

Built in Python 3.14 + PyQt6 with a dual-mode interface (rich GUI + headless CLI). **100% free of Windows/Microsoft runtimes.**

---

## 🌟 The 5 Pillars

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                MormorsFilDammsugare                                    │
├───────────────┬───────────────────┬───────────────────┬────────────────┬───────────────┤
│  📊 0. Survey │    📷 1. Photos   │   📄 2. Docs      │  🛡️ 3. Privacy │  🧹 4. Cleaner│
│  (The Sampler │  (Continent/Year  │  (Format/Category │ (YOLOv8 Local  │  (Czkawka     │
│   Inspector)  │   Deduplication)  │   Deduplication)  │  Media Audit)  │   Toolkit)    │
└───────────────┴───────────────────┴───────────────────┴────────────────┴───────────────┘
```

1. **📊 Module 0 — Filedump Sampler & Survey (`mormor survey`)**:
   * Scans unknown folders/drives in milliseconds.
   * Sniffs binary magic bytes without trusting extensions.
   * Reveals file size distributions and duplicate waste before touching any files.
2. **📷 Module 1 — Photo & Video Sorter (`mormor photos`)**:
   * Extracts unique photos and videos, deduplicates via SHA-256 stream hashing.
   * Resolves EXIF/QuickTime GPS offline to `Continent / Country / Year` (with Swedish *län* support).
   * Safe move mode with 1-click transactional undo (`mormor restore-photos`).
3. **📄 Module 2 — Document Devourer (`mormor docs`)**:
   * Sifts through backup piles for PDFs, Office docs, e-books, and emails.
   * Categorizes by semantic topics (`Economy & Finance`, `Agreements & Legal`, `Personal & Career`, `Work & Projects`, `Manuals & Documentation`) and parent folder hints.
   * Deduplicates and sorts into `Format / Year / Category`.
4. **🛡️ Module 3 — Privacy & Loaner Audit (`mormor audit`)**:
   * Offline YOLOv8 AI model running locally on your CPU hardware via ONNX Runtime.
   * Audits pictures and videos for explicit content before lending your PC.
   * Quarantines sensitive files into an isolated Vault (`mormor vault`).
5. **🧹 Module 4 — Czkawka Cleaner Toolkit (`mormor clean-dupes`, `similar-images`, etc.)**:
   * **Exact Duplicates**: 3-stage high-speed duplicate finder (Size $\rightarrow$ Head/Tail probe $\rightarrow$ Full SHA-256) with smart winner selection (`cleanest`, `oldest`, `newest`) and safe trash deletion.
   * **Similar Images**: 128-bit perceptual hashing (dHash + aHash) to find compressed, resized, cropped, or burst photos.
   * **Empty Folders**: Discovers and prunes empty directory trees bottom-up.
   * **Space Hogs**: Identifies top largest files consuming disk space.
   * **Bad Extensions**: Detects and fixes files with wrong extensions (e.g. `.CHK` $\rightarrow$ `.mp4`).

---

## 🚀 Quick Start

### 1. Launch Desktop GUI (KDE Plasma on SteamOS)
```bash
./mormor gui
```
The desktop GUI automatically detects and matches your KDE Plasma theme (`~/.config/kdeglobals`), honoring Breeze Dark / Breeze Light palettes, font sizes, and system accents.

To install it into your SteamOS / KDE Application Launcher with icons:
```bash
./install-desktop-menu.sh
```

### 2. Headless CLI Usage
```bash
# Survey an unorganized backup drive:
./mormor survey /run/media/deck/BackupDrive

# Extract and organize photos by Continent/Country/Year:
./mormor photos /path/to/backups --dest /path/to/organized_photos

# Sift and categorize all documents:
./mormor docs /path/to/backups --dest /path/to/organized_docs

# Run local YOLOv8 privacy audit:
./mormor audit /path/to/photos --quarantine

# Clean duplicate files (safely moves losers to KDE Trash):
./mormor clean-dupes /path/to/backups --winner cleanest --trash
```

---

## 📖 Command-Line Reference

| Command | Arguments | Description |
|---|---|---|
| `gui` | *none* | Launch the full PyQt6 desktop graphical suite |
| `survey` | `<folder>` | Fast disk dump survey and duplicate estimate |
| `photos` | `<source> --dest <path> [--move]` | Extract & sort photos/videos into Continent/Year |
| `restore-photos` | `[--dest <path>]` | Undo previous photo move operation via catalog DB |
| `docs` | `<source> --dest <path> [--move]` | Ingest & categorize PDFs, Office docs, emails |
| `restore-docs` | `[--dest <path>]` | Undo previous document move operation |
| `audit` | `<folder> [--quarantine] [--model 320n\|640m]` | Audit media with local YOLOv8 computer vision |
| `vault` | `[--list\|--restore\|--purge]` | Inspect and manage quarantined files in the Vault |
| `clean-dupes` | `<folder> [--winner cleanest\|oldest] [--trash]` | Hunt and safely remove exact duplicate files |
| `similar-images` | `<folder> [--distance 5]` | Find visually similar / burst photos via perceptual hash |
| `empty-dirs` | `<folder> [--delete]` | Bottom-up empty directory tree pruner |
| `space-hogs` | `<folder> [--top 25]` | Rank the largest space hogs on disk |
| `bad-extensions` | `<folder> [--fix]` | Detect and fix mismatched file extensions |

---

## 🛠️ Developer Guide

For developers and coding agents contributing to *MormorsFilDammsugare*:

* **Onboarding & Architecture Guide**: See [HANDOFF.md](HANDOFF.md).
* **Work Sessions Log**: See [docs/SESSIONS.md](docs/SESSIONS.md).
* **Testing & Verification Checklist**: See [TODO.md](TODO.md).
* **Third-Party & Upstream Attributions**: See [ATTRIBUTIONS.md](ATTRIBUTIONS.md).
* **Release History**: See [CHANGELOG.md](CHANGELOG.md).

### Local Environment Setup
```bash
cd /home/deck/developer/MormorsFilDammsugare

# Virtual environment is pre-configured at .venv
source .venv/bin/activate

# Test Python modules
PYTHONPATH=. .venv/bin/python3 -m unittest discover tests/
```

### Safety Principles
1. **Source Immutability**: Source files are never modified in-place; copy operations are verified via byte size and SHA-256 before any removal.
2. **Safe Deletions**: Deletions use `send2trash` (FreeDesktop Trash spec) so files can be inspected in Dolphin. Hard unlinking requires explicit `--permanent`.
3. **No Windows Baggage**: Zero Microsoft/.NET dependencies. Runs pure native Linux.

---

## 📜 License & Attributions

*MormorsFilDammsugare* is licensed under the [MIT License](LICENSE).  
Algorithms and models are credited in [ATTRIBUTIONS.md](ATTRIBUTIONS.md).
