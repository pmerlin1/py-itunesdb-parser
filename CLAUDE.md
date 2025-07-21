# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an iPod data directory containing iTunes database files and device configuration data from an iPod Classic/Nano. The repository includes binary database files, XML configuration files, and comprehensive documentation for the iTunesDB format specification.

## Key Files and Structure

- `iTunes/iTunesDB` - Primary binary database containing all song metadata, playlists, and iPod content
- `iTunes/iTunesPrefs.plist` - iTunes preferences in XML plist format
- `iTunes/Play Counts` - Track play count and playback statistics
- `Device/SysInfo` - Device model and system information
- `Device/Preferences` - Binary device preferences and settings
- `itunesdb.txt` - Complete technical specification for iTunesDB format (39k+ lines)
- `itunesdb-spec.pdf` - PDF version of iTunes database specification

## iTunesDB File Format

The iTunesDB uses a hierarchical chunk-based format with little-endian encoding:

### Primary Structure
- `mhbd` - Database header (contains version, library ID, language)
- `mhsd` - Dataset containers (tracks=1, playlists=2, podcasts=3, albums=4)
- `mhlt` - Track list container
- `mhit` - Individual track items with metadata
- `mhlp` - Playlist container
- `mhyp` - Individual playlists
- `mhod` - Data objects (strings, smart playlist rules, etc.)

### Key Data Types
- Track metadata: title, artist, album, bitrate, length, play counts
- Playlist data: standard and smart playlists with rules
- Device info: library persistent ID, language settings
- File types: MP3 (0x4d503320), AAC (0x41414320), M4A (0x4D344120), M4P (0x4D345020)

## Database Versions by iTunes Release
- 0x09 = iTunes 4.2
- 0x0c = iTunes 4.71/4.8
- 0x0f = iTunes 6
- 0x13 = iTunes 7.0
- 0x15 = iTunes 7.2
- 0x17 = iTunes 7.3
- 0x19 = iTunes 7.4+

## Working with This Repository

When analyzing iPod data:
- Use `itunesdb.txt` as the authoritative format specification
- Binary files require hex editors or specialized parsers
- All multi-byte integers are little-endian except where noted
- Track IDs are unique 32-bit values used for playlist references
- Database ID (dbid) is a 64-bit value linking tracks across databases
- Play count data is stored separately and synced back to iTunes

## Device Information
- Model: xC297 (iPod Classic/Nano generation)
- FireWire GUID: [REDACTED]
- Owner: [REDACTED]
