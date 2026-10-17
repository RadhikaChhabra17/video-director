"""
Instagram Saved Collection URL Extractor

Extracts Instagram Reel/Post URLs from:
1. Official Instagram Data Export files (saved_posts.json, saved_saved_media.json, or your_saved_items.html)
2. Raw pasted text or browser console output
3. Can also output an interactive browser console snippet to extract URLs from your saved tab in Chrome/Safari/Edge.
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Set


BROWSER_SNIPPET = """// ============================================================
// 10-SECOND BROWSER EXTRACTOR:
// 1. Open your Instagram Saved Collection in Chrome / Safari / Edge:
//    https://www.instagram.com/<your_username>/saved/
// 2. Press Cmd + Option + J (Mac) or Ctrl + Shift + J (Windows) to open Console.
// 3. Paste the snippet below and press Enter.
// ============================================================

(async () => {
  console.log("Extracting Reel URLs from Saved collection...");
  let lastHeight = 0;
  const urls = new Set();
  
  for (let i = 0; i < 40; i++) {
    document.querySelectorAll('a[href*="/reel/"], a[href*="/p/"]').forEach(a => {
      const cleanUrl = a.href.split('?')[0];
      urls.add(cleanUrl);
    });
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, 1200));
    if (document.body.scrollHeight === lastHeight) break;
    lastHeight = document.body.scrollHeight;
  }
  
  const result = Array.from(urls).join('\\n');
  
  // 1. Download as reels.txt directly
  const blob = new Blob([result], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'reels.txt';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);

  // 2. Also try clipboard if available
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try { await navigator.clipboard.writeText(result); } catch (e) {}
  }
  
  console.log(`✅ Extracted ${urls.size} URLs! Downloaded to reels.txt`);
  alert(`Extracted ${urls.size} Reel URLs!\\n\\n'reels.txt' has been downloaded to your Downloads folder.`);
})();
"""


def extract_urls_from_text(text: str) -> List[str]:
    """Finds all instagram reel and post URLs in any arbitrary text or JSON."""
    pattern = r"https?://(?:www\.)?instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)/?"
    matches = re.finditer(pattern, text)
    seen: Set[str] = set()
    urls: List[str] = []
    
    for match in matches:
        shortcode = match.group(1)
        # Normalize to standard reel link
        url = f"https://www.instagram.com/reel/{shortcode}/"
        if url not in seen:
            seen.add(url)
            urls.append(url)
            
    return urls


def extract_from_file(file_path: Path) -> List[str]:
    """Extracts URLs from an Instagram data export (JSON or HTML) or plain text."""
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    
    # Try parsing as JSON first
    try:
        data = json.loads(content)
        # Search for string values with instagram links
        extracted = []
        
        def recurse(node):
            if isinstance(node, dict):
                for v in node.values():
                    recurse(v)
            elif isinstance(node, list):
                for item in node:
                    recurse(item)
            elif isinstance(node, str):
                extracted.extend(extract_urls_from_text(node))

        recurse(data)
        if extracted:
            # Deduplicate preserving order
            return list(dict.fromkeys(extracted))
    except Exception:
        pass

    # Fallback to regex over the raw text/HTML
    return extract_urls_from_text(content)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage:")
        print("  python tools/extract_saved_reels.py <path_to_saved_posts.json_or_html>")
        print("  python tools/extract_saved_reels.py --snippet  (prints browser console code)")
        print()
        sys.exit(0)

    arg = sys.argv[1]
    if arg == "--snippet":
        print(BROWSER_SNIPPET)
        return

    path = Path(arg)
    if not path.exists():
        print(f"Error: File '{path}' does not exist.")
        sys.exit(1)

    urls = extract_from_file(path)
    if not urls:
        print(f"No Instagram Reel/Post URLs found in {path}.")
        sys.exit(1)

    out_file = Path("saved_reels_urls.txt")
    out_file.write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"Successfully extracted {len(urls)} URLs into {out_file.resolve()}!")
    print(f"To ingest all of them and rebuild patterns:")
    print(f"  uv run python main.py {out_file.name}")


if __name__ == "__main__":
    main()

