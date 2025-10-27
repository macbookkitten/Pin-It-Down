#!/usr/bin/env python3
# ==============================================
# Pinterest Downloader – Download best-quality image/video from links
# No login required. Supports single or multiple links.
# ==============================================

"""Simple Pinterest downloader with an interactive CLI.

Features:
- No login required
- Single or multiple links
- Tries to pick the best-quality image or video

Notes:
- SSL verification is disabled to avoid certificate issues on some systems.
- Use on trusted networks only.
"""

from __future__ import annotations

import os
import re
import sys
import time
import ssl
import errno
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
DEFAULT_OUTDIR = os.path.join(os.getcwd(), "downloads")
HTML_TIMEOUT = 20
DOWNLOAD_TIMEOUT = 30
READ_CHUNK_SIZE = 128 * 1024
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
VIDEO_EXTS = (".mp4",)
# Disable SSL certificate verification globally for HTTPS requests
ssl._create_default_https_context = ssl._create_unverified_context  # type: ignore[attr-defined]


def banner() -> None:
    """Print the simple banner header."""
    print("=" * 50)
    print(" 🎯 Pin-It-Down - Pinterest Downloader ")
    print("=" * 50 + "\n")


def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist (idempotent)."""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def sanitize_filename(name: str) -> str:
    """Normalize filename by removing illegal characters and collapsing spaces."""
    name = re.sub(r"[\s\t\n\r]+", " ", name).strip()
    # Remove invalid file name characters for macOS/Linux
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    # Collapse repeated underscores
    name = re.sub(r"_+", "_", name)
    return name or "file"


def read_all(resp, chunk_size: int = READ_CHUNK_SIZE) -> bytes:
    """Read entire response into bytes in chunks."""
    data = bytearray()
    while True:
        chunk = resp.read(chunk_size)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def http_get(url: str, timeout: int = HTML_TIMEOUT) -> bytes:
    """Fetch a URL and return its raw bytes (SSL verification disabled)."""
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.pinterest.com/",
        },
    )
    # Always use an unverified SSL context (disables certificate verification)
    with urlopen(
        req, timeout=timeout, context=ssl._create_unverified_context()
    ) as resp:
        return read_all(resp)


def fetch_html(url: str) -> str:
    """Fetch a URL and decode as UTF-8 (replace invalid bytes)."""
    body = http_get(url)
    return body.decode("utf-8", errors="replace")


def split_ext_from_url(url: str) -> Tuple[str, Optional[str]]:
    """Extract base filename and extension (if present) from a URL path."""
    path = urlparse(url).path
    base = os.path.basename(path)
    root, ext = os.path.splitext(base)
    if ext:
        return base, ext.lstrip(".").lower()
    return base or "file", None


def ext_from_content_type(content_type: Optional[str]) -> Optional[str]:
    """Map common Content-Type values to file extensions."""
    if not content_type:
        return None
    ct = content_type.split(";", 1)[0].strip().lower()
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "video/mp4": "mp4",
        "video/quicktime": "mov",
    }
    return mapping.get(ct)


def score_image_url(u: str) -> int:
    """Score image URL by quality hints to sort candidates."""
    score = 0
    if "/originals/" in u:
        score += 10_000
    # Prefer larger declared width like /1200x/ or /736x/
    m = re.search(r"/(\d{2,5})x/", u)
    if m:
        score += int(m.group(1))
    # Prefer jpeg/png over webp/gif
    if u.lower().endswith((".jpg", ".jpeg")):
        score += 50
    elif u.lower().endswith((".png",)):
        score += 25
    return score


def score_video_url(u: str) -> int:
    """Score video URL by quality hints to sort candidates."""
    score = 0
    # Prefer MP4 progressive over HLS playlists
    if u.lower().endswith(".mp4"):
        score += 1000
    # Prefer higher p tags in URL
    m = re.search(r"(\d{3,4})p", u, re.IGNORECASE)
    if m:
        score += int(m.group(1))
    return score


PINIMG_URL_RE = re.compile(r"https?://[a-z0-9\.-]*pinimg\.com[^\s\"'<>\)]+", re.I)


def extract_candidate_urls(html: str) -> Tuple[List[str], List[str]]:
    """Extract candidate image/video URLs from page HTML content."""
    # Grab all pinimg URLs in the document (HTML + embedded JSON)
    all_urls = set(PINIMG_URL_RE.findall(html))

    image_urls = [u for u in all_urls if u.lower().endswith(IMAGE_EXTS)]
    video_urls = [u for u in all_urls if u.lower().endswith(VIDEO_EXTS)]

    # Also look for OpenGraph / Twitter meta tags (name= or property=)
    meta_pattern = re.compile(
        r"<meta[^>]+(?:name|property)=(?:\"|')([^\"']+)(?:\"|')[^>]+content=(?:\"|')([^\"']+)(?:\"|')",
        re.I,
    )
    for m in meta_pattern.finditer(html):
        key = m.group(1).lower()
        val = m.group(2)
        if key.startswith("og:video") and val.lower().endswith(VIDEO_EXTS):
            video_urls.append(val)
        elif (
            key.startswith("og:image") or key.startswith("twitter:image")
        ) and val.lower().endswith(IMAGE_EXTS):
            image_urls.append(val)

    # Deduplicate preserving order
    image_urls = list(dict.fromkeys(image_urls))
    video_urls = list(dict.fromkeys(video_urls))
    return image_urls, video_urls


def pick_best_asset(html: str) -> Tuple[Optional[str], Optional[str]]:
    """Return best image and best video URL candidates from HTML."""
    images, videos = extract_candidate_urls(html)

    best_image = None
    best_video = None

    if images:
        images_sorted = sorted(images, key=score_image_url, reverse=True)
        best_image = images_sorted[0]

    if videos:
        videos_sorted = sorted(videos, key=score_video_url, reverse=True)
        best_video = videos_sorted[0]

    # Prefer video if present, else image
    return best_image, best_video


def derive_pin_id(src_url: str) -> Optional[str]:
    """Try to pull the numeric pin ID from a Pinterest URL path."""
    try:
        path = urlparse(src_url).path.strip("/")
        parts = path.split("/")
        # Pinterest pin pages usually /pin/<ID>/
        for part in parts:
            if part.isdigit() and len(part) >= 8:
                return part
    except Exception:
        pass
    return None


def unique_filepath(directory: str, basename: str) -> str:
    """Return a unique path by suffixing _N if the file exists."""
    root, ext = os.path.splitext(basename)
    candidate = os.path.join(directory, basename)
    i = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{root}_{i}{ext}")
        i += 1
    return candidate


def download_file(
    asset_url: str, out_dir: str, preferred_name: Optional[str] = None
) -> str:
    """Download the asset to out_dir with a sensible filename and extension."""
    ensure_dir(out_dir)
    base_from_url, url_ext = split_ext_from_url(asset_url)

    req = Request(
        asset_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Referer": "https://www.pinterest.com/",
        },
    )
    # Always use an unverified SSL context (disables certificate verification)
    with urlopen(
        req, timeout=DOWNLOAD_TIMEOUT, context=ssl._create_unverified_context()
    ) as resp:
        # Determine final extension from Content-Type if available
        ct = resp.info().get_content_type() if hasattr(resp, "info") else None
        ext_guess = ext_from_content_type(ct) or url_ext or "jpg"

        # Build destination filename
        if preferred_name:
            base_name = sanitize_filename(preferred_name)
            # Replace/append ext_guess
            if not base_name.lower().endswith(f".{ext_guess}"):
                base_name = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", base_name)
                base_name = f"{base_name}.{ext_guess}"
        else:
            base_from_url_s = sanitize_filename(base_from_url)
            base_name = base_from_url_s if base_from_url_s else f"file.{ext_guess}"

        dest_path = unique_filepath(out_dir, base_name)
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(READ_CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)

    return dest_path


def process_single_link(link: str, out_dir: str) -> Tuple[bool, str]:
    """Process one Pinterest page URL and download best asset to out_dir."""
    try:
        print(f"- Fetching page: {link}")
        html = fetch_html(link)
        image_url, video_url = pick_best_asset(html)
        if video_url:
            pin_id = derive_pin_id(link) or "pinterest_video"
            fname = f"pin-{pin_id}.mp4"
            print(f"  Found video: {video_url}")
            path = download_file(video_url, out_dir, preferred_name=fname)
            return True, f"Downloaded video -> {path}"
        if image_url:
            pin_id = derive_pin_id(link) or "pinterest_image"
            # Use extension from URL if present
            _, ext = split_ext_from_url(image_url)
            ext = ext or "jpg"
            fname = f"pin-{pin_id}.{ext}"
            print(f"  Found image: {image_url}")
            path = download_file(image_url, out_dir, preferred_name=fname)
            return True, f"Downloaded image -> {path}"
        return False, "No downloadable asset found on the page."
    except Exception as e:
        return False, f"Error: {e}"


def parse_multi_input(raw: str) -> List[str]:
    """Parse multiple links from text separated by commas, spaces, or newlines."""
    if not raw:
        return []
    cleaned = raw.replace("\r", "\n")
    parts = re.split(r"[\s,]+", cleaned.strip())
    links = [p for p in parts if p]
    # Keep only pinterest-looking links to reduce accidental noise
    links = [l for l in links if "pinterest." in l or "pinimg." in l]
    return links


def interactive_menu() -> None:
    """Run the interactive CLI loop."""
    out_dir = DEFAULT_OUTDIR
    ensure_dir(out_dir)

    while True:
        banner()
        print("Output folder:", out_dir)
        print()
        print("Choose an option:")
        print("  1) Download a single Pinterest link")
        print("  2) Download multiple links (paste list)")
        print("  3) Change output folder")
        print("  4) Exit")
        choice = input("Enter 1-4: ").strip()
        print()

        if choice == "1":
            link = input("Paste Pinterest link: ").strip()
            if not link:
                print("No link provided. Returning to menu...\n")
                continue
            ok, msg = process_single_link(link, out_dir)
            print(msg)
            print()
            input("Press Enter to continue...")
        elif choice == "2":
            print("Paste links separated by newlines, commas, or spaces.")
            print("When finished, press Enter on an empty line.")
            lines: List[str] = []
            while True:
                line = input()
                if not line.strip():
                    break
                lines.append(line)
            raw = "\n".join(lines)
            links = parse_multi_input(raw)
            if not links:
                print("No valid links detected. Returning to menu...\n")
                input("Press Enter to continue...")
                continue
            print(f"Found {len(links)} link(s). Starting downloads...\n")
            success = 0
            for idx, link in enumerate(links, 1):
                print(f"[{idx}/{len(links)}]")
                ok, msg = process_single_link(link, out_dir)
                print(msg)
                print()
                if ok:
                    success += 1
            print(f"Completed: {success}/{len(links)} successful.")
            print()
            input("Press Enter to continue...")
        elif choice == "3":
            new_dir = input("Enter new output folder path: ").strip()
            if new_dir:
                out_dir = os.path.abspath(os.path.expanduser(new_dir))
                try:
                    ensure_dir(out_dir)
                    print(f"Output folder set to: {out_dir}\n")
                except Exception as e:
                    print(f"Failed to set output folder: {e}\n")
            else:
                print("No folder provided.\n")
            input("Press Enter to continue...")
        elif choice == "4":
            print("Goodbye!")
            return
        else:
            print("Invalid choice. Please enter 1-4.\n")
            time.sleep(1)


def main() -> None:
    """Program entry point."""
    interactive_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
