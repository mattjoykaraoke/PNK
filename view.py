import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QLineEdit, QProgressBar, QTextEdit,
    QDialog
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt

class MainView(QMainWindow):
    def __init__(self, version):
        super().__init__()
        self.version = version
        self.setWindowTitle(f"PNK: Playlist Needing Karaoke v{self.version}")
        self.resize(700, 750)
        
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_path, "assets", "PNKIco.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Connect Row
        row1 = QHBoxLayout()
        self.connect_btn = QPushButton("1. Connect to Spotify")
        self.about_btn = QPushButton("About PNK")
        row1.addWidget(self.connect_btn)
        row1.addStretch()
        row1.addWidget(self.about_btn)
        main_layout.addLayout(row1)

        # Playlist Row
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Spotify Playlist:"))
        self.playlist_combo = QComboBox()
        self.playlist_combo.setMinimumWidth(250)
        self.playlist_combo.setEnabled(False)
        row2.addWidget(self.playlist_combo)
        
        row2.addStretch()
        row2.addWidget(QLabel("Search Scope:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Everything", "Web Only", "Community Only"])
        row2.addWidget(self.scope_combo)
        main_layout.addLayout(row2)

        # YouTube Row
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("OR YouTube URL:"))
        self.yt_url_entry = QLineEdit()
        self.yt_url_entry.setPlaceholderText("Paste YouTube Music Playlist URL...")
        row3.addWidget(self.yt_url_entry)
        
        self.load_yt_btn = QPushButton("Load URL")
        row3.addWidget(self.load_yt_btn)
        main_layout.addLayout(row3)

        # Status Row
        row4 = QHBoxLayout()
        self.song_count_lbl = QLabel("Songs: 0")
        self.song_count_lbl.setStyleSheet("font-weight: bold;")
        self.etr_lbl = QLabel("Est. Time: --:--")
        row4.addWidget(self.song_count_lbl)
        row4.addSpacing(20)
        row4.addWidget(self.etr_lbl)
        row4.addStretch()
        main_layout.addLayout(row4)

        # Start / Cancel Row
        row5 = QHBoxLayout()
        self.start_btn = QPushButton("2. Start Karaoke Check")
        self.start_btn.setEnabled(False)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet("color: #ff4c4c; font-weight: bold;")
        
        row5.addWidget(self.start_btn, stretch=3)
        row5.addWidget(self.cancel_btn, stretch=1)
        main_layout.addLayout(row5)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        # Setting a nice dark theme for the log area
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, monospace;
                font-size: 13px;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.log_area)

        self.log("Ready. Click 'Connect to Spotify' to load your playlists.")

    def log(self, message):
        self.log_area.append(message)
        # Scroll to bottom automatically handled by append

    def populate_playlists(self, playlist_names):
        self.playlist_combo.blockSignals(True)
        self.playlist_combo.clear()
        self.playlist_combo.addItems(playlist_names)
        self.playlist_combo.setEnabled(True)
        self.playlist_combo.blockSignals(False)

    def set_processing_state(self, processing):
        self.connect_btn.setEnabled(not processing)
        self.playlist_combo.setEnabled(not processing)
        self.yt_url_entry.setEnabled(not processing)
        self.load_yt_btn.setEnabled(not processing)
        self.start_btn.setEnabled(not processing)
        self.cancel_btn.setEnabled(processing)

    def show_about_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("About PNK")
        dlg.resize(550, 400)
        
        layout = QVBoxLayout(dlg)
        layout.setAlignment(Qt.AlignCenter)
        
        # Logo
        logo_lbl = QLabel()
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_path, "assets", "PNKLogo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(520, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pixmap)
        else:
            logo_lbl.setText("🎤 PNK")
            logo_lbl.setStyleSheet("font-size: 24px; font-weight: bold;")
        logo_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_lbl)
        
        # Text
        info_lbl = QLabel(
            "Vibe Coded in 2026 by Matt Joy.<br>"
            "<a href='https://www.youtube.com/@MattJoyKaraoke' style='color:#708090;'>youtube.com/@MattJoyKaraoke</a><br>"
            "<a href='https://github.com/mattjoykaraoke' style='color:#708090;'>github.com/mattjoykaraoke</a><br><br>"
            f"Version {self.version}.<br>"
            "Built with Python / PySide6.<br>"
            "Powered by Spotipy & BeautifulSoup.<br>"
            "This software uses open-source components.<br>"
            "See licenses folder for details.<br>"
            "Inspired by Deastrom."
        )
        info_lbl.setAlignment(Qt.AlignCenter)
        info_lbl.setOpenExternalLinks(True)
        info_lbl.setStyleSheet("font-size: 13px;")
        layout.addWidget(info_lbl)
        
        ok_btn = QPushButton("OK")
        ok_btn.setMinimumWidth(100)
        ok_btn.clicked.connect(dlg.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        dlg.exec()
