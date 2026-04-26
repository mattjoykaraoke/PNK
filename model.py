import os
import sqlite3

class PNKModel:
    def __init__(self):
        self.playlists_map = {}
        self.active_source = "spotify"
        self.loaded_songs = []
        self.playlist_title_for_file = ""
        
        self._setup_cache_db()

    def _setup_cache_db(self):
        """Sets up the SQLite database for caching KaraokeNerds search results."""
        app_dir = os.path.join(os.path.expanduser("~"), ".pnk_app")
        os.makedirs(app_dir, exist_ok=True)
        self.db_path = os.path.join(app_dir, "cache.db")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kn_cache (
                    original_name TEXT PRIMARY KEY,
                    found BOOLEAN,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def check_cache(self, original_name: str):
        """Checks the cache for a specific song. Returns True/False if found in cache, else None."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT found, (timestamp < datetime('now', '-7 days')) AS is_expired 
                    FROM kn_cache WHERE original_name = ?
                """, (original_name,))
                result = cursor.fetchone()
                if result is not None:
                    found = bool(result[0])
                    is_expired = bool(result[1])
                    if found:
                        return True
                    if not found and not is_expired:
                        return False
                    return None
        except Exception as e:
            print(f"Cache read error: {e}")
        return None

    def save_to_cache(self, original_name: str, found: bool):
        """Saves a check result to the SQLite cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO kn_cache (original_name, found)
                    VALUES (?, ?)
                """, (original_name, found))
                conn.commit()
        except Exception as e:
            print(f"Cache write error: {e}")
