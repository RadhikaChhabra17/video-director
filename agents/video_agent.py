from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from corpus.director_schema import DirectorResponseManifest
from tools.omni_video_tool import generate_master_10s_video


class VideoGenerationAgent:
    def __init__(
        self,
        model: Optional[str] = None,
        output_dir: str = "output/renders",
        cache_dir: str = ".cache/renders",
        concurrency: int = 1,
        timeout_s: int = 600,
    ) -> None:
        self.model = model or os.environ.get("VIDEO_MODEL", "gemini-omni-1.1-flash-preview")
        self.output_dir = Path(output_dir)
        self.cache_dir = Path(cache_dir)
        self.timeout_s = timeout_s

    def render_manifest(
        self,
        manifest: DirectorResponseManifest,
        resolution: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        first_frame_path: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> str:
        proj_id = manifest.project_id or "proj_render"
        res = resolution or manifest.resolution or "720p"
        ar = aspect_ratio or manifest.aspect_ratio or "9:16"

        final_video_name = f"{proj_id}_{res}_{ar.replace(':', 'x')}.mp4"
        final_video_path = self.output_dir / final_video_name
        final_video_path.parent.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 65)
        print(f"       VIDEO GENERATION ({self.model.upper()})")
        print("=" * 65)
        print(f"Project ID:    {proj_id}")
        print(f"Title:         {manifest.title}")
        print(f"Model:         {self.model}")
        print(f"Aspect Ratio:  {ar} | Resolution: {res}")
        print("=" * 65)

        return generate_master_10s_video(
            manifest=manifest,
            output_path=str(final_video_path),
            aspect_ratio=ar,
            resolution=res,
            model=self.model,
            timeout_s=self.timeout_s,
            first_frame_path=first_frame_path,
        )
