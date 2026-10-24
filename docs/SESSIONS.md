# 📓 Work Sessions Log — MormorsFilDammsugare

This document records the design decisions, implementation milestones, and architectural evolution of *MormorsFilDammsugare*.

---

## Session 1: Migration Strategy & Discovery
**Date**: 2026-10-24  
**Context**: Evaluation of `/home/deck/developer/photo-tools` on SteamOS.

### Objectives
* Inspect existing repositories: `Arkivslukaren`, `Mormorskopiadammsugare`, `PhotoSorter`, `offline-nsfw-scanner`, and `photos-trash-restorer`.
* Locate the missing "file info / filedump sampler" tool.
* Determine whether to run .NET 10 on Linux or port to a Linux-native stack.

### Key Decisions & Findings
1. **The Missing Sampler Tool**:
   * Investigation confirmed that the sampler never existed as a standalone repo. Concepts existed in `Arkivslukaren/tools/realpile/probe_parsers.py` and `offline-nsfw-scanner/tools/ScanBenchmark`.
   * Decision: Build Module 0 as a first-class **Filedump Sampler & Survey** component.
2. **Platform & Runtime Choice**:
   * All legacy tools were written in C# targeting Windows desktop (`net10.0-windows` with WPF). WPF cannot run on Linux.
   * Installing user-space .NET runtimes would add unnecessary weight to SteamOS.
   * Decision: Consolidate all logic into a single Linux-native Python 3.14 + PyQt6 superapp, matching the user's existing SteamOS utility `mem-watch`.
3. **Naming**:
   * Selected Swedish pun name: **`MormorsFilDammsugare`** ("*Grandma's File Vacuum Cleaner*").

---

## Session 2: Core Engine & Modules 0–3
**Date**: 2026-10-24  
**Context**: Implementation of the fundamental architecture and porting the three C# codebases.

### Milestones Completed
1. **Core Utilities**:
   * Fast file walker (`core/walker.py`) with ignore rules (`.git`, `node_modules`, `AppData`, `Thumbs.db`).
   * Magic-byte sniffing (`core/sniffer.py`) covering 30+ binary formats.
   * Streaming SHA-256 and fast 64KB head/tail fingerprinting (`core/hasher.py`).
2. **Module 0 — Filedump Sampler**:
   * Surveys unknown folders in milliseconds, providing size histograms and duplicate estimates.
3. **Module 1 — Photo & Video Sorter**:
   * Ported offline polygon raycaster (`geo/locator.py`) reading `countries.gz` (PSGEO3 binary format). Resolves Swedish *län* without network access.
   * EXIF and QuickTime/MP4 `mvhd` metadata parsing with epoch rejection.
   * SQLite WAL transactional catalog (`catalog/db.py`) for safe move mode and 1-click restore.
4. **Module 2 — Document Devourer**:
   * PDF, DOCX, XLSX, and RFC 822 EML email text extraction and date heuristic waterfall.
   * Semantic categorization into `Economy`, `Legal`, `Career`, `Work`, and `Manuals`.
5. **Module 3 — Privacy & Loaner Audit**:
   * Bundled `320n.onnx` and `640m.onnx` YOLOv8 computer vision models.
   * CPU inference via ONNX Runtime with letterbox padding and non-maximum suppression (NMS).
   * Isolated quarantine Vault (`privacy/vault.py`) renaming sensitive files to UUIDs.

---

## Session 3: Czkawka Cleaner Toolkit Integration
**Date**: 2026-10-24  
**Context**: Implementing open source algorithms inspired by Czkawka.

### Milestones Completed
1. **Exact Duplicate Finder (`cleaner/duplicates.py`)**:
   * 3-stage candidate pruning: Size $\rightarrow$ 64KB Head/Tail probe $\rightarrow$ Full SHA-256.
   * Smart winner strategies: `cleanest` (prefer master files over `(1)` copies), `oldest`, `newest`, `shortest_path`.
   * Safe FreeDesktop trash integration via `send2trash`.
2. **Perceptual Image Similarity (`cleaner/perceptual.py`)**:
   * 128-bit perceptual hash (64-bit dHash + 64-bit aHash).
   * Hamming distance clustering for burst shots, rescaled images, and alternate formats.
3. **Empty Directory Pruner (`cleaner/empty_dirs.py`)**:
   * Bottom-up recursive tree traversal ignoring `.DS_Store` and `Thumbs.db`.
4. **Space Hogs Scanner (`cleaner/space_hogs.py`)**:
   * Min-heap ranking of top $N$ largest files.
5. **Bad Extension Detective (`cleaner/bad_extensions.py`)**:
   * Binary magic bytes vs declared extension validator with safe rename proposals.

---

## Session 4: Legacy Deprecation, GitHub Archiving & Initial Release
**Date**: 2026-10-24  
**Context**: Retiring old repositories and publishing `MormorsFilDammsugare`.

### Milestones Completed
1. **GitHub Repository Creation**:
   * Created public repository `codingdoctorbot/MormorsFilDammsugare` and pushed initial commit tree.
2. **Retirement of Old GitHub Repos**:
   * Added deprecation banners pointing to `MormorsFilDammsugare` on:
     * `Arkivslukaren`
     * `Mormorskopiadammsugare`
     * `offline-nsfw-scanner`
     * `PhotoSorter`
   * Marked all 4 repositories as archived (`read-only`) via GitHub API / `gh repo archive`.
3. **Local Filesystem Tidy**:
   * Moved old local repos to `/home/deck/developer/_archive/legacy-dotnet-photo-tools/`.
   * Relocated `photos-trash-restorer` to `/home/deck/developer/browser-extensions/`.
   * Recorded paths in `/home/deck/developer/_archive/MOVES.tsv`.

---

## Session 5: KDE Theme Perfection, App Icon Branding & Dev Documentation
**Date**: 2026-10-24  
**Context**: Polishing desktop appearance on KDE Plasma 6 and establishing development standards.

### Milestones Completed
1. **Native KDE Plasma 6 Theme Engine (`gui/theme.py`)**:
   * Dynamically parses `~/.config/kdeglobals` for window, view, button, highlight, and tooltip colors.
   * Builds matching `QPalette` and Breeze-compliant QSS stylesheet.
   * Respects system dark/light switching and SteamOS color schemes without hardcoded hex clashes.
2. **Application Icon & Desktop Integration**:
   * Generated vector SVG icon and bundled 256x256 RGBA desktop icons in `gui/assets/`.
   * Configured `install-desktop-menu.sh` to install icons into FreeDesktop hicolor icon directories (`~/.local/share/icons/hicolor/`).
   * Wired icons to `QApplication` and `MainWindow` for taskbar and Alt-Tab recognition.
3. **Developer Experience Documentation**:
   * Created `HANDOFF.md`, `ATTRIBUTIONS.md`, `CHANGELOG.md`, and updated `TODO.md` to ensure any future developer or AI agent can pick up where we left off.
