import os
import re
import sys
import threading
import time
import tkinter as tk
import urllib.parse
import webbrowser
from difflib import SequenceMatcher
from tkinter import scrolledtext, ttk

import requests
import spotipy
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image, ImageTk
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables
load_dotenv()


class PNKApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNK: Playlist Needing Karaoke")
        self.root.geometry("650x680")  # Increased height for YouTube URL row

        self.sp = None
        self.playlists_map = {}
        self.is_running = False
        self.active_source = "spotify"

        self.setup_ui()

    def setup_ui(self):
        # Top Frame for Controls
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)

        # Row 0: Connect & About
        self.connect_btn = ttk.Button(
            control_frame, text="1. Connect to Spotify", command=self.connect_spotify
        )
        self.connect_btn.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.about_btn = ttk.Button(
            control_frame, text="About PNK", command=self.show_about
        )
        self.about_btn.grid(row=0, column=3, sticky=tk.E, padx=5, pady=5)

        # Row 1: Playlist Selection & Search Scope
        ttk.Label(control_frame, text="Spotify Playlist:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )

        self.playlist_combo = ttk.Combobox(control_frame, width=35, state=tk.DISABLED)
        self.playlist_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        # Bind selection change to update stats immediately
        self.playlist_combo.bind("<<ComboboxSelected>>", self.on_playlist_selected)

        ttk.Label(control_frame, text="Search Scope:").grid(
            row=1, column=2, sticky=tk.W, padx=(15, 5), pady=5
        )

        # Increased width from 15 to 18 so "Community Only" isn't cut off by DPI scaling
        self.scope_combo = ttk.Combobox(control_frame, width=18, state="readonly")
        self.scope_combo["values"] = ("Everything", "Web Only", "Community Only")
        self.scope_combo.current(0)
        self.scope_combo.grid(row=1, column=3, sticky=tk.W, pady=5)

        # Row 2: YouTube Music Integration
        ttk.Label(control_frame, text="OR YouTube URL:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )

        self.yt_url_entry = ttk.Entry(control_frame, width=37)
        self.yt_url_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        self.load_yt_btn = ttk.Button(
            control_frame, text="Load URL", command=self.load_yt_playlist
        )
        self.load_yt_btn.grid(row=2, column=2, sticky=tk.W, padx=(15, 5), pady=5)

        # Row 3: Status Row (Songs count and ETR)
        status_info_frame = ttk.Frame(control_frame)
        status_info_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=2)

        self.song_count_lbl = ttk.Label(
            status_info_frame, text="Songs: 0", font=("Segoe UI", 9, "bold")
        )
        self.song_count_lbl.pack(side=tk.LEFT, padx=(0, 20))

        self.etr_lbl = ttk.Label(
            status_info_frame, text="Est. Time: --:--", font=("Segoe UI", 9)
        )
        self.etr_lbl.pack(side=tk.LEFT)

        # Row 4: Start Check
        self.start_btn = ttk.Button(
            control_frame,
            text="2. Start Karaoke Check",
            command=self.start_thread,
            state=tk.DISABLED,
        )
        self.start_btn.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)

        # Progress Bar
        self.progress = ttk.Progressbar(
            self.root, orient=tk.HORIZONTAL, mode="determinate"
        )
        self.progress.pack(fill=tk.X, padx=10, pady=5)

        # Log Window
        self.log_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=18)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log("Ready. Click 'Connect to Spotify' to load your playlists.")

    def log(self, message):
        self.log_area.insert(tk.END, str(message) + "\n")
        self.log_area.see(tk.END)
        self.root.update()

    def connect_spotify(self):
        client_id = os.environ.get("SPOTIPY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")

        if not all([client_id, client_secret, redirect_uri]):
            self.log("❌ Error: Missing Spotify credentials. Check your .env file.")
            return

        try:
            self.log("Authenticating...")
            scope = (
                "user-library-read playlist-read-private playlist-read-collaborative"
            )

            # Setup a safe, writable directory in the user's home folder for the cache
            app_dir = os.path.join(os.path.expanduser("~"), ".pnk_app")
            os.makedirs(app_dir, exist_ok=True)
            cache_path = os.path.join(app_dir, ".spotify_cache")

            auth_manager = SpotifyOAuth(scope=scope, cache_path=cache_path)

            # Force the initial token fetch (opens browser if logging in for the first time)
            auth_manager.get_access_token(as_dict=False)

            # CRITICAL FIX: Disable Spotipy from opening browsers in the background ever again
            auth_manager.open_browser = False

            self.sp = spotipy.Spotify(auth_manager=auth_manager)

            user = self.sp.current_user()
            self.log(f"✅ Connected as: {user.get('display_name', 'User')}")

            self.load_playlists()

        except Exception as e:
            self.log(f"Connection Error: {e}")

    def load_playlists(self):
        self.log("Fetching your playlists...")
        self.playlists_map = {"Liked Songs (Saved Tracks)": "liked"}

        try:
            results = self.sp.current_user_playlists(limit=50)
            while results:
                for item in results["items"]:
                    if item:
                        name = item["name"]
                        self.playlists_map[name] = item["id"]
                if results["next"]:
                    results = self.sp.next(results)
                else:
                    results = None

            self.playlist_combo["values"] = list(self.playlists_map.keys())
            self.playlist_combo.current(0)
            self.playlist_combo.config(state="readonly")
            self.start_btn.config(state=tk.NORMAL)

            # Show stats for default playlist
            self.on_playlist_selected(None)

            self.log(f"Loaded {len(self.playlists_map)} playlists. Ready to scan.")

        except Exception as e:
            self.log(f"Error fetching playlists: {e}")

    def on_playlist_selected(self, event):
        """Updates the UI with track count and initial ETR when playlist changes."""
        self.active_source = "spotify"
        self.yt_url_entry.delete(0, tk.END)

        selected_name = self.playlist_combo.get()
        playlist_id = self.playlists_map.get(selected_name)

        if not playlist_id:
            return

        def update_task():
            try:
                if playlist_id == "liked":
                    results = self.sp.current_user_saved_tracks(limit=1)
                else:
                    results = self.sp.playlist_items(
                        playlist_id, fields="total", limit=1
                    )

                total_songs = results.get("total", 0)
                self.song_count_lbl.config(text=f"Songs: {total_songs}")

                seconds = int(total_songs * 1.7)
                mins, secs = divmod(seconds, 60)
                self.etr_lbl.config(text=f"Est. Time: {mins}m {secs:02d}s")
            except Exception as e:
                if "403" in str(e):
                    self.song_count_lbl.config(text="Songs: [Blocked]")
                    self.etr_lbl.config(text="Est. Time: N/A")
                else:
                    self.song_count_lbl.config(text="Songs: --")

        threading.Thread(target=update_task, daemon=True).start()

    def load_yt_playlist(self):
        url = self.yt_url_entry.get().strip()
        if not url:
            self.log("Please enter a YouTube Music playlist URL.")
            return

        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        playlist_id = query.get("list", [None])[0]

        if not playlist_id:
            self.log("Invalid URL. Could not find a 'list' ID in the URL.")
            return

        self.active_source = "youtube"
        self.playlist_combo.set("")  # Clear Spotify visual selection
        self.log(f"Loading YouTube playlist ID: {playlist_id}...")

        def update_task():
            try:
                import ytmusicapi

                ytmusic = ytmusicapi.YTMusic()
                playlist = ytmusic.get_playlist(playlist_id, limit=None)

                total_songs = len(playlist.get("tracks", []))
                self.song_count_lbl.config(text=f"Songs: {total_songs}")

                seconds = int(total_songs * 1.7)
                mins, secs = divmod(seconds, 60)
                self.etr_lbl.config(text=f"Est. Time: {mins}m {secs:02d}s")

                self.log(
                    f"✅ Loaded YouTube playlist: '{playlist.get('title', 'Unknown')}'"
                )
                self.start_btn.config(state=tk.NORMAL)
            except ImportError:
                self.log("❌ Missing library: ytmusicapi is not installed.")
                self.log("Please run this in your terminal: pip install ytmusicapi")
            except Exception as e:
                self.song_count_lbl.config(text="Songs: [Blocked]")
                self.etr_lbl.config(text="Est. Time: N/A")
                self.log(
                    "\n❌ YouTube Music blocked access to this playlist or it is Private."
                )
                self.log(
                    "Note: To check your 'Liked Music', batch-select them, add them to a new 'Unlisted' playlist, and paste that link here."
                )
                self.log(f"Details: {str(e)}")

        threading.Thread(target=update_task, daemon=True).start()

    def start_thread(self):
        if self.is_running:
            return
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.connect_btn.config(state=tk.DISABLED)
        self.playlist_combo.config(state=tk.DISABLED)
        self.yt_url_entry.config(state=tk.DISABLED)
        self.load_yt_btn.config(state=tk.DISABLED)
        self.progress["value"] = 0
        self.log_area.delete(1.0, tk.END)

        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        try:
            songs = []
            playlist_title_for_file = ""

            if self.active_source == "youtube":
                songs, playlist_title_for_file = self.get_yt_playlist_tracks()
            else:
                songs = self.get_playlist_tracks()
                playlist_title_for_file = self.playlist_combo.get()

            if not songs:
                self.log("No songs found to check.")
                self.reset_ui()
                return

            self.log(f"Fetched {len(songs)} total tracks. Cross-referencing...\n")
            self.check_karaoke_nerds(songs, playlist_title_for_file)

        except Exception as e:
            self.log(f"An error occurred: {str(e)}")
        finally:
            self.reset_ui()

    def get_yt_playlist_tracks(self):
        url = self.yt_url_entry.get().strip()
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        playlist_id = query.get("list", [None])[0]

        if not playlist_id:
            return [], ""

        self.log(f"Accessing YouTube playlist items...")
        try:
            import ytmusicapi

            ytmusic = ytmusicapi.YTMusic()
            playlist = ytmusic.get_playlist(playlist_id, limit=None)

            songs = []
            for track in playlist.get("tracks", []):
                title = track.get("title", "Unknown Title")
                artists_data = track.get("artists", [])
                artist = "Unknown Artist"
                if artists_data and isinstance(artists_data, list):
                    artist = artists_data[0].get("name", "Unknown Artist")

                original_name = f"{artist} - {title}"
                songs.append(
                    {"original": original_name, "artist": artist, "title": title}
                )

            return songs, playlist.get("title", "YouTube_Playlist")
        except Exception as e:
            self.log("\n❌ YouTube Music blocked access to this playlist.")
            self.log("Note: Make sure the playlist is set to 'Public' or 'Unlisted'.")
            return [], ""

    def get_playlist_tracks(self):
        selected_name = self.playlist_combo.get()
        playlist_id = self.playlists_map.get(selected_name)
        songs = []
        if not playlist_id:
            return []

        self.log(f"Accessing playlist items for: {selected_name}...")
        try:
            if playlist_id == "liked":
                results = self.sp.current_user_saved_tracks(limit=50)
            else:
                results = self.sp.playlist_items(playlist_id, limit=50)

            while results:
                items = results.get("items", [])

                for item in items:
                    if not item or not isinstance(item, dict):
                        continue

                    # 1. Flatten the structure aggressively
                    # Spotify normally uses 'track', but some endpoints/playlists use 'item'
                    track_data = item
                    if "track" in item and isinstance(item["track"], dict):
                        track_data = item["track"]
                    elif "item" in item and isinstance(item["item"], dict):
                        track_data = item["item"]

                    # 2. Extract Artist
                    artist = "Unknown Artist"
                    artists_data = track_data.get("artists") or track_data.get("artist")

                    if isinstance(artists_data, list) and len(artists_data) > 0:
                        first_artist = artists_data[0]
                        if isinstance(first_artist, dict):
                            artist = first_artist.get("name", "Unknown Artist")
                        else:
                            artist = str(first_artist)
                    elif isinstance(artists_data, str):
                        artist = artists_data
                    elif isinstance(artists_data, dict):
                        artist = artists_data.get("name", "Unknown Artist")

                    # 3. Extract Title
                    title = track_data.get("name")
                    if not title:
                        # Fallback to checking the parent item just in case
                        title = item.get("name")

                    if not title or str(title).strip() == "" or str(title) == "None":
                        title = "Unknown Title"
                    else:
                        title = str(title).strip()

                    # Skip ONLY if we got absolutely nothing
                    if artist == "Unknown Artist" and title == "Unknown Title":
                        continue

                    original_name = f"{artist} - {title}"
                    songs.append(
                        {"original": original_name, "artist": artist, "title": title}
                    )

                # 4. Handle Pagination
                if results.get("next"):
                    results = self.sp.next(results)
                else:
                    results = None

            return songs
        except Exception as e:
            if "403" in str(e) and "Forbidden" in str(e):
                self.log(
                    "\n❌ Spotify blocked access to this playlist (403 Forbidden)."
                )
                self.log(
                    "Note: Spotify completely prevents 3rd-party apps from reading 'Blend' playlists, personalized algorithmic playlists, and restricted private playlists."
                )
            else:
                self.log(f"Error fetching tracks: {e}")
            return []

    def is_similar(self, a, b, threshold=0.6):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold

    def clean_title_only(self, title):
        clean_title = re.sub(r"\(.*?\)|\[.*?\]", "", title)
        clean_title = re.sub(r"(?i)feat\..*|ft\..*", "", clean_title)
        clean_title = re.sub(r"[^\w\s]", " ", clean_title)
        return " ".join(clean_title.split())

    def check_karaoke_nerds(self, songs, playlist_title="Playlist"):
        scope_map = {
            "Everything": "All",
            "Web Only": "OnlyWeb",
            "Community Only": "OnlyCommunity",
        }
        selected_scope = scope_map.get(self.scope_combo.get(), "All")

        missing_songs = []
        total = len(songs)
        self.progress["maximum"] = total

        for i, song_data in enumerate(songs):
            original_name = song_data["original"]
            spotify_artist = song_data["artist"]
            spotify_title = song_data["title"]

            remaining = total - i
            est_seconds = int(remaining * 1.7)
            mins, secs = divmod(est_seconds, 60)
            self.etr_lbl.config(text=f"Est. Remaining: {mins}m {secs:02d}s")

            self.log(f"Checking: {original_name}")

            clean_title = self.clean_title_only(spotify_title)
            query_url = urllib.parse.quote_plus(clean_title)
            url = f"https://karaokenerds.com/Search?query={query_url}&webFilter={selected_scope}"

            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")
                found_match = False

                rows = soup.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        kn_artist = cols[1].text.strip()
                        if self.is_similar(spotify_artist, kn_artist):
                            found_match = True
                            break

                if found_match:
                    self.log(f"✅ Found")
                else:
                    self.log(f"❌ NOT FOUND")
                    missing_songs.append(original_name)

            except Exception as e:
                self.log(f"Connection error: {e}")

            self.progress["value"] = i + 1
            time.sleep(1.5)

        self.etr_lbl.config(text="Est. Remaining: 0m 00s")
        if missing_songs:
            # Grab the playlist name and sanitize it for a valid filename
            safe_name = re.sub(r'[\\/*?:"<>|]', "", playlist_title).replace(" ", "_")
            if not safe_name:
                safe_name = "Karaoke_Check"
            filename = f"missing_{safe_name}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(missing_songs))
            self.log(
                f"\nFinished! {len(missing_songs)} missing tracks saved to '{filename}'."
            )
        else:
            self.log("\nFinished! Everything in this playlist has a karaoke version.")

    def reset_ui(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.connect_btn.config(state=tk.NORMAL)
        self.playlist_combo.config(state="readonly")
        self.yt_url_entry.config(state=tk.NORMAL)
        self.load_yt_btn.config(state=tk.NORMAL)

    def show_about(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("About PNK")
        dlg.configure(bg="#1E1E1E")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        font_normal = ("Segoe UI", 10)
        bg_color = "#1E1E1E"
        fg_normal = "white"
        fg_link = "#708090"

        try:
            # Bulletproof cross-platform path resolution (works for source code and PyInstaller)
            base_path = getattr(
                sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
            )
            logo_path = os.path.join(base_path, "assets", "PNKLogo.png")

            img = Image.open(logo_path)
            img.thumbnail((520, 220), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            logo_lbl = tk.Label(dlg, image=photo, bg=bg_color)
            logo_lbl.image = photo
            logo_lbl.pack(pady=(16, 5), padx=16)
        except Exception:
            tk.Label(
                dlg,
                text="🎤 PNK",
                font=("Segoe UI", 24, "bold"),
                fg=fg_normal,
                bg=bg_color,
            ).pack(pady=(16, 5))

        tk.Label(
            dlg,
            text="Vibe Coded in 2026 by Matt Joy.",
            font=font_normal,
            fg=fg_normal,
            bg=bg_color,
        ).pack()

        yt_link = tk.Label(
            dlg,
            text="youtube.com/@MattJoyKaraoke",
            font=font_normal,
            fg=fg_link,
            bg=bg_color,
            cursor="hand2",
        )
        yt_link.pack()
        yt_link.bind(
            "<Button-1>",
            lambda e: webbrowser.open("https://www.youtube.com/@MattJoyKaraoke"),
        )

        gh_link = tk.Label(
            dlg,
            text="github.com/mattjoykaraoke",
            font=font_normal,
            fg=fg_link,
            bg=bg_color,
            cursor="hand2",
        )
        gh_link.pack()
        gh_link.bind(
            "<Button-1>", lambda e: webbrowser.open("https://github.com/mattjoykaraoke")
        )

        tk.Label(
            dlg, text="\nVersion 1.2.1.", font=font_normal, fg=fg_normal, bg=bg_color
        ).pack()
        tk.Label(
            dlg,
            text="Built with Python / Tkinter.",
            font=font_normal,
            fg=fg_normal,
            bg=bg_color,
        ).pack()
        tk.Label(
            dlg,
            text="Powered by Spotipy & BeautifulSoup.",
            font=font_normal,
            fg=fg_normal,
            bg=bg_color,
        ).pack()
        tk.Label(
            dlg,
            text="This software uses open-source components.",
            font=font_normal,
            fg=fg_normal,
            bg=bg_color,
        ).pack()
        tk.Label(
            dlg,
            text="See licenses folder for details.",
            font=font_normal,
            fg=fg_normal,
            bg=bg_color,
        ).pack()
        tk.Label(
            dlg,
            text="Inspired by Deastrom.",
            font=font_normal,
            fg=fg_normal,
            bg=bg_color,
        ).pack()

        ok_btn = tk.Button(
            dlg,
            text="OK",
            command=dlg.destroy,
            bg="#333333",
            fg="white",
            relief="flat",
            activebackground="#444444",
            activeforeground="white",
            padx=14,
            pady=4,
            cursor="hand2",
        )
        ok_btn.pack(pady=(20, 16))

        dlg.update_idletasks()
        x = (
            self.root.winfo_x()
            + (self.root.winfo_width() // 2)
            - (dlg.winfo_width() // 2)
        )
        y = (
            self.root.winfo_y()
            + (self.root.winfo_height() // 2)
            - (dlg.winfo_height() // 2)
        )
        dlg.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PNKApp(root)
    root.mainloop()
