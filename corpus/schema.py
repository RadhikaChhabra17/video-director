from datetime import datetime
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass
from typing import Literal
from pydantic import BaseModel, Field


class Platform(StrEnum):
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"


class ToneTag(StrEnum):
    COZY = "cozy"
    SLOW = "slow"
    WARM = "warm"
    PLAYFUL = "playful"
    FAST = "fast"
    DEADPAN = "deadpan"
    CHILL = "chill"
    NOSTALGIC = "nostalgic"
    SATISFYING = "satisfying"
    CALM = "calm"
    SUSPENSEFUL = "suspenseful"
    ENERGETIC = "energetic"
    INSPIRATIONAL = "inspirational"
    HUMOROUS = "humorous"
    DRAMATIC = "dramatic"
    EDUCATIONAL = "educational"
    MYSTERIOUS = "mysterious"
    URGENT = "urgent"
    QUIRKY = "quirky"
    RELATABLE = "relatable"
    AESTHETIC = "aesthetic"
    INFORMATIVE = "informative"


class StyleTag(StrEnum):
    FAST = "FAST"
    CINEMATIC = "CINEMATIC"
    IMMERSIVE = "IMMERSIVE"
    FUNNY = "FUNNY"
    EMOTIONAL = "EMOTIONAL"
    EDUCATIONAL = "EDUCATIONAL"
    SUSPENSEFUL = "SUSPENSEFUL"
    RAW = "RAW"
    PREMIUM = "PREMIUM"
    CHAOTIC = "CHAOTIC"
    MINIMAL = "MINIMAL"
    HIGH_ENERGY = "HIGH ENERGY"
    SATISFYING = "SATISFYING"
    ASMR = "ASMR"
    POV = "POV"
    DOCUMENTARY = "DOCUMENTARY"
    STORY_DRIVEN = "STORY-DRIVEN"
    VISUAL_FIRST = "VISUAL-FIRST"
    DIALOGUE_FIRST = "DIALOGUE-FIRST"
    MUSIC_DRIVEN = "MUSIC-DRIVEN"
    SFX_DRIVEN = "SFX-DRIVEN"


class HookType(StrEnum):
    CURIOSITY = "curiosity"
    SECRET = "secret"
    CLIFFHANGER = "cliffhanger"
    QUESTION = "question"
    CALL_OUT = "call_out"
    CONTRARIAN = "contrarian"
    WARNING = "warning"
    MISTAKE = "mistake"
    CONTROVERSIAL = "controversial"
    MYTH_BUST = "myth_bust"
    HOW_TO = "how_to"
    PAIN_POINT = "pain_point"
    LISTICLE = "listicle"
    COUNTDOWN = "countdown"
    STORY = "story"
    POV = "pov"
    RELATABLE = "relatable"
    STATISTIC = "statistic"
    BEFORE_AFTER = "before_after"
    COMPARISON = "comparison"
    SHOCKING_FACT = "shocking_fact"
    PATTERN_INTERRUPT = "pattern_interrupt"
    COLD_OPEN_ACTION = "cold_open_action"
    VISUAL_ACTION = "visual_action"
    CHALLENGE = "challenge"
    TREND_FORMAT = "trend_format"


class CreatorSetup(StrEnum):
    SOLO = "solo"
    DUO = "duo"
    CREW = "crew"


class BeatName(StrEnum):
    HOOK = "hook"
    CONTEXT = "context"
    PROBLEM = "problem"
    DEMO = "demo"
    ESCALATION = "escalation"
    TWIST = "twist"
    PROOF = "proof"
    PAYOFF = "payoff"
    CTA = "cta"
    IDEA = "idea"
    ENGINEERING = "engineering"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EdgeRelation(StrEnum):
    ILLUSTRATES = "illustrates"
    PROOF = "proof"
    ELABORATE = "elaborate"
    CONTRASTS = "contrasts"
    CAUSES = "causes"
    CUTS_TO = "cuts_to"
    REINFORCES = "reinforces"
    FOLLOWS = "follows"
    INTRODUCES = "introduces"
    RESOLVES = "resolves"
    FORESHADOWS = "foreshadows"
    CALLBACK = "callback"
    RECONTEXTUALIZES = "recontextualizes"
    MOTIVATES = "motivates"


class ShotSize(StrEnum):
    EXTREME_CLOSE_UP = "ecu"
    CLOSE_UP = "cu"
    MEDIUM_CLOSE_UP = "mcu"
    MEDIUM = "m"
    MEDIUM_WIDE = "mw"
    WIDE = "w"
    EXTREME_WIDE = "ew"


class TransitionType(StrEnum):
    JUMP_CUT = "jump_cut"
    WHIP_PAN = "whip_pan"
    MATCH_CUT = "match_cut"
    CROSS_DISSOLVE = "cross_dissolve"
    HARD_CUT = "hard_cut"
    ZOOM_TRANSITION = "zoom_transition"
    SPEED_RAMP = "speed_ramp"
    FREEZE_FRAME = "freeze_frame"
    SWIPE = "swipe"
    SPIN = "spin"
    GLITCH = "glitch"
    SMASH_CUT = "smash_cut"
    LIGHT_LEAK = "light_leak"
    MASK_TRANSITION = "mask_transition"
    INVISIBLE_CUT = "invisible_cut"
    FADE_TO_BLACK = "fade_to_black"
    FADE_TO_WHITE = "fade_to_white"


class CameraMovement(StrEnum):
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    ZOOM = "zoom"
    HANDHELD = "handheld"
    TRACKING = "tracking"
    WHIP = "whip"
    DOLLY = "dolly"
    CRANE = "crane"
    AERIAL = "aerial"
    ORBIT = "orbit"


