import datetime
from pprint import pprint
from typing import Optional
import requests
import os
from dotenv import load_dotenv
import json
import re
from logging_setup import get_logger
from models import SnapshotFilter, SnapshotSummary, VideoStreamInfo, PlayState, NowPlayingItem, JellyfinPlaybackSnapshot

logger = get_logger('playback_snapshotting')

"""
        "PlayState": {
            "PositionTicks": 3000910000,
            "CanSeek": true,
            "IsPaused": true,
            "IsMuted": false,
            "VolumeLevel": 82,
            "AudioStreamIndex": 1,
            "SubtitleStreamIndex": -1,
            "MediaSourceId": "b67f1b7fdf783febee0a45b7dca2efdb",
            "PlayMethod": "DirectPlay",
        },
        "RemoteEndPoint": "172.21.0.3",
        "PlayableMediaTypes": [
            "Audio",
            "Video"
        ],
        "Id": "1c0071e3fa83989a9ddb264af0a23e58",
        "UserId": "f5be1b729aac4ad3a5eea0264d12a524",
        "UserName": "Big Bois",
        "Client": "Jellyfin Media Player",
        "LastActivityDate": "2025-02-06T04:16:24.3261024Z",
        "LastPlaybackCheckIn": "2025-02-06T04:16:24.3261025Z",
        "LastPausedDate": "2025-02-06T04:16:03.3489325Z",
        "DeviceName": "Alec\u2019s MacBook Pro",
        "NowPlayingItem": {
            "Name": "When It Rains, It Pours",
            "ServerId": "7bc43eb3bf2c4266980f3e30ab4d8fa4",
            "Id": "b67f1b7fdf783febee0a45b7dca2efdb",
            "ProviderIds": {
                "Tvdb": "2832681",
                "Imdb": "tt1635814",
                "TvRage": "1064979918"
            },
            "MediaStreams": [
                {
                "AverageFrameRate": 23.976025,  # optional
                "RealFrameRate": 23.976025,  # optional
                "ReferenceFrameRate": 23.976025,  # optional
                "type": "Video",
                }
            ]
"""

DB_PATH = 'snapshots_db.json'

def filter_out_duplicate_snapshots(snapshots: list[JellyfinPlaybackSnapshot]) -> list[JellyfinPlaybackSnapshot]:
    logger.info("Filtering out duplicate snapshots")
    filtered_snapshots = []
    for snapshot in snapshots:
        if snapshot not in filtered_snapshots:
            filtered_snapshots.append(snapshot)
    return filtered_snapshots

# create or read json file to store records in
def update_db(new_snapshot: JellyfinPlaybackSnapshot) -> None:
    logger.info("Updating database with new snapshot")
    db: list[JellyfinPlaybackSnapshot] = []
    # create db file if it doesn't exist
    try:
        with open(DB_PATH, 'r') as f:
            json.load(f)
    except Exception as e:
        logger.warning(f"Error reading {DB_PATH}: {e}")
        with open(DB_PATH, 'w') as f:
            json.dump([], f)
    # read in db file
    try:
        with open(DB_PATH, 'r') as f:
            data: list = json.load(f)
            db = [JellyfinPlaybackSnapshot.from_dict(d) for d in data]
            db = filter_out_duplicate_snapshots(db)
        db.append(new_snapshot)
        with open(DB_PATH, 'w') as f:
            json.dump(
                [s.model_dump() for s in db],
                f,
                indent=4
            )
        logger.info("Database updated successfully")
    except FileNotFoundError:
        logger.error(f"{DB_PATH} not found")
        return []

# Load environment variables from .env
load_dotenv()

# Get Jellyfin server URL and API key from .env
JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")

if not JELLYFIN_API_KEY or not JELLYFIN_URL:
    raise Exception("Error: API key or URL is missing. Please check your .env file.")

def get_value_from_dot_notation(obj: dict, field: str) -> any:
    parts = field.split(".")
    for part in parts:
        obj = getattr(obj, part)
    return obj

