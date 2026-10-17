from __future__ import annotations

import json
import os
import sys
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from agents.director_agent import DirectorAgent
from corpus.director_schema import DirectorResponseManifest
WEB_DIR = BASE_DIR / "web"
MANIFESTS_DIR = BASE_DIR / "corpus" / "director_output"
MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)


def find_manifest_file(filename: str) -> Optional[Path]:
    import urllib.parse
    raw_name = urllib.parse.unquote(filename).strip()
    safe_name = Path(raw_name).name
    if not safe_name:
        return None

    candidates = [safe_name]
    if not safe_name.endswith(".json"):
        candidates.append(f"{safe_name}.json")
    else:
        candidates.append(safe_name[:-5])

    # 1. Root MANIFESTS_DIR
    for c in candidates:
        p = MANIFESTS_DIR / c
        if p.is_file():
            return p

    # 2. Across all session subdirectories
    for c in candidates:
        matches = list(MANIFESTS_DIR.glob(f"*/{c}"))
        if matches and matches[0].is_file():
            return matches[0]

    # 3. Recursive search
    for c in candidates:
        matches = list(MANIFESTS_DIR.rglob(c))
        if matches and matches[0].is_file():
            return matches[0]

    # 4. Search by stem or project_id
    clean_stem = safe_name[:-5] if safe_name.endswith(".json") else safe_name
    for f in MANIFESTS_DIR.rglob("*.json"):
        if f.stem == clean_stem or f.stem.lower() == clean_stem.lower():
            return f
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("project_id") in (clean_stem, safe_name) or data.get("title") in (clean_stem, safe_name):
                return f
        except Exception:
            continue
    return None


class StudioRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def _send_json_response(self, data: dict | list, status_code: int = 200) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.path = "/web/index.html"
            return super().do_GET()

        if parsed.path == "/api/manifests":
            manifests = []
            seen = set()
            for file_path in sorted(MANIFESTS_DIR.rglob("*.json")):
                if file_path.name in seen:
                    continue
                seen.add(file_path.name)
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    manifests.append({
                        "filename": file_path.name,
                        "project_id": data.get("project_id"),
                        "title": data.get("title"),
                        "total_target_duration_sec": data.get("total_target_duration_sec"),
                        "shots_count": len(data.get("shots", [])),
                        "aspect_ratio": data.get("aspect_ratio", "9:16"),
                    })
                except Exception:
                    pass
            self._send_json_response({"manifests": manifests})
            return

        if parsed.path.startswith("/api/manifest/"):
            raw_filename = parsed.path.replace("/api/manifest/", "")
            target_file = find_manifest_file(raw_filename)
            if target_file and target_file.exists():
                try:
                    data = json.loads(target_file.read_text(encoding="utf-8"))
                    self._send_json_response(data)
                    return
                except Exception as e:
                    self._send_json_response({"error": str(e)}, 500)
                    return
            self._send_json_response({"error": "Manifest not found"}, 404)
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        if parsed.path == "/api/direct":
            script = body.get("script", "").strip()
            creative_pitch = body.get("creative_pitch", "").strip()
            target_duration = float(body.get("duration", 10.0))
            category = body.get("category", "travel")
            style_tags = body.get("style_tags", None)

            if not script:
                self._send_json_response({"error": "Script or idea text is required."}, 400)
                return

            full_prompt = script
            if creative_pitch:
                full_prompt = f"{script}\nCreative Direction & Editing Pitch: {creative_pitch}"

            try:
                director = DirectorAgent()
                manifest = director.direct(
                    script_or_idea=full_prompt,
                    target_category=category,
                    target_duration_sec=target_duration,
                    target_style_tags=style_tags,
                    save=True,
                )
                self._send_json_response({
                    "status": "success",
                    "manifest": manifest.model_dump(),
                })
            except Exception as e:
                self._send_json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/api/refine-shot":
            shot_data = body.get("shot")
            instruction = body.get("instruction", "").strip()
            manifest_context = body.get("manifest_context", {})

            if not shot_data or not instruction:
                self._send_json_response({"error": "Both shot and instruction are required"}, 400)
                return

            try:
                from corpus.director_schema import DirectorShotPlan
                from tools.pattern_tools import get_genai_client
                from google.genai import types

                client = get_genai_client()
                prompt = (
                    "You are an expert short-form video director. The user wants to adjust a specific shot in their video manifest.\n"
                    f"Overall Video Title: {manifest_context.get('title', 'Shorts Project')}\n"
                    f"Overall Style: {manifest_context.get('visual_style_anchor', '')}\n\n"
                    f"Current Shot JSON:\n{json.dumps(shot_data, indent=2)}\n\n"
                    f"User Chat Instruction:\n\"{instruction}\"\n\n"
                    "Refine this single shot's visual description, subject action, camera, lighting, speech transcript, duration, or sfx cues according to the instruction.\n"
                    "Respond with the updated shot matching the schema strictly. Do not include markdown or conversational filler."
                )

                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DirectorShotPlan,
                        temperature=0.4,
                    ),
                )
                updated_shot = json.loads(response.text)
                self._send_json_response({
                    "status": "success",
                    "shot": updated_shot,
                    "explanation": f"Updated shot based on: \"{instruction}\""
                })
            except Exception as e:
                self._send_json_response({"error": str(e)}, 500)
            return

        if parsed.path == "/api/save-manifest":
            manifest_dict = body.get("manifest")
            if not manifest_dict:
                self._send_json_response({"error": "No manifest provided"}, 400)
                return

            try:
                validated = DirectorResponseManifest.model_validate(manifest_dict)
                proj_id = validated.project_id or "proj_edited"
                out_file = MANIFESTS_DIR / f"{proj_id}.json"
                out_file.write_text(validated.model_dump_json(indent=2), encoding="utf-8")
                self._send_json_response({
                    "status": "success",
                    "filename": out_file.name,
                    "manifest": validated.model_dump(),
                })
            except Exception as e:
                self._send_json_response({"error": str(e)}, 400)
            return

        self._send_json_response({"error": "Not Found"}, 404)


def run_server(port: int = 8080) -> None:
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, StudioRequestHandler)
    print(f"Studio Server listening at http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(p)
