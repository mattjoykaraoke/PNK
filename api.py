import os
import urllib.parse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from bs4 import BeautifulSoup
from utils import clean_title_only, is_similar

class SpotifyClient:
    def __init__(self):
        self.sp = None
        self.user = None
    
    def connect(self):
        client_id = os.environ.get("SPOTIPY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")

        if not all([client_id, client_secret, redirect_uri]):
            raise ValueError("Missing Spotify credentials. Check your .env file.")

        scope = "user-library-read playlist-read-private playlist-read-collaborative"
        app_dir = os.path.join(os.path.expanduser("~"), ".pnk_app")
        os.makedirs(app_dir, exist_ok=True)
        cache_path = os.path.join(app_dir, ".spotify_cache")

        auth_manager = SpotifyOAuth(scope=scope, cache_path=cache_path)
        auth_manager.get_access_token(as_dict=False)
        auth_manager.open_browser = False

        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        self.user = self.sp.current_user()
        return self.user.get('display_name', 'User')

    def get_playlists(self):
        playlists_map = {"Liked Songs (Saved Tracks)": "liked"}
        results = self.sp.current_user_playlists(limit=50)
        while results:
            for item in results["items"]:
                if item:
                    playlists_map[item["name"]] = item["id"]
            if results["next"]:
                results = self.sp.next(results)
            else:
                break
        return playlists_map

    def get_tracks(self, playlist_id):
        songs = []
        if playlist_id == "liked":
            results = self.sp.current_user_saved_tracks(limit=50)
        else:
            results = self.sp.playlist_items(playlist_id, limit=50)

        while results:
            items = results.get("items", [])
            for item in items:
                if not item or not isinstance(item, dict):
                    continue

                track_data = item
                if "track" in item and isinstance(item["track"], dict):
                    track_data = item["track"]
                elif "item" in item and isinstance(item["item"], dict):
                    track_data = item["item"]

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

                title = track_data.get("name") or item.get("name")
                if not title or str(title).strip() == "" or str(title) == "None":
                    title = "Unknown Title"
                else:
                    title = str(title).strip()

                if artist == "Unknown Artist" and title == "Unknown Title":
                    continue

                original_name = f"{artist} - {title}"
                songs.append({"original": original_name, "artist": artist, "title": title})

            if results.get("next"):
                results = self.sp.next(results)
            else:
                break
        return songs

    def get_playlist_track_count(self, playlist_id):
        if playlist_id == "liked":
            results = self.sp.current_user_saved_tracks(limit=1)
        else:
            results = self.sp.playlist_items(playlist_id, fields="total", limit=1)
        return results.get("total", 0)

class YTMusicClient:
    def __init__(self):
        try:
            import ytmusicapi
            self.ytmusic = ytmusicapi.YTMusic()
            self.available = True
        except ImportError:
            self.ytmusic = None
            self.available = False

    def extract_playlist_id(self, url):
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        return query.get("list", [None])[0]

    def get_tracks(self, playlist_id):
        if not self.available:
            raise ImportError("ytmusicapi not installed.")
        
        playlist = self.ytmusic.get_playlist(playlist_id, limit=None)
        songs = []
        for track in playlist.get("tracks", []):
            title = track.get("title", "Unknown Title")
            artists_data = track.get("artists", [])
            artist = "Unknown Artist"
            if artists_data and isinstance(artists_data, list):
                artist = artists_data[0].get("name", "Unknown Artist")

            original_name = f"{artist} - {title}"
            songs.append({"original": original_name, "artist": artist, "title": title})

        return songs, playlist.get("title", "YouTube_Playlist")

class KaraokeNerdsClient:
    def __init__(self):
        self.session = requests.Session()

    def search_song(self, artist, title, scope="All"):
        clean_title = clean_title_only(title)
        query_url = urllib.parse.quote_plus(f"{artist} {clean_title}")
        url = f"https://karaokenerds.com/Search?query={query_url}&webFilter={scope}"

        response = self.session.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                kn_artist = cols[1].text.strip()
                if is_similar(artist, kn_artist):
                    return True
        return False
