"""MormorsFilDammsugare — Native PyQt6 Desktop Application for Linux / SteamOS.

Features:
- Tab 0: 📊 Survey & Filedump Sampler
- Tab 1: 📷 Photo & Video Sorter (Continent / Year)
- Tab 2: 📄 Document Devourer (Format / Year / Category)
- Tab 3: 🛡️ Privacy & Loaner Audit (YOLOv8 ONNX)
- Tab 4: 🔒 Quarantine Vault Manager
"""

from pathlib import Path
import sys

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..cleaner.duplicates import delete_duplicates, find_duplicates, pick_keeper
from ..cleaner.empty_dirs import delete_empty_folders, find_empty_folders
from ..cleaner.perceptual import find_similar_images
from ..cleaner.space_hogs import find_space_hogs
from ..core.walker import walk_files
from ..modules.document_devourer import DocumentDevourer, DocumentDevourerOptions
from ..modules.photo_sorter import PhotoSorter, PhotoSorterOptions
from ..modules.privacy_scanner import PrivacyScanner, PrivacyScannerOptions
from ..modules.sampler import FileSampler, format_bytes
from ..privacy.vault import VaultService
from .theme import apply_kde_theme


# Worker Threads for Background Operations
class SurveyWorker(QThread):
    finished_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(int)

    def __init__(self, target_dir: Path):
        super().__init__()
        self.target_dir = target_dir

    def run(self):
        sampler = FileSampler(check_duplicates=True)
        stats = sampler.survey(self.target_dir, progress_callback=self.progress_signal.emit)
        self.finished_signal.emit(stats)


class PhotoWorker(QThread):
    finished_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(str, int)

    def __init__(self, options: PhotoSorterOptions):
        super().__init__()
        self.options = options

    def run(self):
        sorter = PhotoSorter(self.options)
        stats = sorter.organize(progress_callback=self.progress_signal.emit)
        self.finished_signal.emit(stats)


class DocWorker(QThread):
    finished_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(str, int)

    def __init__(self, options: DocumentDevourerOptions):
        super().__init__()
        self.options = options

    def run(self):
        devourer = DocumentDevourer(self.options)
        stats = devourer.devour(progress_callback=self.progress_signal.emit)
        self.finished_signal.emit(stats)


