"""Save a signet's Open Graph image for the Pages CMS vignette action."""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SIGNETS = ROOT / "content/signets"
IMAGES = ROOT / "content/images"
UA = "Mozilla/5.0 (compatible; glane/1.0; +https://glane.ludique.dev)"


class ImageMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.src = None

    def handle_starttag(self, tag, attrs):
        if tag != "meta" or self.src:
            return
        attrs = dict(attrs)
        if attrs.get("property") in ("og:image", "og:image:url") or attrs.get("name") == "twitter:image":
            self.src = attrs.get("content")


def get(url, limit):
    with urlopen(Request(quote(url, safe=":/?&=#%+@"), headers={"User-Agent": UA}), timeout=10) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("image or page exceeds size limit")
        return response.geturl(), data


def extension(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"GIF8"):
        return "gif"
    return None


def fetch_image(url):
    page_url, html = get(url, 500_000)
    meta = ImageMeta()
    meta.feed(html.decode("utf-8", "replace"))
    if not meta.src:
        raise ValueError("no Open Graph image found")
    image_url = urljoin(page_url, meta.src)
    if urlsplit(image_url).scheme not in ("http", "https"):
        raise ValueError("image URL must use HTTP or HTTPS")
    _, data = get(image_url, 5_000_000)
    ext = extension(data)
    if not ext:
        raise ValueError("unsupported image format")
    return ext, data


def main(path):
    fiche = Path(path).resolve()
    if fiche.parent != SIGNETS or fiche.suffix != ".md" or not fiche.is_file():
        raise ValueError("expected an existing content/signets/*.md file")
    text = fiche.read_text()
    if re.search(r"(?m)^  image:", text):
        raise ValueError("signet already has an image")
    url = re.search(r"(?m)^  url:\s*[\"']?(https?://[^\s\"']+)", text)
    if not url:
        raise ValueError("signet has no HTTP URL")
    ext, data = fetch_image(url.group(1))
    updated = re.sub(
        r"(?m)^extra:\s*$",
        f'extra:\n  image: "/images/{fiche.stem}.{ext}"',
        text,
        count=1,
    )
    if updated == text:
        raise ValueError("signet has no extra field")
    IMAGES.mkdir(exist_ok=True)
    (IMAGES / f"{fiche.stem}.{ext}").write_bytes(data)
    fiche.write_text(updated)
    print(f"Saved /images/{fiche.stem}.{ext}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 scripts/fetch_images.py content/signets/name.md")
    try:
        main(sys.argv[1])
    except (OSError, ValueError) as error:
        sys.exit(str(error))
