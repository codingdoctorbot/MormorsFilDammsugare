# 📰 Changelog — MormorsFilDammsugare

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-24

### 🌟 Initial Release: The Great Unification

Consolidates the logic of four legacy Windows/.NET tools (`Mormorskopiadammsugare`, `Arkivslukaren`, `offline-nsfw-scanner`, and the missing Sampler) into a unified, lightweight Linux/SteamOS native application, augmented with high-speed cleanup algorithms inspired by `Czkawka`.

#### Added
* **Module 0: Filedump Sampler & Survey**
  * Binary magic-byte sniffer supporting 30+ image, video, document, and archive formats without trusting extensions.
  * Fast disk survey reporting total file counts, byte volume, file size distribution histograms, and estimated duplicate waste.
* **Module 1: Photo & Video Sorter**
  * Streaming SHA-256 deduplication ensuring each unique photo and video is extracted once.
  * Offline polygon raycasting engine reading `countries.gz` (PSGEO3 binary format) to resolve GPS coordinates into `Continent / Country / Year` (with Swedish *län* support).
  * EXIF and QuickTime/MP4 `mvhd` / `moov` metadata parsers with clock-epoch rejection.
  * Move mode with strict copy verification before removing originals.
  * SQLite WAL transactional catalog (`catalog.db`) with 1-click restore (`mormor restore-photos`).
* **Module 2: Document Devourer**
  * Text extraction and metadata digestion for PDF, DOCX, XLSX, and RFC 822 EML emails.
  * Semantic categorization into `Economy & Finance`, `Agreements & Legal`, `Personal & Career`, `Work & Projects`, and `Manuals & Documentation`.
  * Date heuristic waterfall: internal metadata $\rightarrow$ filename patterns $\rightarrow$ folder names.
* **Module 3: Privacy & Loaner Audit**
  * Offline YOLOv8 computer vision inference using local ONNX Runtime (`320n.onnx` fast model and `640m.onnx` high-precision model).
  * Strict explicit filtering and suggestive content detection with non-maximum suppression (NMS).
  * Isolated quarantine Vault storing files under randomized UUIDs (`{id}.bin` + `{id}.json`) with 1-click restoration.
* **Module 4: Czkawka Cleaner Toolkit**
  * **Exact Duplicates**: 3-stage candidate pruning (Size $\rightarrow$ 64KB Head/Tail probe $\rightarrow$ Full SHA-256) with smart winner strategies (`cleanest`, `oldest`, `newest`, `shortest_path`).
  * **Perceptual Similar Photos**: 128-bit perceptual hash (dHash + aHash) with configurable Hamming distance threshold.
  * **Empty Directory Pruner**: Bottom-up recursive tree pruning ignoring `.DS_Store` and `Thumbs.db`.
  * **Space Hogs Scanner**: Min-heap ranking of top $N$ largest files.
  * **Bad Extensions Detective**: Magic-byte vs extension verification with automated safe rename.
* **Desktop GUI & SteamOS Integration**
  * Modern PyQt6 application with 6 dedicated tabs (Survey, Photos, Docs, Privacy, Vault, Cleaner).
  * Dynamic KDE Plasma 6 theme engine (`gui/theme.py`) reading `~/.config/kdeglobals` for 100% native color palette compliance.
  * Desktop launcher installer (`install-desktop-menu.sh`) installing 256x256 PNG and scalable SVG icons into `~/.local/share/icons/hicolor/`.
  * Non-blocking background worker threads (`QThread`) for all heavy scan operations.
  * Safe file disposal using `send2trash` (FreeDesktop Trash specification) by default.