class PrivacyWorker(QThread):
    finished_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(str, int)

    def __init__(self, options: PrivacyScannerOptions):
        super().__init__()
        self.options = options

    def run(self):
        scanner = PrivacyScanner(self.options)
        stats = scanner.scan(progress_callback=self.progress_signal.emit)
        self.finished_signal.emit(stats)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("👵 MormorsFilDammsugare — Backup Triage Suite")
        self.resize(1020, 720)
        self.vault = VaultService()

        # Window icon fallback
        icon_path = Path(__file__).parent / "assets" / "mormors-fildammsugare.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_survey_tab()
        self._build_photos_tab()
        self._build_docs_tab()
        self._build_privacy_tab()
        self._build_vault_tab()
        self._build_cleaner_tab()

    # --- TAB 0: SURVEY ---
    def _build_survey_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Picker
        box = QGroupBox("Target Folder / Backup Drive")
        box_layout = QHBoxLayout(box)
        self.survey_path = QLineEdit()
        self.survey_path.setPlaceholderText("/run/media/... or /home/deck/...")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(lambda: self._browse_dir(self.survey_path))
        self.btn_run_survey = QPushButton("🔍 Start Survey")
        self.btn_run_survey.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_run_survey.clicked.connect(self._run_survey)

        box_layout.addWidget(self.survey_path)
        box_layout.addWidget(btn_browse)
        box_layout.addWidget(self.btn_run_survey)
        layout.addWidget(box)

        # Progress
        self.survey_progress = QProgressBar()
        self.survey_progress.setVisible(False)
        self.survey_progress.setRange(0, 0)
        layout.addWidget(self.survey_progress)

        # Overview Stats
        self.lbl_survey_summary = QLabel("Point to a backup folder and press 'Start Survey'.")
        self.lbl_survey_summary.setStyleSheet("font-size: 14px; margin: 6px 0;")
        layout.addWidget(self.lbl_survey_summary)

        # Table
        self.survey_table = QTableWidget(0, 4)
        self.survey_table.setHorizontalHeaderLabels(["Category", "Files", "% Files", "Total Size"])
        self.survey_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.survey_table)

        # Action handoff buttons
        handoff_layout = QHBoxLayout()
        btn_to_photos = QPushButton("📷 Send Photos to Sorter")
        btn_to_photos.clicked.connect(self._handoff_to_photos)
        btn_to_docs = QPushButton("📄 Send Docs to Devourer")
        btn_to_docs.clicked.connect(self._handoff_to_docs)
        handoff_layout.addWidget(btn_to_photos)
        handoff_layout.addWidget(btn_to_docs)
        layout.addLayout(handoff_layout)

        self.tabs.addTab(tab, "📊 0. Survey & Sampler")

    def _run_survey(self):
        p = Path(self.survey_path.text().strip())
        if not p.exists() or not p.is_dir():
            QMessageBox.warning(self, "Invalid Path", "Please select a valid directory to survey.")
            return

        self.btn_run_survey.setEnabled(False)
        self.survey_progress.setVisible(True)
        self.lbl_survey_summary.setText(f"Surveying {p.name}...")

        self.worker = SurveyWorker(p)
        self.worker.progress_signal.connect(lambda n: self.lbl_survey_summary.setText(f"Scanning... ({n:,} files)"))
        self.worker.finished_signal.connect(self._on_survey_finished)
        self.worker.start()

    def _on_survey_finished(self, stats):
        self.btn_run_survey.setEnabled(True)
        self.survey_progress.setVisible(False)

        summary_text = (
            f"<b>Total:</b> {stats.total_files:,} files ({format_bytes(stats.total_bytes)}) in {stats.scan_time_seconds:.2f}s"
        )
        if stats.estimated_duplicate_files > 0:
            summary_text += f" | <span style='color: #e74c3c;'><b>Duplicates:</b> ~{stats.estimated_duplicate_files:,} files wasting {format_bytes(stats.estimated_wasted_bytes)}</span>"
        self.lbl_survey_summary.setText(summary_text)

        self.survey_table.setRowCount(0)
        sorted_cats = sorted(stats.category_bytes.items(), key=lambda x: x[1], reverse=True)
        for cat, b in sorted_cats:
            cnt = stats.category_counts[cat]
            pct = (cnt / stats.total_files * 100) if stats.total_files else 0
            row = self.survey_table.rowCount()
            self.survey_table.insertRow(row)
            self.survey_table.setItem(row, 0, QTableWidgetItem(cat))
            self.survey_table.setItem(row, 1, QTableWidgetItem(f"{cnt:,}"))
            self.survey_table.setItem(row, 2, QTableWidgetItem(f"{pct:.1f}%"))
            self.survey_table.setItem(row, 3, QTableWidgetItem(format_bytes(b)))

    def _handoff_to_photos(self):
        path = self.survey_path.text().strip()
        if path:
            self.photo_src.setText(path)
            self.tabs.setCurrentIndex(1)

    def _handoff_to_docs(self):
        path = self.survey_path.text().strip()
        if path:
            self.doc_src.setText(path)
            self.tabs.setCurrentIndex(2)

    # --- TAB 1: PHOTOS ---
    def _build_photos_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Source & Dest
        box = QGroupBox("Locations")
        b_layout = QVBoxLayout(box)

        s_row = QHBoxLayout()
        self.photo_src = QLineEdit()
        self.photo_src.setPlaceholderText("Source directory...")
        btn_src = QPushButton("Browse...")
        btn_src.clicked.connect(lambda: self._browse_dir(self.photo_src))
        s_row.addWidget(QLabel("Source:"))
        s_row.addWidget(self.photo_src)
        s_row.addWidget(btn_src)
        b_layout.addLayout(s_row)

        d_row = QHBoxLayout()
        self.photo_dst = QLineEdit()
        self.photo_dst.setPlaceholderText("Destination directory...")
        btn_dst = QPushButton("Browse...")
        btn_dst.clicked.connect(lambda: self._browse_dir(self.photo_dst))
        d_row.addWidget(QLabel("Dest:    "))
        d_row.addWidget(self.photo_dst)
        d_row.addWidget(btn_dst)
        b_layout.addLayout(d_row)

        layout.addWidget(box)

        # Options
        opt_box = QGroupBox("Organization Settings")
        opt_layout = QHBoxLayout(opt_box)

        self.cb_photo_layout = QComboBox()
        self.cb_photo_layout.addItem("Continent / Year (Default)", "continent_year")
        self.cb_photo_layout.addItem("Continent / Country / Year", "country_year")
        self.cb_photo_layout.addItem("Continent / Country / Län / Year", "region_year")

        self.chk_photo_move = QCheckBox("Move mode (safe remove)")
        self.chk_photo_dry = QCheckBox("Dry run")

        opt_layout.addWidget(QLabel("Folder Tree:"))
        opt_layout.addWidget(self.cb_photo_layout)
        opt_layout.addWidget(self.chk_photo_move)
        opt_layout.addWidget(self.chk_photo_dry)
        layout.addWidget(opt_box)

        # Action
        act_layout = QHBoxLayout()
        self.btn_run_photos = QPushButton("📷 Vacuum Photos & Videos")
        self.btn_run_photos.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        self.btn_run_photos.clicked.connect(self._run_photos)

        btn_restore_photos = QPushButton("↩ Restore Originals (Undo)")
        btn_restore_photos.clicked.connect(self._restore_photos)

        act_layout.addWidget(self.btn_run_photos)
        act_layout.addWidget(btn_restore_photos)
        layout.addLayout(act_layout)

        self.lbl_photo_status = QLabel("Ready.")
        layout.addWidget(self.lbl_photo_status)

        layout.addStretch()
        self.tabs.addTab(tab, "📷 1. Photos & Videos")

    def _run_photos(self):
        src = Path(self.photo_src.text().strip())
        dst = Path(self.photo_dst.text().strip())
        if not src.exists() or not dst:
            QMessageBox.warning(self, "Invalid Paths", "Please set valid source and destination folders.")
            return

        opts = PhotoSorterOptions(
            source_dirs=[src],
            dest_dir=dst,
            layout=self.cb_photo_layout.currentData(),
            is_move=self.chk_photo_move.isChecked(),
            dry_run=self.chk_photo_dry.isChecked(),
        )

        self.btn_run_photos.setEnabled(False)
        self.photo_worker = PhotoWorker(opts)
        self.photo_worker.progress_signal.connect(lambda f, n: self.lbl_photo_status.setText(f"Organized {n:,} ({f})"))
        self.photo_worker.finished_signal.connect(self._on_photos_finished)
        self.photo_worker.start()

    def _on_photos_finished(self, stats):
        self.btn_run_photos.setEnabled(True)
        msg = f"Done! Photos: {stats.photos_processed:,}, Videos: {stats.videos_processed:,}, Duplicates Skipped: {stats.duplicates_skipped:,}"
        if self.chk_photo_move.isChecked():
            msg += f", Originals Removed: {stats.originals_removed:,}"
        self.lbl_photo_status.setText(msg)
        QMessageBox.information(self, "Photos Organized", msg)

    def _restore_photos(self):
        dst = Path(self.photo_dst.text().strip())
        if not dst.exists():
            QMessageBox.warning(self, "Invalid Destination", "Destination folder not found.")
            return
        restored = PhotoSorter.restore_originals(dst)
        QMessageBox.information(self, "Restore Complete", f"Restored {restored:,} original files back to their sources.")

    # --- TAB 2: DOCUMENTS ---
    def _build_docs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Locations")
        b_layout = QVBoxLayout(box)

        s_row = QHBoxLayout()
        self.doc_src = QLineEdit()
        self.doc_src.setPlaceholderText("Source directory...")
        btn_src = QPushButton("Browse...")
        btn_src.clicked.connect(lambda: self._browse_dir(self.doc_src))
        s_row.addWidget(QLabel("Source:"))
        s_row.addWidget(self.doc_src)
        s_row.addWidget(btn_src)
        b_layout.addLayout(s_row)

        d_row = QHBoxLayout()
        self.doc_dst = QLineEdit()
        self.doc_dst.setPlaceholderText("Destination directory...")
        btn_dst = QPushButton("Browse...")
        btn_dst.clicked.connect(lambda: self._browse_dir(self.doc_dst))
        d_row.addWidget(QLabel("Dest:    "))
        d_row.addWidget(self.doc_dst)
        d_row.addWidget(btn_dst)
        b_layout.addLayout(d_row)

        layout.addWidget(box)

        # Options
        opt_box = QGroupBox("Document Settings")
        opt_layout = QHBoxLayout(opt_box)

        self.chk_doc_move = QCheckBox("Move mode (safe remove)")
        self.chk_doc_dry = QCheckBox("Dry run")
        self.chk_doc_times = QCheckBox("Trust file dates")

        opt_layout.addWidget(self.chk_doc_move)
        opt_layout.addWidget(self.chk_doc_times)
        opt_layout.addWidget(self.chk_doc_dry)
        layout.addWidget(opt_box)

        # Action
        act_layout = QHBoxLayout()
        self.btn_run_docs = QPushButton("📄 Devour Documents")
        self.btn_run_docs.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        self.btn_run_docs.clicked.connect(self._run_docs)

        btn_restore_docs = QPushButton("↩ Restore Originals (Undo)")
        btn_restore_docs.clicked.connect(self._restore_docs)

        act_layout.addWidget(self.btn_run_docs)
        act_layout.addWidget(btn_restore_docs)
        layout.addLayout(act_layout)

        self.lbl_doc_status = QLabel("Ready.")
        layout.addWidget(self.lbl_doc_status)

        layout.addStretch()
        self.tabs.addTab(tab, "📄 2. Document Devourer")

    def _run_docs(self):
        src = Path(self.doc_src.text().strip())
        dst = Path(self.doc_dst.text().strip())
        if not src.exists() or not dst:
            QMessageBox.warning(self, "Invalid Paths", "Please set valid source and destination folders.")
            return

        opts = DocumentDevourerOptions(
            source_dirs=[src],
            dest_dir=dst,
            trust_file_times=self.chk_doc_times.isChecked(),
            is_move=self.chk_doc_move.isChecked(),
            dry_run=self.chk_doc_dry.isChecked(),
        )

        self.btn_run_docs.setEnabled(False)
        self.doc_worker = DocWorker(opts)
        self.doc_worker.progress_signal.connect(lambda f, n: self.lbl_doc_status.setText(f"Devoured {n:,} ({f})"))
        self.doc_worker.finished_signal.connect(self._on_docs_finished)
        self.doc_worker.start()

    def _on_docs_finished(self, stats):
        self.btn_run_docs.setEnabled(True)
        msg = f"Done! Documents: {stats.documents_processed:,}, Duplicates Skipped: {stats.duplicates_skipped:,}"
        if self.chk_doc_move.isChecked():
            msg += f", Originals Removed: {stats.originals_removed:,}"
        self.lbl_doc_status.setText(msg)
        QMessageBox.information(self, "Documents Devoured", msg)

    def _restore_docs(self):
        dst = Path(self.doc_dst.text().strip())
        if not dst.exists():
            QMessageBox.warning(self, "Invalid Destination", "Destination folder not found.")
            return
        restored = PhotoSorter.restore_originals(dst)
        QMessageBox.information(self, "Restore Complete", f"Restored {restored:,} original documents back to their sources.")

    # --- TAB 3: PRIVACY AUDIT ---
    def _build_privacy_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Privacy Audit Folder")
        b_layout = QHBoxLayout(box)
        self.priv_src = QLineEdit()
        self.priv_src.setPlaceholderText("Folder to scan before lending PC...")
        btn_src = QPushButton("Browse...")
        btn_src.clicked.connect(lambda: self._browse_dir(self.priv_src))
        b_layout.addWidget(self.priv_src)
        b_layout.addWidget(btn_src)
        layout.addWidget(box)

        # Options
        opt_box = QGroupBox("Model & Sensitivity")
        opt_layout = QHBoxLayout(opt_box)

        self.cb_model = QComboBox()
        self.cb_model.addItem("Fast CPU (320n)", "320n")
        self.cb_model.addItem("High Precision (640m)", "640m")

        self.chk_priv_strict = QCheckBox("Strict nudity only")
        self.chk_priv_suggestive = QCheckBox("Include suggestive")
        self.chk_priv_quarantine = QCheckBox("Quarantine to Vault immediately")

        opt_layout.addWidget(QLabel("Model:"))
        opt_layout.addWidget(self.cb_model)
        opt_layout.addWidget(self.chk_priv_strict)
        opt_layout.addWidget(self.chk_priv_suggestive)
        opt_layout.addWidget(self.chk_priv_quarantine)
        layout.addWidget(opt_box)

        self.btn_run_priv = QPushButton("🛡️ Start Privacy Audit")
        self.btn_run_priv.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        self.btn_run_priv.clicked.connect(self._run_privacy)
        layout.addWidget(self.btn_run_priv)

        self.lbl_priv_status = QLabel("Ready.")
        layout.addWidget(self.lbl_priv_status)

        # Results table
        self.priv_table = QTableWidget(0, 3)
        self.priv_table.setHorizontalHeaderLabels(["Filename", "Detected Classes", "Max Conf"])
        self.priv_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.priv_table)

        self.tabs.addTab(tab, "🛡️ 3. Privacy Audit")

    def _run_privacy(self):
        src = Path(self.priv_src.text().strip())
        if not src.exists():
            QMessageBox.warning(self, "Invalid Path", "Please select a valid folder to audit.")
            return

        opts = PrivacyScannerOptions(
            source_dirs=[src],
            strict_only=self.chk_priv_strict.isChecked(),
            include_suggestive=self.chk_priv_suggestive.isChecked(),
            quarantine_flagged=self.chk_priv_quarantine.isChecked(),
            model_name=self.cb_model.currentData(),
        )

        self.btn_run_priv.setEnabled(False)
        self.priv_worker = PrivacyWorker(opts)
        self.priv_worker.progress_signal.connect(lambda f, n: self.lbl_priv_status.setText(f"Scanning {n:,} ({f})"))
        self.priv_worker.finished_signal.connect(self._on_privacy_finished)
        self.priv_worker.start()

    def _on_privacy_finished(self, stats):
        self.btn_run_priv.setEnabled(True)
        self.lbl_priv_status.setText(f"Audited {stats.total_scanned:,} images in {stats.scan_time_seconds:.2f}s. Flagged: {len(stats.flagged_files):,}")

        self.priv_table.setRowCount(0)
        for res in stats.flagged_files:
            row = self.priv_table.rowCount()
            self.priv_table.insertRow(row)
            self.priv_table.setItem(row, 0, QTableWidgetItem(res.filepath.name))
            classes = ", ".join(f"{d.friendly_name} ({d.confidence:.2f})" for d in res.detections[:3])
            self.priv_table.setItem(row, 1, QTableWidgetItem(classes))
            self.priv_table.setItem(row, 2, QTableWidgetItem(f"{res.max_confidence:.2f}"))

        self._refresh_vault_tab()

    # --- TAB 4: VAULT ---
    def _build_vault_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("🔒 Isolated Quarantine Vault"))
        btn_refresh = QPushButton("Refresh Vault")
        btn_refresh.clicked.connect(self._refresh_vault_tab)
        top_layout.addWidget(btn_refresh)
        layout.addLayout(top_layout)

        self.vault_table = QTableWidget(0, 4)
        self.vault_table.setHorizontalHeaderLabels(["ID", "Original Filename", "Size", "Quarantined At"])
        self.vault_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.vault_table)

        btn_restore_v = QPushButton("Restore Selected to Original Path")
        btn_restore_v.clicked.connect(self._restore_selected_vault)
        layout.addWidget(btn_restore_v)

        self.tabs.addTab(tab, "🔒 4. Vault")
        self._refresh_vault_tab()

    def _refresh_vault_tab(self):
        entries = self.vault.list_entries()
        self.vault_table.setRowCount(0)
        for e in entries:
            row = self.vault_table.rowCount()
            self.vault_table.insertRow(row)
            self.vault_table.setItem(row, 0, QTableWidgetItem(e.id[:8]))
            self.vault_table.setItem(row, 1, QTableWidgetItem(e.filename))
            self.vault_table.setItem(row, 2, QTableWidgetItem(format_bytes(e.size)))
            self.vault_table.setItem(row, 3, QTableWidgetItem(e.quarantined_at[:19]))

    def _restore_selected_vault(self):
        row = self.vault_table.currentRow()
        if row < 0:
            return
        item_id_prefix = self.vault_table.item(row, 0).text()
        entries = self.vault.list_entries()
        target = next((e for e in entries if e.id.startswith(item_id_prefix)), None)
        if target:
            restored_path = self.vault.restore(target.id)
            QMessageBox.information(self, "Restored", f"Restored to:\n{restored_path}")
            self._refresh_vault_tab()

    # --- TAB 5: CZKAWKA CLEANER ---
    def _build_cleaner_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Target Folder")
        b_layout = QHBoxLayout(box)
        self.cleaner_src = QLineEdit()
        self.cleaner_src.setPlaceholderText("Folder to clean...")
        btn_src = QPushButton("Browse...")
        btn_src.clicked.connect(lambda: self._browse_dir(self.cleaner_src))
        b_layout.addWidget(self.cleaner_src)
        b_layout.addWidget(btn_src)
        layout.addWidget(box)

        # Tools action row
        act_box = QGroupBox("Czkawka Tools")
        act_layout = QHBoxLayout(act_box)

        btn_find_dupes = QPushButton("⚡ Exact Duplicates")
        btn_find_dupes.clicked.connect(self._run_find_dupes)

        btn_sim_images = QPushButton("🖼️ Similar Photos")
        btn_sim_images.clicked.connect(self._run_similar_photos)

        btn_empty_dirs = QPushButton("📁 Empty Folders")
        btn_empty_dirs.clicked.connect(self._run_empty_folders)

        btn_space_hogs = QPushButton("🐳 Big Space Hogs")
        btn_space_hogs.clicked.connect(self._run_space_hogs)

        act_layout.addWidget(btn_find_dupes)
        act_layout.addWidget(btn_sim_images)
        act_layout.addWidget(btn_empty_dirs)
        act_layout.addWidget(btn_space_hogs)
        layout.addWidget(act_box)

        self.lbl_cleaner_status = QLabel("Pick a folder and choose a Czkawka cleaner tool.")
        layout.addWidget(self.lbl_cleaner_status)

        # Cleaner Results Table
        self.cleaner_table = QTableWidget(0, 3)
        self.cleaner_table.setHorizontalHeaderLabels(["Name / Group", "Details", "Size / Count"])
        self.cleaner_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.cleaner_table)

        self.btn_clean_action = QPushButton("Prune / Trash Selected")
        self.btn_clean_action.setVisible(False)
        self.btn_clean_action.clicked.connect(self._perform_cleaner_action)
        layout.addWidget(self.btn_clean_action)

        self.tabs.addTab(tab, "🧹 5. Czkawka Cleaner")

    def _run_find_dupes(self):
        src = Path(self.cleaner_src.text().strip())
        if not src.exists():
            QMessageBox.warning(self, "Invalid Path", "Select a valid directory.")
            return

        self.lbl_cleaner_status.setText(f"Scanning for exact duplicates in {src.name}...")
        self.current_dupe_groups = find_duplicates([src])

        total_dupes = sum(len(g.files) - 1 for g in self.current_dupe_groups)
        total_wasted = sum(g.size * (len(g.files) - 1) for g in self.current_dupe_groups)

        self.lbl_cleaner_status.setText(f"Found {len(self.current_dupe_groups):,} groups with {total_dupes:,} redundant copies wasting {format_bytes(total_wasted)}.")
        self.cleaner_table.setRowCount(0)
        self.cleaner_table.setHorizontalHeaderLabels(["Keep (Winner)", "Remove (Duplicate)", "Wasted Size"])

        for g in self.current_dupe_groups:
            keeper, to_remove = pick_keeper(g.files, strategy="cleanest")
            row = self.cleaner_table.rowCount()
            self.cleaner_table.insertRow(row)
            self.cleaner_table.setItem(row, 0, QTableWidgetItem(keeper.name))
            self.cleaner_table.setItem(row, 1, QTableWidgetItem(", ".join(r.name for r in to_remove)))
            self.cleaner_table.setItem(row, 2, QTableWidgetItem(format_bytes(g.size * len(to_remove))))

        if total_dupes > 0:
            self.btn_clean_action.setText(f"🗑️ Move {total_dupes:,} Duplicates to Trash ({format_bytes(total_wasted)})")
            self.btn_clean_action.setVisible(True)
            self.cleaner_action_mode = "dupes"
        else:
            self.btn_clean_action.setVisible(False)

    def _run_similar_photos(self):
        src = Path(self.cleaner_src.text().strip())
        if not src.exists():
            QMessageBox.warning(self, "Invalid Path", "Select a valid directory.")
            return

        from ..core.sniffer import MediaCategory, sniff_file
        imgs = [f for f in walk_files(src) if sniff_file(f).category == MediaCategory.PHOTO]
        self.lbl_cleaner_status.setText(f"Computing perceptual hashes for {len(imgs):,} photos...")
        groups = find_similar_images(imgs, max_distance=5)

        self.lbl_cleaner_status.setText(f"Found {len(groups):,} clusters of visually similar photos.")
        self.cleaner_table.setRowCount(0)
        self.cleaner_table.setHorizontalHeaderLabels(["Base Image", "Similar Photos", "Resolution & Match"])

        for g in groups:
            base = g.base_image
            row = self.cleaner_table.rowCount()
            self.cleaner_table.insertRow(row)
            self.cleaner_table.setItem(row, 0, QTableWidgetItem(f"{base.path.name} ({base.width}x{base.height})"))
            sim_names = ", ".join(other.path.name for other, _ in g.similar_images)
            self.cleaner_table.setItem(row, 1, QTableWidgetItem(sim_names))
            sim_scores = ", ".join(f"{100 - (d / 128 * 100):.0f}%" for _, d in g.similar_images)
            self.cleaner_table.setItem(row, 2, QTableWidgetItem(sim_scores))

        self.btn_clean_action.setVisible(False)

    def _run_empty_folders(self):
        src = Path(self.cleaner_src.text().strip())
        if not src.exists():
            QMessageBox.warning(self, "Invalid Path", "Select a valid directory.")
            return

        self.current_empty_dirs = find_empty_folders(src)
        self.lbl_cleaner_status.setText(f"Found {len(self.current_empty_dirs):,} empty folders.")
        self.cleaner_table.setRowCount(0)
        self.cleaner_table.setHorizontalHeaderLabels(["Empty Directory Path", "Relative Path", "Status"])

        for d in self.current_empty_dirs:
            row = self.cleaner_table.rowCount()
            self.cleaner_table.insertRow(row)
            self.cleaner_table.setItem(row, 0, QTableWidgetItem(str(d)))
            try:
                rel = str(d.relative_to(src))
            except Exception:
                rel = str(d)
            self.cleaner_table.setItem(row, 1, QTableWidgetItem(rel))
            self.cleaner_table.setItem(row, 2, QTableWidgetItem("Empty"))

        if self.current_empty_dirs:
            self.btn_clean_action.setText(f"🗑️ Delete {len(self.current_empty_dirs):,} Empty Folders")
            self.btn_clean_action.setVisible(True)
            self.cleaner_action_mode = "empty_dirs"
        else:
            self.btn_clean_action.setVisible(False)

    def _run_space_hogs(self):
        src = Path(self.cleaner_src.text().strip())
        if not src.exists():
            QMessageBox.warning(self, "Invalid Path", "Select a valid directory.")
            return

        hogs = find_space_hogs([src], top_n=30)
        self.lbl_cleaner_status.setText(f"Top {len(hogs)} largest files in {src.name}.")
        self.cleaner_table.setRowCount(0)
        self.cleaner_table.setHorizontalHeaderLabels(["Filename", "Category / Format", "File Size"])

        for h in hogs:
            row = self.cleaner_table.rowCount()
            self.cleaner_table.insertRow(row)
            self.cleaner_table.setItem(row, 0, QTableWidgetItem(h.path.name))
            self.cleaner_table.setItem(row, 1, QTableWidgetItem(f"{h.category} ({h.format_name})"))
            self.cleaner_table.setItem(row, 2, QTableWidgetItem(format_bytes(h.size)))

        self.btn_clean_action.setVisible(False)

    def _perform_cleaner_action(self):
        if self.cleaner_action_mode == "dupes":
            removed, freed = delete_duplicates(self.current_dupe_groups, strategy="cleanest", use_trash=True, dry_run=False)
            QMessageBox.information(self, "Duplicates Cleaned", f"Moved {removed:,} duplicate files to Trash, reclaiming {format_bytes(freed)} space.")
            self._run_find_dupes()
        elif self.cleaner_action_mode == "empty_dirs":
            removed = delete_empty_folders(self.current_empty_dirs, dry_run=False)
            QMessageBox.information(self, "Pruning Complete", f"Deleted {removed:,} empty folders.")
            self._run_empty_folders()

    def _browse_dir(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            line_edit.setText(folder)


def run_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    apply_kde_theme(app, window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
