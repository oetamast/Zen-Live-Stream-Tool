from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class AssetBase(SQLModel):
    type: str
    filename: str
    path: str
    size_bytes: int
    duration_s: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    hash: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status: str = "active"


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    jobs: List["Job"] = Relationship(back_populates="video_asset", sa_relationship_kwargs={"foreign_keys": "Job.video_asset_id"})
    audio_jobs: List["Job"] = Relationship(back_populates="audio_asset", sa_relationship_kwargs={"foreign_keys": "Job.audio_asset_id"})


class DestinationBase(SQLModel):
    name: str
    rtmp_url: str
    stream_key_encrypted: str
    rtmp_mode: str = "rtmp"


class Destination(DestinationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    jobs: List["Job"] = Relationship(back_populates="destination")


class PresetBase(SQLModel):
    name: str
    mode: str = "copy_default"
    video_bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    gop: Optional[int] = None
    preset: Optional[str] = None
    profile: Optional[str] = None
    tune: Optional[str] = None
    scale: Optional[str] = None
    fps: Optional[float] = None
    audio_channels: Optional[int] = None
    audio_rate: Optional[int] = None
    use_safety_cap: bool = True


class Preset(PresetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    jobs: List["Job"] = Relationship(back_populates="preset")


class JobBase(SQLModel):
    name: str
    tier_required: str = "Basic"
    destination_id: int
    video_asset_id: int
    loop_enabled: bool = False
    crossfade_enabled: bool = False
    audio_mode: str = "none"
    audio_asset_id: Optional[int] = None
    auto_recovery: bool = False
    hot_swap_mode: str = "immediate"
    scenes_enabled: bool = False
    scene_overrides_json: Optional[str] = None
    swap_rules_json: Optional[str] = None
    preset_id: Optional[int] = None
    status: str = "draft"
    invalid_reasons: Optional[str] = None


class Job(JobBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    destination: Destination = Relationship(back_populates="jobs")
    video_asset: Asset = Relationship(back_populates="jobs", sa_relationship_kwargs={"foreign_keys": "Job.video_asset_id"})
    audio_asset: Optional[Asset] = Relationship(back_populates="audio_jobs", sa_relationship_kwargs={"foreign_keys": "Job.audio_asset_id"})
    preset: Optional[Preset] = Relationship(back_populates="jobs")
    schedules: List["Schedule"] = Relationship(back_populates="job")
    sessions: List["Session"] = Relationship(back_populates="job")


class ScheduleBase(SQLModel):
    job_id: int
    type: str = "one_time"
    start_at: datetime
    end_at: Optional[datetime] = None
    duration_s: Optional[int] = None
    retry_policy_json: Optional[str] = None
    enabled: bool = True


class Schedule(ScheduleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job: Job = Relationship(back_populates="schedules")
    sessions: List["Session"] = Relationship(back_populates="schedule")


class SessionBase(SQLModel):
    job_id: int
    schedule_id: Optional[int] = None
    trigger: str = "run_now"
    planned_start_at: Optional[datetime] = None
    planned_end_at: Optional[datetime] = None
    actual_start_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    state: str = "queued"
    runner_id: Optional[str] = None
    ffmpeg_pid: Optional[int] = None
    last_heartbeat_at: Optional[datetime] = None
    current_loop_index: Optional[int] = None
    next_loop_eta_s: Optional[int] = None
    stop_reason: Optional[str] = None


class Session(SessionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job: Job = Relationship(back_populates="sessions")
    schedule: Optional[Schedule] = Relationship(back_populates="sessions")
    events: List["Event"] = Relationship(back_populates="session")
    ffmpeg_logs: List["FFmpegLog"] = Relationship(back_populates="session")


class EventBase(SQLModel):
    session_id: int
    level: str
    code: str
    message: str
    ts: datetime = Field(default_factory=datetime.utcnow)


class Event(EventBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session: Session = Relationship(back_populates="events")


class FFmpegLogBase(SQLModel):
    session_id: int
    path: str
    bytes: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None


class FFmpegLog(FFmpegLogBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session: Session = Relationship(back_populates="ffmpeg_logs")


class LicenseStateBase(SQLModel):
    install_id: str
    install_secret_hash: str
    activated_tier: str = "Basic"
    lease_expires_at: Optional[datetime] = None
    last_check_at: Optional[datetime] = None
    grace_started_at: Optional[datetime] = None
    member_license_id: Optional[int] = None


class LicenseState(LicenseStateBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class MemberLicenseBase(SQLModel):
    install_id: str
    install_secret_hash: str
    tier: str = "Basic"
    notes: Optional[str] = None
    active: bool = True
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_check_at: Optional[datetime] = None
    grace_started_at: Optional[datetime] = None


class MemberLicense(MemberLicenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class LicenseActivityBase(SQLModel):
    install_id: str
    action: str
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LicenseActivity(LicenseActivityBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class JobBackupBase(SQLModel):
    job_id: int
    previous_tier: str
    backup_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disabled_copy: bool = True


class JobBackup(JobBackupBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class RunnerLock(SQLModel, table=True):
    lock_id: int = Field(default=1, primary_key=True)
    runner_id: str
    heartbeat_at: datetime = Field(default_factory=datetime.utcnow)
