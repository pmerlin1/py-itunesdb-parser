# iTunes Database Parser

Extract music library data from iPod iTunes database files and export to CSV format.

## Simple Usage

**Export entire library:**
```bash
python itunes_db_parser.py
```
→ Creates `ipod_music_library.csv`

**Export specific playlist:**
```bash
python itunes_db_parser.py --playlist "On-The-Go 1"
```
→ Creates `on-the-go_1.csv`

**List available playlists:**
```bash
python itunes_db_parser.py --list-playlists
```

## Requirements

- Python 3.7+
- No external dependencies

## Installation

```bash
git clone https://github.com/pmerlin1/py-itunesdb-parser.git
cd py-itunesdb-parser
```

## Configuration

**Environment variables (optional):**
```bash
export ITUNES_DB_PATH="/path/to/iTunesDB"
export PLAY_COUNTS_PATH="/path/to/Play Counts"
```

**Command line options:**
- `--playlist "Name"` - Export specific playlist
- `--output file.csv` - Custom output filename
- `--itunes-db path` - Custom iTunesDB path
- `--play-counts path` - Custom Play Counts path

## CSV Output

Contains: Artist, Album, Title, Genre, Year, Rating, Play Count

Sorted by: Play count (highest first), then rating, then alphabetically

## iPod File Locations

**Mac/Linux:** `/Volumes/IPOD/iPod_Control/iTunes/`
**Windows:** `F:\iPod_Control\iTunes\`

Files needed:
- `iTunesDB` (required) - Track metadata and playlists
- `Play Counts` (optional) - Actual play statistics

## Examples

```bash
# From mounted iPod
ITUNES_DB_PATH="/Volumes/IPOD/iPod_Control/iTunes/iTunesDB" python itunes_db_parser.py

# Export sleep playlist (often has very high play counts)
python itunes_db_parser.py --playlist "Sleep"

# Skip play counts for faster parsing
python itunes_db_parser.py --play-counts /dev/null
```

## Sample Output

```csv
Artist,Album,Title,Genre,Year,Rating,Play Count
Brian Eno,Apollo,Always Returning,Ambient,1983,5,393
Boards of Canada,Music Has The Right To Children,An Eagle In Your Mind,IDM,1998,5,387
```

## Troubleshooting

- **Database not found:** Check iPod is mounted and path is correct
- **No playlists:** Some iPods only have system playlists
- **No play counts:** File may not exist - use `--play-counts /dev/null` to skip
- **Slow parsing:** Large libraries (10k+ tracks) take 30-60 seconds

## Development

**Install development tools:**
```bash
pip install ruff pre-commit
pre-commit install
```

**Lint code:**
```bash
make lint
make format
```

**Available commands:**
```bash
make help
```

## License

MIT License
