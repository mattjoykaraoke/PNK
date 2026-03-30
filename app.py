import os
import re
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
        self.root.geometry("650x550")

        self.sp = None
        self.playlists_map = {}
        self.is_running = False

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
        ttk.Label(control_frame, text="Select Playlist:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )

        # This is the ONLY playlist combo that should exist
        self.playlist_combo = ttk.Combobox(control_frame, width=35, state=tk.DISABLED)
        self.playlist_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(control_frame, text="Search Scope:").grid(
            row=1, column=2, sticky=tk.W, padx=(15, 5), pady=5
        )

        self.scope_combo = ttk.Combobox(control_frame, width=15, state="readonly")
        self.scope_combo["values"] = ("Everything", "Web Only", "Community Only")
        self.scope_combo.current(0)
        self.scope_combo.grid(row=1, column=3, sticky=tk.W, pady=5)

        # Row 2: Start Check
        self.start_btn = ttk.Button(
            control_frame,
            text="2. Start Karaoke Check",
            command=self.start_thread,
            state=tk.DISABLED,
        )
        self.start_btn.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)

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
        self.log_area.insert(tk.END, message + "\n")
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
            # We need playlist-read-private to see your custom playlists
            scope = "user-library-read playlist-read-private"
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

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
                        self.playlists_map[item["name"]] = item["id"]
                if results["next"]:
                    results = self.sp.next(results)
                else:
                    results = None

            # Update UI
            self.playlist_combo["values"] = list(self.playlists_map.keys())
            self.playlist_combo.current(0)
            self.playlist_combo.config(state="readonly")

            self.start_btn.config(state=tk.NORMAL)
            self.log(f"Loaded {len(self.playlists_map)} playlists. Ready to scan.")

        except Exception as e:
            self.log(f"Error fetching playlists: {e}")

    def start_thread(self):
        if self.is_running:
            return
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.connect_btn.config(state=tk.DISABLED)
        self.playlist_combo.config(state=tk.DISABLED)
        self.progress["value"] = 0
        self.log_area.delete(1.0, tk.END)

        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        try:
            songs = self.get_playlist_tracks()

            if not songs:
                self.log("No songs found in this playlist.")
                self.reset_ui()
                return

            self.log(
                f"Found {len(songs)} tracks. Cross-referencing with KaraokeNerds...\n"
            )
            self.check_karaoke_nerds(songs)

        except Exception as e:
            self.log(f"An error occurred: {str(e)}")
        finally:
            self.reset_ui()

    def get_playlist_tracks(self):
        selected_name = self.playlist_combo.get()
        playlist_id = self.playlists_map.get(selected_name)

        songs = []
        try:
            if playlist_id == "liked":
                results = self.sp.current_user_saved_tracks(limit=50)
            else:
                results = self.sp.playlist_items(playlist_id, limit=50)

            while results:
                for item in results["items"]:
                    track = item.get("track")
                    # Skip local files or broken tracks that have no artist data
                    if not track or not track.get("artists"):
                        continue

                    artist = track["artists"][0]["name"]
                    title = track["name"]
                    original_name = f"{artist} - {title}"

                    songs.append(
                        {"original": original_name, "artist": artist, "title": title}
                    )

                if results["next"]:
                    results = self.sp.next(results)
                else:
                    results = None
            return songs
        except Exception as e:
            self.log(f"Error fetching tracks: {e}")
            return []

    def is_similar(self, a, b, threshold=0.6):
        """Fuzzy string matching for the Artist column."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold

    def clean_title_only(self, title):
        """Strips out features and parentheses to get the core song title."""
        clean_title = re.sub(r"\(.*?\)|\[.*?\]", "", title)
        clean_title = re.sub(r"(?i)feat\..*|ft\..*", "", clean_title)
        clean_title = re.sub(r"[^\w\s]", " ", clean_title)
        return " ".join(clean_title.split())

    def check_karaoke_nerds(self, songs):
        # Map the UI selection to the URL parameter
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

            self.log(f"Checking: {original_name}")

            clean_title = self.clean_title_only(spotify_title)
            query_url = urllib.parse.quote_plus(clean_title)
            url = f"https://karaokenerds.com/Search?query={query_url}&webFilter={selected_scope}"

            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")
                found_match = False

                # Check the results table
                rows = soup.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        kn_title = cols[0].text.strip()
                        kn_artist = cols[1].text.strip()

                        # Fuzzy match the artist to confirm it's the right song
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

        if missing_songs:
            with open("missing_karaoke_tracks.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(missing_songs))
            self.log(
                f"\nFinished! {len(missing_songs)} missing tracks saved to 'missing_karaoke_tracks.txt'."
            )
        else:
            self.log("\nFinished! Everything in this playlist has a karaoke version.")

    def reset_ui(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.connect_btn.config(state=tk.NORMAL)
        self.playlist_combo.config(state="readonly")

    def show_about(self):
        # Create a modal dialog
        dlg = tk.Toplevel(self.root)
        dlg.title("About PNK")
        dlg.configure(bg="#1E1E1E")
        dlg.resizable(False, False)

        # Make it modal (blocks interacting with the main window)
        dlg.transient(self.root)
        dlg.grab_set()

        # Styles
        font_normal = ("Segoe UI", 10)
        bg_color = "#1E1E1E"
        fg_normal = "white"
        fg_link = "#708090"

        # --- Logo ---
        try:
            # Assumes you have an assets folder with a logo like in ChromaLyric
            img = Image.open("assets/PNKLogo.png")
            # Scales the image smoothly while keeping aspect ratio
            img.thumbnail((520, 220), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            logo_lbl = tk.Label(dlg, image=photo, bg=bg_color)
            logo_lbl.image = (
                photo  # Keep a reference so it doesn't get garbage collected
            )
            logo_lbl.pack(pady=(16, 5), padx=16)
        except Exception:
            # Fallback text if the image doesn't exist yet
            tk.Label(
                dlg,
                text="🎤 PNK",
                font=("Segoe UI", 24, "bold"),
                fg=fg_normal,
                bg=bg_color,
            ).pack(pady=(16, 5))

        # --- Text Content ---
        tk.Label(
            dlg,
            text="Vibe Coded in 2026 by Matt Joy.",
            font=font_normal,
            fg=fg_normal,
            bg=bg_color,
        ).pack()

        # Clickable YouTube Link
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

        # Clickable GitHub Link
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

        # Additional Info
        tk.Label(
            dlg, text="\nVersion 1.1.0.", font=font_normal, fg=fg_normal, bg=bg_color
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

        # --- OK Button ---
        # Using a standard tk.Button here to easily force the dark mode styling
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

        # Center the dialog window relative to the main app window
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
