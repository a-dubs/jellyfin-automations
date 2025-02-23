from dataclasses import dataclass
import datetime
from typing import Optional
import requests
import os
from dotenv import load_dotenv
from pprint import pprint, pformat
import json
import re
from pydantic import BaseModel, Field

class SnapshotFilter(BaseModel):
    device_name: str = None
    user_name: str = None
    is_paused: str = None

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

class VideoStreamInfo(BaseModel):
    self_type: str = Field(default="VideoStreamInfo", frozen=True)
    AverageFrameRate: float
    RealFrameRate: float
    ReferenceFrameRate: float

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            AverageFrameRate=data.get("AverageFrameRate"),
            RealFrameRate=data.get("RealFrameRate"),
            ReferenceFrameRate=data.get("ReferenceFrameRate"),
        )

class PlayState(BaseModel):
    self_type: str = Field(default="PlayState", frozen=True)
    PositionTicks: int
    CanSeek: bool
    IsPaused: bool
    IsMuted: bool
    VolumeLevel: Optional[int] = None
    AudioStreamIndex: int
    SubtitleStreamIndex: int
    MediaSourceId: str
    PlayMethod: str

def ticks_to_seconds(ticks: int) -> int:
    # divide by 10,000,000 to convert to seconds
    return ticks // 10000000

def seconds_to_timestamp(seconds: int) -> str:  
    return str(datetime.timedelta(seconds=seconds))

class NowPlayingItem(BaseModel):
    self_type: str = Field(default="NowPlayingItem", frozen=True)
    Name: str
    ServerId: str
    Id: str
    ProviderIds: dict[str, str]  # provider: id
    VideoStreamInfo: VideoStreamInfo
    SeriesName: str
    SeasonName: str
    SeriesId: str
    SeasonId: str
    RunTimeTicks: int
    Path: str

    @classmethod
    def from_dict(cls, data: dict, user_id: str):
        if not data.get("Path"):
            r = requests.get(f"{JELLYFIN_URL}/Items/{data['Id']}", headers={"X-MediaBrowser-Token": JELLYFIN_API_KEY}, params={"UserId": user_id})
            print(r.status_code)
            print(r.raise_for_status())
            item_data = r.json()
            with open('item_data.json', 'w') as f:
                json.dump(item_data, f)
            data["Path"] = item_data["Path"]
        pprint(data)
        return cls(
            Name=data["Name"],
            ServerId=data["ServerId"],
            Id=data["Id"],
            ProviderIds=data["ProviderIds"],
            VideoStreamInfo=VideoStreamInfo.from_dict(
                data.get("VideoStreamInfo", data.get("MediaStreams", [{}])[0])
            ),
            SeriesName=data.get("SeriesName"),
            SeasonName=data.get("SeasonName"),
            SeriesId=data.get("SeriesId"),
            SeasonId=data.get("SeasonId"),
            RunTimeTicks=data.get("RunTimeTicks"),
            Path=data.get("Path"),
        )

class JellyfinPlaybackSnapshot(BaseModel):
    self_type: str = Field(default="JellyfinPlaybackSnapshot", frozen=True)
    PlayState: PlayState
    RemoteEndPoint: str
    PlayableMediaTypes: list[str]
    Id: str
    UserId: str
    UserName: str
    Client: str
    LastActivityDate: str
    LastPlaybackCheckIn: str
    LastPausedDate: str
    DeviceName: str
    NowPlayingItem: NowPlayingItem
    CurrentPlaybackTimeStamp: str 


    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            PlayState=PlayState(**data["PlayState"]),
            RemoteEndPoint=data["RemoteEndPoint"],
            PlayableMediaTypes=data["PlayableMediaTypes"],
            Id=data["Id"],
            UserId=data["UserId"],
            UserName=data["UserName"],
            Client=data["Client"],
            LastActivityDate=data["LastActivityDate"],
            LastPlaybackCheckIn=data["LastPlaybackCheckIn"],
            LastPausedDate=data["LastPausedDate"],
            DeviceName=data["DeviceName"],
            NowPlayingItem=NowPlayingItem.from_dict(data["NowPlayingItem"], data["UserId"]),
            CurrentPlaybackTimeStamp=seconds_to_timestamp(ticks_to_seconds(data["PlayState"]["PositionTicks"]))
        )







# create or read json file to store records in

def update_db(new_snapshot: JellyfinPlaybackSnapshot) -> None:
    db: list[JellyfinPlaybackSnapshot] = []
    try:
        with open('sessions_db.json', 'r') as f:
            json.load(f)
    except Exception as e:
        with open('sessions_db.json', 'w') as f:
            json.dump([], f)
    try:
        with open('sessions_db.json', 'r') as f:
            data: list = json.load(f)
            db = [JellyfinPlaybackSnapshot.from_dict(d) for d in data]
        db.append(new_snapshot)
        with open('sessions_db.json', 'w') as f:
            json.dump(
                [s.model_dump() for s in db],
                f,
                indent=4
            )


    except FileNotFoundError:
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
    snapshot_obj = JellyfinPlaybackSnapshot.from_dict(snapshot)
    for field, value in filter_params.items():
        snapshot_value = get_value_from_dot_notation(snapshot_obj, field)
        if not re.match(value, str(snapshot_value), re.IGNORECASE):
            print(f"Filter mismatch: {field} ({snapshot_value}) does not match {value}")
            return False
        else:
            print(f"Filter match: {field} ({snapshot_value}) matches {value}")
    return True

def save_playback_snapshot(
    filter: SnapshotFilter
) -> Optional[JellyfinPlaybackSnapshot]:
    target_field_re_matches = {}
    if filter.device_name:
        target_field_re_matches["DeviceName"] = filter.device_name
    if filter.user_name:
        target_field_re_matches["UserName"] = filter.user_name
    if filter.is_paused:
        target_field_re_matches["PlayState.IsPaused"] = filter.is_paused

    endpoint = f"{JELLYFIN_URL}/Sessions"
    headers = {"X-MediaBrowser-Token": JELLYFIN_API_KEY}
    params = {
        "ActiveWithinSeconds": 90,   # Adjust as needed
    }

    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code == 200:
        sessions = response.json()
        currently_playing = [s for s in sessions if "NowPlayingItem" in s]
        with open('sessions.json', 'w') as f:
            json.dump(sessions, f)
        if currently_playing:
            for session in currently_playing:
                if is_match(target_field_re_matches, session):
                    if "LastPausedDate" in session:
                        print(f"{session['UserName']} is currently paused at {session['NowPlayingItem']['Name']} ({session['NowPlayingItem']['Path']})")
                    snapshot = JellyfinPlaybackSnapshot.from_dict(session)
                    update_db(snapshot)
                    return snapshot
                
        else:
            print("No active playback sessions found.")
    else:
        print(f"Error: Unable to retrieve sessions (Status Code: {response.status_code})")
    return None

# Main execution
if __name__ == "__main__":
    save_playback_snapshot(
        SnapshotFilter(
            device_name="alec.*macbook|big.*boi.*tv",
            user_name="big bois|alec",
            is_paused="true",
        ),
    )
