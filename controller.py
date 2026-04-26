
import os
import re
from PySide6.QtCore import QObject
from workers import FetchPlaylistsWorker, FetchTracksWorker, KaraokeNerdsWorker

class MainController(QObject):
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view
        self.kn_worker = None

        self._connect_signals()

    def _connect_signals(self):
        self.view.connect_btn.clicked.connect(self.connect_spotify)
        self.view.playlist_combo.currentIndexChanged.connect(self.on_playlist_selected)
        self.view.load_yt_btn.clicked.connect(self.load_yt_playlist)
        self.view.start_btn.clicked.connect(self.start_check)
        self.view.cancel_btn.clicked.connect(self.cancel_check)
        self.view.about_btn.clicked.connect(self.show_about)

    def show_about(self):
        self.view.show_about_dialog()

    def connect_spotify(self):
        self.view.log("Connecting to Spotify...")
        self.view.connect_btn.setEnabled(False)
        self.worker = FetchPlaylistsWorker()
        self.worker.finished_signal.connect(self.on_playlists_fetched)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def on_playlists_fetched(self, playlists_map, username):
        self.model.playlists_map = playlists_map
        self.view.log(f"✅ Connected as: {username}")
        self.view.populate_playlists(list(playlists_map.keys()))
        self.view.connect_btn.setEnabled(True)
        self.view.start_btn.setEnabled(True)

    def on_playlist_selected(self, index):
        if index < 0:
            return
        
        selected_name = self.view.playlist_combo.currentText()
        playlist_id = self.model.playlists_map.get(selected_name)
        if not playlist_id:
            return

        self.model.active_source = "spotify"
        self.model.playlist_title_for_file = selected_name
        self.view.yt_url_entry.clear()
        
        self.view.song_count_lbl.setText("Songs: Fetching...")
        
        self.worker = FetchTracksWorker("spotify", playlist_id)
        self.worker.finished_signal.connect(self.on_tracks_fetched)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def load_yt_playlist(self):
        url = self.view.yt_url_entry.text().strip()
        if not url:
            self.view.log("Please enter a YouTube Music playlist URL.")
            return

        self.model.active_source = "youtube"
        self.view.playlist_combo.setCurrentIndex(-1)
        self.view.song_count_lbl.setText("Songs: Fetching...")
        self.view.log("Loading YouTube playlist...")

        self.worker = FetchTracksWorker("youtube", url)
        self.worker.finished_signal.connect(self.on_tracks_fetched)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def on_tracks_fetched(self, songs, title):
        self.model.loaded_songs = songs
        if self.model.active_source == "youtube":
            self.model.playlist_title_for_file = title
            self.view.log(f"✅ Loaded YouTube playlist: '{title}'")
            self.view.start_btn.setEnabled(True)
        
        total_songs = len(songs)
        self.view.song_count_lbl.setText(f"Songs: {total_songs}")
        
        seconds = int(total_songs * 1.5)
        mins, secs = divmod(seconds, 60)
        self.view.etr_lbl.setText(f"Est. Time: {mins}m {secs:02d}s")

    def start_check(self):
        if not self.model.loaded_songs:
            self.view.log("No songs loaded to check.")
            return

        self.view.set_processing_state(True)
        self.view.progress_bar.setMaximum(len(self.model.loaded_songs))
        self.view.progress_bar.setValue(0)
        self.view.log_area.clear()

        scope_map = {
            "Everything": "All",
            "Web Only": "OnlyWeb",
            "Community Only": "OnlyCommunity",
        }
        selected_scope = scope_map.get(self.view.scope_combo.currentText(), "All")

        self.view.log(f"Starting check for {len(self.model.loaded_songs)} tracks...")

        self.kn_worker = KaraokeNerdsWorker(self.model.loaded_songs, self.model, scope=selected_scope)
        self.kn_worker.progress_signal.connect(self.update_progress)
        self.kn_worker.log_signal.connect(self.view.log)
        self.kn_worker.finished_signal.connect(self.on_check_finished)
        self.kn_worker.error_signal.connect(self.on_error)
        self.kn_worker.start()

    def cancel_check(self):
        if self.kn_worker and self.kn_worker.isRunning():
            self.view.log("Cancelling... Please wait for current request to finish.")
            self.kn_worker.cancel()
            self.view.cancel_btn.setEnabled(False)

    def update_progress(self, current, total, song_name, est_seconds):
        self.view.progress_bar.setValue(current)
        mins, secs = divmod(est_seconds, 60)
        self.view.etr_lbl.setText(f"Est. Remaining: {mins}m {secs:02d}s")

    def on_check_finished(self, missing_songs):
        self.view.set_processing_state(False)
        self.view.etr_lbl.setText("Est. Remaining: 0m 00s")
        
        if missing_songs:
            safe_name = re.sub(r'[\\\\/*?:"<>|]', "", self.model.playlist_title_for_file).replace(" ", "_")
            if not safe_name:
                safe_name = "Karaoke_Check"
            filename = f"missing_{safe_name}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(missing_songs))
            self.view.log(f"\nFinished! {len(missing_songs)} missing tracks saved to '{filename}'.")
        else:
            if not getattr(self.kn_worker, "cancel_requested", False):
                self.view.log("\nFinished! Everything in this playlist has a karaoke version.")
        
        self.kn_worker = None

    def on_error(self, err_msg):
        self.view.log(f"❌ Error: {err_msg}")
        self.view.set_processing_state(False)
        self.view.song_count_lbl.setText("Songs: [Error]")
        self.view.etr_lbl.setText("Est. Time: N/A")
