# 👵 MormorsFilDammsugare

*The Ultimate Native Linux Backup Triage & File Vacuum Suite.*

Born out of the union of `Mormorskopiadammsugare`, `Arkivslukaren`, and `offline-nsfw-scanner`, rewritten from scratch for **SteamOS / Linux (KDE Plasma)** in Python 3 + Qt. Zero Windows baggage, zero Microsoft dependencies.

---

## What It Does

When you point it at a chaotic multi-hundred-gigabyte pile of **"backups of backups"**, MormorsFilDammsugare gives you a complete, safe workflow:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MormorsFilDammsugare                            │
├───────────────┬───────────────────┬───────────────────┬────────────────┤
│  📊 0. Survey │    📷 1. Photos   │   📄 2. Docs      │   🛡️ 3. Privacy │
│  (The Sampler │  (Continent/Year  │  (Format/Category │ (YOLOv8 Local  │
│   Inspector)  │   Deduplication)  │   Deduplication)  │  Media Audit)  │
└───────────────┴───────────────────┴───────────────────┴────────────────┘
```

1. **📊 Module 0 — Filedump Sampler & Survey**:
   * Scans any folder or external drive in milliseconds.
   * Sniffs real binary magic bytes (identifies true formats, not fooled by `.CHK` or renamed extensions).
   * Generates size distribution histograms.
   * Runs fast sample-based duplicate estimation to reveal wasted gigabytes before moving any files.
2. **📷 Module 1 — Photo & Video Sorter**:
   * Sucks every photo and video out of the pile, deduplicates by SHA-256, and organizes into `Continent / Country / Year`.
3. **📄 Module 2 — Document Devourer**:
   * Extracts unique documents (PDF, Office, e-books, emails), deduplicates, and categorizes into `Format / Year / Topic`.
4. **🛡️ Module 3 — Offline Privacy Vault**:
   * Local YOLOv8 computer vision model detects explicit/sensitive media with blurred previews and quarantine vault.

---

## Quickstart (CLI)

Run the **Filedump Sampler** on any folder or external drive:

```bash
# In terminal:
./mormor survey /path/to/folder

# Export survey to JSON:
./mormor survey /path/to/folder --export-json report.json

# Skip duplicate checking for ultra-fast scan on slow USB drives:
./mormor survey /path/to/folder --no-dupes
```
