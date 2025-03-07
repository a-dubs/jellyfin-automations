import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional


class SnapshotFilter(BaseModel):
    device_name: str = None
    user_name: str = None
    is_paused: str = None


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


class NowPlayingItem(BaseModel):
    self_type: str = Field(default="NowPlayingItem", frozen=True)
    Name: str
    ServerId: str
    Id: str
    ProviderIds: dict[str, str]
    VideoStreamInfo: VideoStreamInfo
    SeriesName: Optional[str] = None
    SeasonName: Optional[str] = None
    SeriesId: Optional[str] = None
    SeasonId: Optional[str] = None
    RunTimeTicks: int
    Path: str

    @classmethod
    def from_dict(cls, data: dict, user_id: str):
        # if not data.get("Path"):
        #     r = requests.get(f"{JELLYFIN_URL}/Items/{data['Id']}", headers={"X-MediaBrowser-Token": JELLYFIN_API_KEY}, params={"UserId": user_id})
        #     print(r.status_code)
        #     print(r.raise_for_status())
        #     item_data = r.json()
        #     with open('item_data.json', 'w') as f:
        #         json.dump(item_data, f)
        #     data["Path"] = item_data["Path"]
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


def ticks_to_seconds(ticks: int) -> int:
    # divide by 10,000,000 to convert to seconds
    return ticks // 10000000


def seconds_to_timestamp(seconds: int) -> str:  
    return str(datetime.timedelta(seconds=seconds))


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
    LastPausedDate: Optional[str] = None
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
            LastPausedDate=data.get("LastPausedDate"),
            DeviceName=data["DeviceName"],
            NowPlayingItem=NowPlayingItem.from_dict(data["NowPlayingItem"], data["UserId"]),
            CurrentPlaybackTimeStamp=seconds_to_timestamp(ticks_to_seconds(data["PlayState"]["PositionTicks"]))
        )

class Item(BaseModel):
    type: str = "Unknown"
    name: str
    imdb_id: Optional[str]

    @property
    def title(self) -> str:
        return self.name

class ShowItem(Item):
    type: str = "Show"
    series_name: str
    season_name: str
    episode_number: int

    @property
    def title(self) -> str:
        return f"{self.series_name} - {self.season_name} - {self.episode_number} - {self.name}"

class MovieItem(Item):
    type: str = "Movie"

def item_from_playback_session(data: dict) -> Optional[ShowItem | MovieItem]:
    if "NowPlayingItem" not in data:
        return None
    if _is_tv_show(data):
        return ShowItem(
            name=data["NowPlayingItem"]["Name"],
            imdb_id=data["NowPlayingItem"]["ProviderIds"].get("Imdb"),
            series_name=data["NowPlayingItem"]["SeriesName"],
            season_name=data["NowPlayingItem"]["SeasonName"],
            episode_number=data["NowPlayingItem"]["IndexNumber"],
        )
    else:
        return MovieItem(
            name=data["NowPlayingItem"]["Name"],
            imdb_id=data["NowPlayingItem"]["ProviderIds"].get("Imdb"),
        )

def _is_tv_show(data: dict) -> bool:
    return data.get("NowPlayingItem", {}).get("SeasonName") is not None

# def _generate_media_title(data: dict) -> str:
#     if _is_tv_show(data):
#         show_name = data["NowPlayingItem"]["SeriesName"]
#         season_name = data["NowPlayingItem"]["SeasonName"]
#         episode_number = data["NowPlayingItem"]["IndexNumber"]
#         episode_name = data["NowPlayingItem"]["Name"]
#         return f"{show_name} - {season_name} - {episode_number} - {episode_name}"
#     else:
#         return data["NowPlayingItem"]["Name"]

# model representing active playback session summary
class PlaybackSessionSummary(BaseModel):
    device_name: str
    user_name: str
    is_paused: bool
    playing_item: ShowItem | MovieItem
    playback_timestamp: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            device_name=data["DeviceName"],
            user_name=data["UserName"],
            is_paused=data["PlayState"]["IsPaused"],
            playing_item=item_from_playback_session(data),
            playback_timestamp=seconds_to_timestamp(
                ticks_to_seconds(
                    data["PlayState"]["PositionTicks"],
                ),
            ),
        )


class SnapshotSummary(BaseModel):
    datetime_recorded: str
    playback_timestamp: str
    title: str

    @classmethod
    def from_snapshot(cls, snapshot: JellyfinPlaybackSnapshot):
        title = (
            f"{snapshot.NowPlayingItem.SeriesName} - "
            f"{snapshot.NowPlayingItem.SeasonName} - "
            f"{snapshot.NowPlayingItem.Name}"
        )
        return cls(
            datetime_recorded=snapshot.LastActivityDate,
            playback_timestamp=snapshot.CurrentPlaybackTimeStamp,
            title=title,
        )