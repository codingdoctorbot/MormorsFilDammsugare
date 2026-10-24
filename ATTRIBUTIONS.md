# 📜 Attributions & Third-Party Notices

*MormorsFilDammsugare* is built on the shoulders of several open source projects, research models, and prior iterations of backup triage utilities.

---

## 🏛️ Direct Ancestors & Core Logic

### 1. [Mormorskopiadammsugare](https://github.com/codingdoctorbot/Mormorskopiadammsugare)
* **Author**: codingdoctorbot (License: MIT)
* **Contributions**:
  * Core photo & video extraction and SHA-256 stream deduplication.
  * EXIF tag parsing and QuickTime/MP4 `mvhd` / `moov` capture date extraction.
  * Offline polygon raycasting algorithm and `PSGEO3` binary format reader for reverse geocoding GPS coordinates without network requests.
  * Multi-level organization hierarchy: `Continent / Country / Year` (with Swedish *län* resolution).
  * Safe Move mode design: verification of kept copy before removing original, SQLite `catalog.db` transactional undo (*Restore originals*).

### 2. [Arkivslukaren](https://github.com/codingdoctorbot/Arkivslukaren)
* **Author**: codingdoctorbot (License: MIT)
* **Contributions**:
  * Semantic document digestion engine.
  * Multi-format content sniffers and text extractors for PDF, DOCX, XLSX, and RFC 822 EML emails.
  * Keyword-based category classification heuristics:
    * `Economy & Finance` (fakturor, kvitton, lönespecifikationer, deklaration)
    * `Agreements & Legal` (avtal, kontrakt, intyg, fullmakt)
    * `Personal & Career` (CV, personligt brev, betyg, intyg)
    * `Work & Projects` (rapporter, presentationer, protokoll)
    * `Manuals & Documentation` (manualer, instruktioner, datablad)
  * File-name and internal metadata date parser waterfall.

### 3. [Offline NSFW Scanner](https://github.com/codingdoctorbot/offline-nsfw-scanner)
* **Author**: codingdoctorbot (License: GPL-3.0)
* **Contributions**:
  * Offline YOLOv8 computer vision pipeline for personal loaner/privacy audits.
  * Bundled ONNX model weights (`320n.onnx` fast model and `640m.onnx` medium-precision model).
  * Isolated quarantine Vault architecture: files are renamed to encrypted UUIDs (`{id}.bin` + `{id}.json`), removing access while maintaining lossless 1-click restoration.

---

## 🧹 Czkawka Algorithms

### [Czkawka](https://github.com/qarmin/czkawka)
* **Author**: Rafał Mikrut (`qarmin`) (License: MIT)
* **Contributions**:
  * **3-Stage Fast Duplicate Pipeline**: Grouping candidate files by exact byte size $\rightarrow$ computing 64KB Head & Tail partial hashes $\rightarrow$ streaming full SHA-256 verification only on remaining matches.
  * **Winner Resolution Strategies**: Automatic selection of duplicates to delete or keep (`cleanest`, `oldest`, `newest`, `shortest_path`).
  * **Perceptual Image Similarity**: Fast 128-bit perceptual hash combining difference hash (`dHash`) and average hash (`aHash`) with Hamming distance comparison to detect burst photos, scaled thumbnails, and re-encoded graphics.
  * **Bottom-Up Empty Directory Pruner**: Post-order tree walking with exclusion rules for invisible desktop clutter (`.DS_Store`, `Thumbs.db`).
  * **Binary Sniffing**: Checking binary headers (magic bytes) against declared extensions to catch renamed or mismatched files.

---

## 🌍 Geographic Datasets

### [Natural Earth](https://www.naturalearthdata.com/)
* Public domain map datasets used to generate the boundary polygons for world continents and countries in `countries.gz`.
* Swedish administrative boundary polygons (Län / Counties) compiled into the binary spatial lookup tree.

---

## 🐍 Open Source Python & Qt Dependencies

| Package | License | Purpose |
|---|---|---|
| **PyQt6** | GPL v3 | Desktop GUI framework and KDE Plasma desktop integration |
| **onnxruntime** | MIT | High-performance CPU execution engine for YOLOv8 neural network |
| **Pillow (PIL)** | HPND | Image decoding, EXIF metadata extraction, perceptual image hashing |
| **pypdf** | BSD-3-Clause | PDF text extraction and document creation date inspection |
| **python-docx** | MIT | Microsoft Word DOCX metadata and text parsing |
| **openpyxl** | MIT | Microsoft Excel XLSX metadata inspection |
| **send2trash** | BSD-3-Clause | Native FreeDesktop Trash integration for Linux / KDE Dolphin |
| **rich** | MIT | Terminal formatting, progress spinners, colorized tables in CLI |
| **numpy** | BSD-3-Clause | Tensor transformations and letterbox padding for YOLOv8 ONNX |