class VocalDelivery(StrEnum):
    CONVERSATIONAL = "conversational"
    EXCITED = "excited"
    DEADPAN = "deadpan"
    URGENT = "urgent"
    WHISPER = "whisper"
    DRAMATIC = "dramatic"
    NARRATIVE = "narrative"
    CASUAL = "casual"
    AUTHORITATIVE = "authoritative"


class VisualFormat(StrEnum):
    TALKING_HEAD = "talking_head"
    B_ROLL = "b_roll"
    SCREEN_RECORDING = "screen_recording"
    PRODUCT_DEMO = "product_demo"
    SKIT = "skit"
    PODCAST_CLIP = "podcast_clip"
    ANIMATION = "animation"
    SPLIT_SCREEN = "split_screen"
    POV = "pov"


class LightingStyle(StrEnum):
    NATURAL = "natural"
    STUDIO = "studio"
    DRAMATIC = "dramatic"
    NEON = "neon"
    DIM = "dim"
    HIGH_KEY = "high_key"
    LOW_KEY = "low_key"


class TextOverlayType(StrEnum):
    KINETIC_CAPTIONS = "kinetic_captions"
    STATIC_CAPTIONS = "static_captions"
    TITLE_CARD = "title_card"
    LOWER_THIRD = "lower_third"
    CALLOUT = "callout"
    STICKERS_EMOJIS = "stickers_emojis"
    NONE = "none"


class MusicPresence(StrEnum):
    DOMINANT = "dominant"
    BACKGROUND = "background"
    DUCKED = "ducked"
    NONE = "none"


class TimeRange(BaseModel):
    start_sec: float
    end_sec: float


class Camera(BaseModel):
    shot_size: ShotSize
    movement: CameraMovement


class SpeakerTelemetry(BaseModel):
    is_speaking: bool = True
    on_camera: bool = True
    speaker_id: str | None = None
    face_expression: str | None = None
    action: str | None = None
    wpm: float | None = Field(default=None, ge=0.0)
    pitch_mean_hz: float | None = Field(default=None, ge=0.0)
    pitch_variation: str | None = None
    energy_level: str | None = None
    vocal_delivery: VocalDelivery | str | None = None
    pause_duration_sec: float | None = Field(default=None, ge=0.0)


class AudioStyle(BaseModel):
    has_voiceover: bool = False
    has_background_music: bool = False
    music_mood: str | None = Field(default=None, description="e.g. upbeat, lo-fi, suspenseful, dramatic")
    music_presence: MusicPresence | str | None = Field(default=None, description="dominant, background, ducked, none")
    sfx_tags: list[str] = Field(default_factory=list, description="Sound effect cues")
    audio_energy: str | None = Field(default=None, description="Overall audio energy level")


class VideoStyle(BaseModel):
    visual_format: VisualFormat | str | None = Field(default=None, description="e.g. talking_head, b_roll, screen_recording, skit")
    lighting: LightingStyle | str | None = Field(default=None, description="e.g. natural, studio, dramatic, neon, dim")
    color_grade: str | None = Field(default=None, description="e.g. warm/golden, neutral/clean, moody/cinematic, vibrant")
    text_overlay_type: TextOverlayType | str | None = Field(default=None, description="kinetic_captions, static_captions, title_card")
    visual_effects: list[str] = Field(default_factory=list, description="VFX cues")
    graphics_and_stickers: list[str] = Field(default_factory=list, description="On-screen visual elements")
    visual_density: str | None = Field(default=None, description="Visual pacing: minimal, balanced, dense/hyper-edited")


class GraphNode(BaseModel):
    event_id: str
    beat_name: BeatName
    hook_type: list[HookType] = Field(default_factory=list)
    timestamp_range: TimeRange
    rel_position: float = Field(ge=0.0, le=1.0)
    description: str
    transcript: str
    ocr_text: str | None = Field(default=None)
    technique_tags: list[str] = Field(default_factory=list)
    camera: Camera | None = None
    speaker_telemetry: SpeakerTelemetry | None = None
    audio_style: AudioStyle | None = None
    video_style: VideoStyle | None = None
    interpretation_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class Transition(BaseModel):
    type: TransitionType
    duration_ms: int = Field(ge=0, default=0)


class GraphEdge(BaseModel):
    edge_id: str
    from_event_id: str
    to_event_id: str
    relationship: EdgeRelation
    transition: Transition | None = None
    pacing: Literal["fast", "medium", "slow"] | None = None


class VideoGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class EngagementMetrics(BaseModel):
    views: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    engagement_rate: float | None = Field(default=None, ge=0.0)

    @property
    def calculated_engagement_rate(self) -> float:
        if self.engagement_rate is not None:
            return self.engagement_rate
        if self.views > 0:
            total_interactions = self.likes + self.comments + (self.shares or 0) + (self.saves or 0)
            return round((total_interactions / self.views) * 100, 2)
        return 0.0


class DerivedFeatures(BaseModel):
    shot_count: int = Field(ge=0, default=0)
    cuts_per_10s: float = Field(ge=0.0, default=0.0)
    has_music: bool = False
    bpm: float | None = None
    wpm: float | None = None
    loopability: float | None = None


class ShortsAnalysis(BaseModel):
    video_id: str
    url: str
    title: str
    channel: str
    platform: Platform
    category: str
    duration_sec: float = Field(ge=0.0)
    posted_at: datetime | None = None
    tone_tags: list[ToneTag] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    creator_setup: CreatorSetup
    aspect_ratio: str
    fps: float | None = None
    engagement: EngagementMetrics
    video_graph: VideoGraph
    derived_features: DerivedFeatures
    virality_score: float = Field(ge=0.0, le=1.0, default=0.0)