def is_match(filter_params: dict, snapshot: dict) -> bool:
    logger.debug(f"Checking if snapshot matches filter: {filter_params}")
    snapshot_obj = JellyfinPlaybackSnapshot.from_dict(snapshot)
    for field, value in filter_params.items():
        snapshot_value = get_value_from_dot_notation(snapshot_obj, field)
        if not re.match(value, str(snapshot_value), re.IGNORECASE):
            logger.debug(f"Filter mismatch: {field} ({snapshot_value}) does not match {value}")
            return False
        else:
            logger.debug(f"Filter match: {field} ({snapshot_value}) matches {value}")
    return True

def fetch_sessions() -> list[dict]:
    endpoint = f"{JELLYFIN_URL}/Sessions"
    headers = {"X-MediaBrowser-Token": JELLYFIN_API_KEY}
    params = {
        "ActiveWithinSeconds": 90,   # Adjust as needed
    }

    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error: Unable to retrieve sessions (Status Code: {response.status_code})")
        return []

from models import PlaybackSessionSummary

def get_playback_session_summaries() -> list[PlaybackSessionSummary]:
    sessions = fetch_sessions()
    summaries = []
    for session in sessions:
        if not "NowPlayingItem" in session:
            continue
        try:
            summary = PlaybackSessionSummary.from_dict(session)
        except Exception as e:
            logger.debug(f"session data: {session}")
            logger.warning(f"Error creating PlaybackSessionSummary: {e}")
            continue
        summaries.append(summary)
    return summaries


def read_in_snapshots_from_db_as_summaries() -> list[SnapshotSummary]:
    logger.info("Reading in snapshots from database")
    try:
        with open(DB_PATH, 'r') as f:
            data = json.load(f)
            snapshots = [JellyfinPlaybackSnapshot.from_dict(d) for d in data]
    except FileNotFoundError:
        logger.error(f"{DB_PATH} not found")
        return []
    except Exception as e:
        logger.error(f"Error reading {DB_PATH}: {e}")
        return []
    
    summaries = []
    for snapshot in snapshots:
        try:
            summaries.append(SnapshotSummary.from_snapshot(snapshot))
        except Exception as e:
            logger.warning(f"Error creating SnapshotSummary: {e}")
            continue

    return summaries


def save_playback_snapshot(
    filter: SnapshotFilter, dry_run: bool = False
) -> Optional[JellyfinPlaybackSnapshot]:
    logger.info(f"Saving playback snapshot with filter: {filter} and dry_run: {dry_run}")
    target_field_re_matches = {}
    if filter.device_name:
        target_field_re_matches["DeviceName"] = filter.device_name
    if filter.user_name:
        target_field_re_matches["UserName"] = filter.user_name
    if filter.is_paused:
        target_field_re_matches["PlayState.IsPaused"] = filter.is_paused

    sessions = fetch_sessions()

    currently_playing = [s for s in sessions if "NowPlayingItem" in s]
    with open('sessions.json', 'w') as f:
        json.dump(sessions, f)
    if currently_playing:
        for session in currently_playing:
            if is_match(target_field_re_matches, session):
                if "LastPausedDate" in session:
                    logger.info(f"{session['UserName']} is currently paused at {session['NowPlayingItem']['Name']} ({session['NowPlayingItem']['Path']})")
                snapshot = JellyfinPlaybackSnapshot.from_dict(session)
                if not dry_run:
                    update_db(snapshot)
                return snapshot
    else:
        logger.info("No active playback sessions found.")
    return None

# Main execution
if __name__ == "__main__":
    logger.info("Starting main execution")
    # save_playback_snapshot(
    #     SnapshotFilter(
    #         device_name="alec.*macbook|big.*boi.*tv",
    #         user_name="big bois|alec",
    #         is_paused="true",
    #     ),
    # )
    r = read_in_snapshots_from_db_as_summaries()
    for s in r:
        pprint(s.model_dump())
