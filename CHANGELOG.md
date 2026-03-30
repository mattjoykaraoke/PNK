# Changelog

All notable changes to PNK will be documented in this file.

## [1.1.1] - 2026-03-29

### Added
**Live Status Information:** Displays the total number of songs in the selected playlist and provides a Smart Estimated Time Remaining (ETR) countdown during the scan.

**Smart Output Files:** Missing tracks are now saved to dynamically named text files based on the playlist name (e.g., missing_Songs_To_Sing.txt) to prevent overwriting results from different playlists.

### Changed
**Spotify Permissions:** Expanded the Spotify authentication scopes (added playlist-read-collaborative and playlist-read-public) to ensure collaborative, shared, and public playlists can be fully read without 403 Forbidden errors.

### Fixed
**Empty Playlist Bug:** Resolved a critical issue where some playlists falsely reported "No songs found" by overhauling the track extraction logic to aggressively capture nested track items regardless of their specific type formatting.

**UI Cutoff:** Widened the Search Scope dropdown to prevent the "Community Only" text from being cut off on high-DPI Windows displays.

## [1.1.0] - 2026-03-29

### Added
- **Choose Search Options:** You can now choose to search Everything, Web Only, or Community only, like on the website.

## [1.0.0] - 2026-03-29

### Added
- **Initial Release**
