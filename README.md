# 👵 MormorsFilDammsugare

*The Ultimate Native Linux Backup Triage & File Vacuum Suite.*

A single, unified, lightweight Linux/SteamOS tool uniting **Mormorskopiadammsugare**, **Arkivslukaren**, **Offline NSFW Scanner**, and a built-in **Filedump Sampler & Survey Inspector**.

Built in Python 3 + PyQt6 with a dual-mode interface (rich GUI + headless CLI). 100% free of Windows/Microsoft runtimes.

---

## 🌟 The 4 Pillars

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MormorsFilDammsugare                            │
├───────────────┬───────────────────┬───────────────────┬────────────────┤
│  📊 0. Survey │    📷 1. Photos   │   📄 2. Docs      │   🛡️ 3. Privacy │
│  (The Sampler │  (Continent/Year  │  (Format/Category │ (YOLOv8 Local  │
│   Inspector)  │   Deduplication)  │   Deduplication)  │  Media Audit)  │
└───────────────┴───────────────────┴───────────────────┴────────────────┘
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
   * Offline YOLOv8 AI model running locally on your hardware.
   * Audits pictures and videos for explicit content before lending your PC.
   * Quarantines sensitive files into an isolated Vault (`mormor vault`).

---

## 🚀 How to Run

### Desktop GUI Mode (KDE Plasma on SteamOS)

Simply run:
```bash
./mormor
# or:
./mormor gui
```

To add MormorsFilDammsugare directly to your SteamOS Desktop Application Launcher:
```bash
./install-desktop-menu.sh
```

---

### Command-Line Usage

#### 1. Survey & Sampler
```bash
# Rapid survey of a folder:
./mormor survey /path/to/backups

# Export survey to JSON:
./mormor survey /path/to/backups --export-json survey.json
```

#### 2. Photo & Video Organization
```bash
# Dry run preview:
./mormor photos /path/to/backups --dest /path/to/organized_photos --dry-run

# Organize by Continent/Year:
./mormor photos /path/to/backups --dest /path/to/organized_photos

# Organize with Country and Swedish Län:
./mormor photos /path/to/backups --dest /path/to/organized_photos --layout region_year

# Move mode (safely removes originals after copy verification):
./mormor photos /path/to/backups --dest /path/to/organized_photos --move

# Undo and restore originals:
./mormor restore-photos --dest /path/to/organized_photos
```

#### 3. Document Devourer
```bash
# Organize documents into Format/Year/Category:
./mormor docs /path/to/backups --dest /path/to/organized_docs

# Move mode:
./mormor docs /path/to/backups --dest /path/to/organized_docs --move

# Undo and restore original documents:
./mormor restore-docs --dest /path/to/organized_docs
```

#### 4. Privacy Audit & Vault
```bash
# Scan a folder for explicit media:
./mormor audit /path/to/photos

# High-precision scan with immediate quarantine:
./mormor audit /path/to/photos --quarantine --model 640m

# Manage the Vault:
./mormor vault list
./mormor vault restore <id>
./mormor vault purge <id>
```
