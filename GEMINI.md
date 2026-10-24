# MormorsFilDammsugare Project Guidelines

## Stack & Architecture
- **Language & Runtime**: Python 3.14 running in dedicated project-local `.venv/`.
- **Framework**: PyQt6 for Desktop GUI (KDE Plasma 6 native) + dual-mode rich CLI.
- **No Windows/.NET Dependencies**: Zero Microsoft or Windows runtimes. Pure Linux native.

## Core Modules
1. **Module 0 — Survey & Sampler**: Fast folder survey with binary magic-byte sniffing (`sniffer.py`, `sampler.py`).
2. **Module 1 — Photo & Video Sorter**: SHA-256 deduplication, offline GPS raycasting via `countries.gz` (PSGEO3 binary), SQLite WAL catalog (`catalog/db.py`).
3. **Module 2 — Document Devourer**: Sifts PDF, DOCX, XLSX, EML into `Format/Year/Category` with semantic topic heuristics.
4. **Module 3 — Privacy & Loaner Audit**: Local CPU YOLOv8 ONNX models (`320n.onnx`, `640m.onnx`) with isolated quarantine Vault (`{id}.bin` + `{id}.json`).
5. **Module 4 — Czkawka Cleaner Toolkit**: 3-stage exact duplicate finder (`Size -> 64KB Probe -> SHA-256`), 128-bit perceptual image hash (dHash + aHash), bottom-up empty directory pruner, space hogs min-heap, and extension sniffer.

## Safety Invariants
- Source files are never modified in-place.
- Move mode requires SHA-256 copy verification before removing original source files.
- Duplicate removal must default to `send2trash` (FreeDesktop Trash spec) rather than hard unlinking.
- Undo is managed via `catalog.db` SQLite database.

## Quality & Testing
- Run test suite: `PYTHONPATH=. .venv/bin/python3 -m unittest discover tests/`.
- Verify KDE Plasma theme integration via `mormorsfildammsugare.gui.theme`.
