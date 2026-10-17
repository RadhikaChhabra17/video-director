#!/usr/bin/env python3
"""
Extracts and decodes the MP4 video from Gemini / Vertex Interactions API response.
Usage:
  python3 decode_video.py response.json [output.mp4]
"""
import sys
import json
import base64
import os
import subprocess

def find_video_data(obj):
    """Recursively search for video base64 data or URI in the JSON response."""
    if isinstance(obj, dict):
        # Case 1: Object with mime_type video/mp4 and data or bytes
        if obj.get("mime_type") == "video/mp4" or obj.get("type") == "video":
            for key in ["data", "bytes", "b64", "content"]:
                if key in obj and isinstance(obj[key], str) and len(obj[key]) > 100:
                    return obj[key]
        # Check standard fields
        for k in ["data", "bytes"]:
            if k in obj and isinstance(obj[k], str) and len(obj[k]) > 500:
                return obj[k]
        for v in obj.values():
            res = find_video_data(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_video_data(item)
            if res:
                return res
    return None

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "response.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "generated_video.mp4"

    if not os.path.exists(input_file):
        print(f"Error: '{input_file}' not found. Please provide a valid JSON file.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading '{input_file}'...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    b64_str = find_video_data(data)
    if not b64_str:
        print("Error: Could not find base64 video data in the response.", file=sys.stderr)
        print("Response keys:", list(data.keys()) if isinstance(data, dict) else "list")
        sys.exit(1)

    print(f"Found base64 video data ({len(b64_str):,} characters). Decoding...")
    video_bytes = base64.b64decode(b64_str)

    with open(output_file, "wb") as f:
        f.write(video_bytes)

    size_mb = len(video_bytes) / (1024 * 1024)
    print(f"Success! Saved video to '{output_file}' ({size_mb:.2f} MB)")

    # Open video automatically on macOS
    if sys.platform == "darwin":
        print(f"Opening '{output_file}' in default player...")
        subprocess.run(["open", output_file])

if __name__ == "__main__":
    main()

