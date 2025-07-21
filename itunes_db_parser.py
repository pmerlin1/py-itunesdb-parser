#!/usr/bin/env python3
"""
iTunes Database Parser

Extract music library data from iPod iTunes database files and export to CSV.
Supports full library export or specific playlist extraction with play count data.

Usage:
    python itunes_db_parser.py [options]

Environment Variables:
    ITUNES_DB_PATH     - Path to iTunesDB file (default: ./iTunes/iTunesDB)
    PLAY_COUNTS_PATH   - Path to Play Counts file (default: ./iTunes/Play Counts)
    OUTPUT_DIR         - Output directory for CSV files (default: .)

Examples:
    # Export full library
    python itunes_db_parser.py

    # Export specific playlist
    python itunes_db_parser.py --playlist "My Top Rated"

    # Custom paths
    ITUNES_DB_PATH=/path/to/iTunesDB python itunes_db_parser.py
"""

import argparse
import csv
import os
import struct
import sys
from typing import Dict, List, Tuple


class iTunesDBParser:
    def __init__(self, db_path: str, play_counts_path: str = None):
        self.db_path = db_path
        self.play_counts_path = play_counts_path
        self.tracks = {}  # track_id -> track_info
        self.tracks_by_index = {}  # track_index -> track_id (for playlist references)
        self.playlists = {}  # playlist_name -> [track_ids]
        self.track_play_counts = []  # List of play counts by track position

    def parse_string_mhod(self, data: bytes, offset: int) -> Tuple[str, int]:
        """Parse mhod string with correct iTunes format"""
        try:
            # mhod header: magic(4) + header_len(4) + total_len(4) + type(4) + ...
            magic, header_len, total_len, mhod_type = struct.unpack(
                "<4sIII", data[offset : offset + 16]
            )

            if magic != b"mhod":
                return "", offset + total_len

            # String data starts after mhod header
            str_section_start = offset + header_len
            str_section_len = total_len - header_len

            if str_section_start + str_section_len > len(data):
                return "", offset + total_len

            # iTunes string section has its own header:
            # unk1(4) + str_len(4) + unk2(4) + unk3(4) + actual_string
            if str_section_len < 16:
                return "", offset + total_len

            unk1, str_len, unk2, unk3 = struct.unpack(
                "<IIII", data[str_section_start : str_section_start + 16]
            )

            actual_str_start = str_section_start + 16
            actual_str_data = data[actual_str_start : actual_str_start + str_len]

            # Decode UTF-16 LE
            text = actual_str_data.decode("utf-16le", errors="ignore").rstrip("\x00")

            return text, offset + total_len

        except Exception:
            return "", offset + total_len if total_len else offset + 24

    def parse_play_counts(self) -> List[Dict]:
        """Parse the Play Counts file to get play statistics"""
        track_play_counts = []

        if not self.play_counts_path or not os.path.exists(self.play_counts_path):
            print("Play Counts file not found - play count data will be 0")
            return track_play_counts

        try:
            with open(self.play_counts_path, "rb") as f:
                data = f.read()

            if len(data) < 16:
                return track_play_counts

            # Play Counts header: magic(4) + header_len(4) + entry_len(4) + num_entries(4)
            magic, header_len, entry_len, num_entries = struct.unpack(
                "<4sIII", data[0:16]
            )

            if magic != b"mhdp":
                print("Invalid Play Counts file format")
                return track_play_counts

            print(f"Found {num_entries} play count entries")

            entry_offset = header_len
            for _ in range(num_entries):
                if entry_offset + entry_len > len(data):
                    break

                # Each entry: play_count(4) + last_played(4) + bookmark(4) + [extra fields]
                play_count, last_played, bookmark = struct.unpack(
                    "<III", data[entry_offset : entry_offset + 12]
                )

                track_play_counts.append(
                    {
                        "play_count": play_count,
                        "last_played": last_played,
                        "bookmark": bookmark,
                    }
                )

                entry_offset += entry_len

        except Exception as e:
            print(f"Error parsing play counts: {e}")

        return track_play_counts

    def parse_track_list(self, data: bytes, offset: int) -> int:
        """Parse mhlt track list"""
        # mhlt header
        magic, mhlt_header_len, num_tracks = struct.unpack(
            "<4sII", data[offset : offset + 12]
        )
        print(f"Found {num_tracks} tracks")

        track_offset = offset + mhlt_header_len

        for i in range(num_tracks):
            if track_offset + 20 >= len(data):
                break

            try:
                # Parse mhit header
                magic, header_len, total_len, num_mhods, track_id = struct.unpack(
                    "<4sIIII", data[track_offset : track_offset + 20]
                )

                if magic != b"mhit":
                    track_offset += total_len
                    continue

                # Extract rating from mhit header (offset 31, 1 byte)
                rating = 0
                if header_len > 31:
                    rating = (
                        struct.unpack(
                            "<B", data[track_offset + 31 : track_offset + 32]
                        )[0]
                        // 20
                    )

                # Extract other metadata from header
                track_info = {
                    "id": track_id,
                    "rating": rating,
                    "title": "",
                    "artist": "",
                    "album": "",
                    "genre": "",
                    "play_count": 0,
                }

                if header_len >= 60:
                    (
                        size,
                        length,
                        track_num,
                        total_tracks,
                        year,
                        bitrate,
                    ) = struct.unpack(
                        "<IIIIII", data[track_offset + 36 : track_offset + 60]
                    )
                    track_info.update({"year": year})

                # Extract dbid (64-bit value at offset 112 in newer formats)
                dbid = None
                if header_len >= 120:
                    dbid = struct.unpack(
                        "<Q", data[track_offset + 112 : track_offset + 120]
                    )[0]

                # Add play count data by track position (index in the database)
                if i < len(self.track_play_counts):
                    track_info["play_count"] = self.track_play_counts[i]["play_count"]

                # Parse mhod strings
                mhod_offset = track_offset + header_len

                for _ in range(num_mhods):
                    if (
                        mhod_offset >= track_offset + total_len
                        or mhod_offset + 16 > len(data)
                    ):
                        break

                    mhod_type = struct.unpack(
                        "<I", data[mhod_offset + 12 : mhod_offset + 16]
                    )[0]

                    if mhod_type == 1:  # Title
                        text, mhod_offset = self.parse_string_mhod(data, mhod_offset)
                        track_info["title"] = text
                    elif mhod_type == 3:  # Album
                        text, mhod_offset = self.parse_string_mhod(data, mhod_offset)
                        track_info["album"] = text
                    elif mhod_type == 4:  # Artist
                        text, mhod_offset = self.parse_string_mhod(data, mhod_offset)
                        track_info["artist"] = text
                    elif mhod_type == 5:  # Genre
                        text, mhod_offset = self.parse_string_mhod(data, mhod_offset)
                        track_info["genre"] = text
                    else:
                        # Skip other mhod types
                        mhod_total_len = struct.unpack(
                            "<I", data[mhod_offset + 8 : mhod_offset + 12]
                        )[0]
                        mhod_offset += mhod_total_len

                self.tracks[track_id] = track_info
                # Store track by its position in the database (0-based, but playlists might be 1-based)
                self.tracks_by_index[i] = track_id
                self.tracks_by_index[i + 1] = track_id  # Also store 1-based
                track_offset += total_len

                # Progress indicator
                if i % 2000 == 0 and i > 0:
                    print(f"Processed {i}/{num_tracks} tracks...")

            except Exception as e:
                print(f"Error parsing track {i}: {e}")
                track_offset += total_len if "total_len" in locals() else 100
                continue

        return track_offset

    def parse_playlist_list(self, data: bytes, offset: int) -> int:
        """Parse mhlp playlist list"""
        # mhlp header
        magic, header_len, num_playlists = struct.unpack(
            "<4sII", data[offset : offset + 12]
        )
        print(f"Found {num_playlists} playlists")

        playlist_offset = offset + header_len

        for i in range(num_playlists):
            if playlist_offset + 24 > len(data):
                break

            try:
                # mhyp header
                magic, header_len, total_len, num_mhods, num_mhips = struct.unpack(
                    "<4sIIII", data[playlist_offset : playlist_offset + 20]
                )

                if magic != b"mhyp":
                    playlist_offset += total_len
                    continue

                playlist_name = f"Playlist_{i}"
                track_ids = []

                # Parse mhods for playlist name
                mhod_offset = playlist_offset + header_len

                for _ in range(min(num_mhods, 20)):  # Limit to prevent runaway
                    if (
                        mhod_offset + 16 > len(data)
                        or mhod_offset >= playlist_offset + total_len
                    ):
                        break

                    try:
                        (
                            mhod_magic,
                            mhod_header_len,
                            mhod_total_len,
                            mhod_type,
                        ) = struct.unpack(
                            "<4sIII", data[mhod_offset : mhod_offset + 16]
                        )

                        if mhod_magic == b"mhod" and mhod_type == 1:  # Playlist name
                            name, _ = self.parse_string_mhod(data, mhod_offset)
                            if name and name.strip():
                                playlist_name = name.strip()
                                break

                        mhod_offset += mhod_total_len
                    except Exception:
                        break

                # Calculate where mhips start (after all mhods)
                mhips_start_offset = playlist_offset + header_len
                for _ in range(num_mhods):
                    if (
                        mhips_start_offset + 16 > len(data)
                        or mhips_start_offset >= playlist_offset + total_len
                    ):
                        break
                    try:
                        (
                            mhod_magic,
                            mhod_header_len,
                            mhod_total_len,
                            mhod_type,
                        ) = struct.unpack(
                            "<4sIII", data[mhips_start_offset : mhips_start_offset + 16]
                        )
                        if mhod_magic == b"mhod":
                            mhips_start_offset += mhod_total_len
                        else:
                            break
                    except Exception:
                        break

                # Parse mhips for track references
                mhip_offset = mhips_start_offset
                for _ in range(num_mhips):
                    if (
                        mhip_offset + 16 > len(data)
                        or mhip_offset >= playlist_offset + total_len
                    ):
                        break

                    try:
                        mhip_magic, mhip_header_len, mhip_total_len = struct.unpack(
                            "<4sII", data[mhip_offset : mhip_offset + 12]
                        )

                        if mhip_magic == b"mhip" and mhip_header_len >= 28:
                            # Track ID is at offset +24 according to the spec
                            track_id = struct.unpack(
                                "<I", data[mhip_offset + 24 : mhip_offset + 28]
                            )[0]
                            # Use track ID directly
                            if track_id in self.tracks:
                                track_ids.append(track_id)

                        mhip_offset += mhip_total_len
                    except Exception:
                        break

                # Add playlist (only if it has tracks or is a known empty playlist)
                if track_ids or any(
                    name in playlist_name.lower()
                    for name in ["podcasts", "on-the-go", "otg"]
                ):
                    self.playlists[playlist_name] = track_ids

                playlist_offset += total_len

            except Exception as e:
                print(f"Error parsing playlist {i}: {e}")
                playlist_offset += total_len if "total_len" in locals() else 100
                continue

        return playlist_offset

    def parse(self):
        """Parse the iTunesDB file"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"iTunes database not found: {self.db_path}")

        # Parse play counts first
        print("Parsing play counts...")
        self.track_play_counts = self.parse_play_counts()

        print("Parsing iTunes database...")

        with open(self.db_path, "rb") as f:
            data = f.read()

        # Parse mhbd header
        magic, header_len, total_len, unk1, version, num_children = struct.unpack(
            "<4sIIIII", data[0:24]
        )
        print(f"Database version: 0x{version:02x}, Children: {num_children}")

        # Find datasets
        offset = header_len
        for _ in range(num_children):
            if offset + 16 > len(data):
                break

            magic, hdr_len, total_len, ds_type = struct.unpack(
                "<4sIII", data[offset : offset + 16]
            )

            if ds_type == 1:  # Track list
                # Skip to mhlt
                mhlt_offset = offset + hdr_len
                self.parse_track_list(data, mhlt_offset)
            elif ds_type == 2:  # Playlist list
                # Skip to mhlp
                mhlp_offset = offset + hdr_len
                self.parse_playlist_list(data, mhlp_offset)

            offset += total_len

    def export_to_csv(self, output_path: str, playlist_name: str = None):
        """Export tracks to CSV"""

        if playlist_name:
            if playlist_name not in self.playlists:
                available = list(self.playlists.keys())
                raise ValueError(
                    f"Playlist '{playlist_name}' not found. Available playlists: {available}"
                )

            track_ids = self.playlists[playlist_name]
            tracks_to_export = [
                self.tracks[tid] for tid in track_ids if tid in self.tracks
            ]
            print(
                f"Exporting {len(tracks_to_export)} tracks from playlist '{playlist_name}'"
            )
        else:
            tracks_to_export = list(self.tracks.values())
            print(f"Exporting {len(tracks_to_export)} tracks from full library")

        # Sort by play count (highest first), then rating, then artist/album
        tracks_to_export.sort(
            key=lambda t: (
                -t.get("play_count", 0),
                -t.get("rating", 0),
                t.get("artist", ""),
                t.get("album", ""),
            )
        )

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                ["Artist", "Album", "Title", "Genre", "Year", "Rating", "Play Count"]
            )

            for track in tracks_to_export:
                writer.writerow(
                    [
                        track.get("artist", ""),
                        track.get("album", ""),
                        track.get("title", ""),
                        track.get("genre", ""),
                        track.get("year", ""),
                        track.get("rating", ""),
                        track.get("play_count", ""),
                    ]
                )


def main():
    parser = argparse.ArgumentParser(
        description="Extract music library data from iPod iTunes database files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  ITUNES_DB_PATH     Path to iTunesDB file (default: ./iTunes/iTunesDB)
  PLAY_COUNTS_PATH   Path to Play Counts file (default: ./iTunes/Play Counts)
  OUTPUT_DIR         Output directory for CSV files (default: .)

Examples:
  %(prog)s
  %(prog)s --playlist "My Top Rated"
  %(prog)s --list-playlists
  %(prog)s --output /path/to/output.csv
        """,
    )

    parser.add_argument(
        "--playlist", "-p", help="Export specific playlist instead of full library"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output CSV file path (default: ipod_music_library.csv or playlist_name.csv)",
    )
    parser.add_argument(
        "--list-playlists",
        "-l",
        action="store_true",
        help="List all available playlists and exit",
    )
    parser.add_argument(
        "--itunes-db", help="Path to iTunesDB file (overrides ITUNES_DB_PATH)"
    )
    parser.add_argument(
        "--play-counts", help="Path to Play Counts file (overrides PLAY_COUNTS_PATH)"
    )

    args = parser.parse_args()

    # Get file paths from environment variables or arguments
    itunes_db_path = args.itunes_db or os.getenv("ITUNES_DB_PATH", "./iTunes/iTunesDB")
    play_counts_path = args.play_counts or os.getenv(
        "PLAY_COUNTS_PATH", "./iTunes/Play Counts"
    )
    output_dir = os.getenv("OUTPUT_DIR", ".")

    try:
        # Create parser and parse database
        db_parser = iTunesDBParser(itunes_db_path, play_counts_path)
        db_parser.parse()

        # List playlists if requested
        if args.list_playlists:
            print(f"\\nFound {len(db_parser.playlists)} playlists:")
            for name, tracks in db_parser.playlists.items():
                print(f"  - {name} ({len(tracks)} tracks)")
            return

        # Determine output filename
        if args.output:
            output_path = args.output
        elif args.playlist:
            # Sanitize playlist name for filename
            safe_name = "".join(
                c for c in args.playlist if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_name = safe_name.replace(" ", "_").lower()
            output_path = os.path.join(output_dir, f"{safe_name}.csv")
        else:
            output_path = os.path.join(output_dir, "ipod_music_library.csv")

        # Export to CSV
        db_parser.export_to_csv(output_path, args.playlist)
        print(f"\\nExported to: {output_path}")

        # Show summary statistics
        played_tracks = [
            t for t in db_parser.tracks.values() if t.get("play_count", 0) > 0
        ]
        high_rated = [t for t in db_parser.tracks.values() if t.get("rating", 0) >= 4]

        print("\\nSummary:")
        print(f"  Total tracks: {len(db_parser.tracks)}")
        print(f"  Tracks with play counts: {len(played_tracks)}")
        print(f"  Highly rated tracks (4+ stars): {len(high_rated)}")
        print(f"  Total playlists: {len(db_parser.playlists)}")

        if args.playlist:
            playlist_tracks = [
                db_parser.tracks[tid]
                for tid in db_parser.playlists[args.playlist]
                if tid in db_parser.tracks
            ]
            total_plays = sum(t.get("play_count", 0) for t in playlist_tracks)
            print(
                f"  Playlist '{args.playlist}': {len(playlist_tracks)} tracks, {total_plays} total plays"
            )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
