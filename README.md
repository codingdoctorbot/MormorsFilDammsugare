# 👵 MormorsFilDammsugare

*The Ultimate Native Linux Backup Triage & File Vacuum Suite.*

A single, unified, lightweight Linux/SteamOS tool uniting **Mormorskopiadammsugare**, **Arkivslukaren**, **Offline NSFW Scanner**, a built-in **Filedump Sampler**, and the best algorithms from **Czkawka** (Exact Duplicates, Similar Photos, Empty Folders, Space Hogs, Bad Extensions).

Built in Python 3 + PyQt6 with a dual-mode interface (rich GUI + headless CLI). 100% free of Windows/Microsoft runtimes.

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
   * Offline YOLOv8 AI model running locally on your hardware.
   * Audits pictures and videos for explicit content before lending your PC.
   * Quarantines sensitive files into an isolated Vault (`mormor vault`).
5. **🧹 Module 4 — Czkawka Cleaner Toolkit (`mormor clean-dupes`, `similar-images`, etc.)**:
   * **Exact Duplicates**: 3-stage high-speed duplicate finder (Size $\rightarrow$ Head/Tail probe $\rightarrow$ Full SHA-256) with smart winner selection (`cleanest`, `oldest`, `newest`) and safe trash deletion.
   * **Similar Images**: 128-bit perceptual hashing (dHash + aHash) to find compressed, resized, cropped, or burst photos.
   * **Empty Folders**: Discovers and prunes empty directory trees bottom-up.
   * **Space Hogs**: Identifies top largest files consuming your disk space.
   * **Bad Extensions**: Detects and fixes files with wrong extensions (e.g. `.CHK` $\rightarrow$ `.mp4`).

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
# Organize by Continent/Year:
./mormor photos /path/to/backups --dest /path/to/organized_photos

# Move mode (safely removes originals after copy verification):
./mormor photos /path/to/backups --dest /path/to/organized_photos --move
```

#### 3. Document Devourer
```bash
# Organize documents into Format/Year/Category:
./mormor docs /path/to/backups --dest /path/to/organized_docs
```

#### 4. Privacy Audit & Vault
```bash
# Scan a folder for explicit media:
./mormor audit /path/to/photos

# High-precision scan with immediate quarantine:
./mormor audit /path/to/photos --quarantine --model 640m
```

#### 5. Czkawka Cleaner Tools
```bash
# Hunt exact duplicates and preview winners:
./mormor clean-dupes /path/to/folder

# Delete duplicates to Freedesktop Trash (keeping cleanest filename):
./mormor clean-dupes /path/to/folder --delete --strategy cleanest

# Find visually similar photos with 128-bit perceptual hash:
./mormor similar-images /path/to/photos --distance 5

# Find and prune empty directory trees:
./mormor empty-dirs /path/to/folder --delete

# Find top 20 biggest space hogs:
./mormor space-hogs /path/to/folder --top 20

# Detect and fix bad/mismatched file extensions:
./mormor bad-extensions /path/to/folder --fix
```
