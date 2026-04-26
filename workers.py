import time
from PySide6.QtCore import QThread, Signal
from api import SpotifyClient, YTMusicClient, KaraokeNerdsClient

class FetchPlaylistsWorker(QThread):
    finished_signal = Signal(dict, str)
    error_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.sp_client = SpotifyClient()

    def run(self):
        try:
            username = self.sp_client.connect()
            playlists = self.sp_client.get_playlists()
            self.finished_signal.emit(playlists, username)
        except Exception as e:
            self.error_signal.emit(str(e))

class FetchTracksWorker(QThread):
    finished_signal = Signal(list, str)
    error_signal = Signal(str)

    def __init__(self, source, identifier):
        super().__init__()
        self.source = source
        self.identifier = identifier

    def run(self):
        try:
            songs = []
            title = ""
            if self.source == "spotify":
                sp_client = SpotifyClient()
                sp_client.connect()
                songs = sp_client.get_tracks(self.identifier)
                title = "Spotify_Playlist"
            elif self.source == "youtube":
                yt_client = YTMusicClient()
                playlist_id = yt_client.extract_playlist_id(self.identifier)
                if not playlist_id:
                    raise ValueError("Invalid YouTube URL. Could not find 'list' query parameter.")
                songs, title = yt_client.get_tracks(playlist_id)
            
            self.finished_signal.emit(songs, title)
        except Exception as e:
            self.error_signal.emit(str(e))

class KaraokeNerdsWorker(QThread):
    progress_signal = Signal(int, int, str, int)
    log_signal = Signal(str)
    finished_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(self, songs, model, scope="All"):
        super().__init__()
        self.songs = songs
        self.model = model
        self.scope = scope
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def run(self):
        try:
            kn_client = KaraokeNerdsClient()
            missing_songs = []
            total = len(self.songs)

            for i, song in enumerate(self.songs):
                if self.cancel_requested:
                    self.log_signal.emit("\n⚠️ Check Cancelled by User.")
                    break

                original_name = song["original"]
                artist = song["artist"]
                title = song["title"]

                remaining = total - i
                est_seconds = int(remaining * 1.5)

                self.progress_signal.emit(i + 1, total, original_name, est_seconds)
                
                # Check cache
                cached_result = self.model.check_cache(original_name)
                if cached_result is True:
                    self.log_signal.emit(f"✅ Found (Cached): {original_name}")
                    continue
                elif cached_result is False:
                    self.log_signal.emit(f"❌ NOT FOUND (Cached): {original_name}")
                    missing_songs.append(original_name)
                    continue

                # Not in cache, query network
                self.log_signal.emit(f"Searching: {original_name}")
                found = kn_client.search_song(artist, title, scope=self.scope)
                
                # Save to cache
                self.model.save_to_cache(original_name, found)

                if found:
                    self.log_signal.emit(f"✅ Found: {original_name}")
                else:
                    self.log_signal.emit(f"❌ NOT FOUND: {original_name}")
                    missing_songs.append(original_name)

                # Rate limiting sleep ONLY if we hit the network
                if not self.cancel_requested:
                    time.sleep(1.5)

            self.finished_signal.emit(missing_songs)
        except Exception as e:
            self.error_signal.emit(str(e))
