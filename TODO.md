# 📋 MormorsFilDammsugare — Testing & Roadmap TODO

## 🧪 Desktop Testing Checklist (SteamOS / KDE Plasma)

### 1. Application Menu & Environment Integration
- [ ] **Desktop Entry Installation**: Run `./install-desktop-menu.sh` and verify creation of `~/.local/share/applications/mormors-fildammsugare.desktop`.
- [ ] **KDE Application Menu**: Verify entry appears under *Utilities* / *System* in the SteamOS application menu with proper icon and name.
- [ ] **Steam Non-Steam Shortcut** (Optional): Add `mormor gui` as a non-Steam shortcut to test launching directly from SteamOS Gaming Mode / Big Picture.

### 2. Window & UI Rendering
- [ ] **Launch Verification**: Run `./mormor gui` inside an active KDE Plasma desktop session.
- [ ] **HiDPI & Window Sizing**: Verify clean default window dimension (1100x750) and responsive resizing on both 1280x800 (Deck screen) and external 1080p/4K monitors.
- [ ] **Theme & Styling**: Verify modern dark mode aesthetics integrate seamlessly with Breeze-Dark and KDE system palettes.
- [ ] **Native File Choosers**: Verify directory selector buttons invoke native KDE / Qt portal dialogs.

### 3. Functional Tab Verification
- [ ] **Tab 0 — Survey**: Test quick survey on an unorganized folder; check magic byte sniffing table and size distribution rendering.
- [ ] **Tab 1 — Photos**: Test dry-run triage of a test photo dump; verify GPS geocoding resolution and SQLite catalog recording.
- [ ] **Tab 2 — Docs**: Test document digestion into `Format/Year/Category`; check category badges and duplicate skipping.
- [ ] **Tab 3 — Privacy**: Test YOLOv8 ONNX scan on sample images; verify progress reporting and bounding-box detection scores.
- [ ] **Tab 4 — Vault**: Verify quarantine action isolates files into encrypted/renamed `.bin` storage, and verify 1-click restore returns them to original paths.
- [ ] **Tab 5 — Czkawka Cleaner**:
  - [ ] Exact Duplicates scan and dry-run preview.
  - [ ] Perceptual Similar Photos scan with adjustable Hamming distance.
  - [ ] Empty Directory tree bottom-up pruner.
  - [ ] Space Hogs top-size report.
  - [ ] Bad Extensions mismatch scanner and rename preview.

### 4. Safety & System Behavior
- [ ] **UI Responsiveness**: Verify long scans run on background worker threads without freezing the Qt event loop or triggering "Application not responding".
- [ ] **Trash Safety**: Verify duplicate/file deletion sends items to KDE Plasma Trash (`trash:///` via `send2trash`) so files can be inspected and restored in Dolphin.
- [ ] **Memory Footprint**: Confirm memory remains under ~200MB during large scans and releases promptly after completion.

---

## 🚀 Future Roadmap Items
- [ ] Video keyframe sampling for Module 3 Privacy Scanner (extract 1 frame every 5s for `.mp4`/`.mov`).
- [ ] Flatpak / AppImage packaging for 1-click portable distribution across any Linux distro.
- [ ] Optional bridge to system `czkawka_cli` when installed via Discover / Flatpak for hardware-accelerated SHA-256.
