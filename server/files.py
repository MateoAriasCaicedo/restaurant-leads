"""Files in a lead folder that the UI can list, show, add and remove.

Only these places are reachable, and only by a bare file name:
  instagram -> leads/<slug>/photos/instagram     maps -> leads/<slug>/photos/maps
  menu      -> leads/<slug>/raw/menu             site -> leads/<slug>/raw/photos (read-only: crawled)
Removing a file moves it to leads/<slug>/.trash/; nothing is deleted.
"""
import io
import re
import tempfile
import time
import zipfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from leadgen import config

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
KINDS = {"instagram": ("photos", "instagram"), "maps": ("photos", "maps"), "menu": ("raw", "menu"), "site": ("raw", "photos")}
WRITABLE = ("instagram", "maps", "menu")
LIMITS = {"instagram": config.MAX_PHOTOS_PER_SOURCE, "maps": config.MAX_PHOTOS_PER_SOURCE, "menu": 12}
THUMB_WIDTHS = (160, 320, 640, 1200)
MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".pdf": "application/pdf"}


class Invalid(Exception):
    pass


def folder(d, kind):
    if kind not in KINDS:
        raise Invalid(f"Unknown file group: {kind}")
    return Path(d).joinpath(*KINDS[kind])


def allowed_ext(kind):
    return IMG_EXT + ((".pdf",) if kind == "menu" else ())


def resolve(d, kind, name):
    """The file `name` inside the kind's folder, or Invalid. The name must be a plain file name."""
    base = folder(d, kind)
    if not name or name != Path(name).name or name.startswith(".") or "\\" in name or "/" in name or ":" in name:
        raise Invalid("Bad file name")
    f = base / name
    if f.suffix.lower() not in allowed_ext(kind) or f.resolve().parent != base.resolve():
        raise Invalid("Bad file name")
    return f


def paths(d, kind):
    """The files of one group that the UI can see, sorted by name."""
    base = folder(d, kind)
    if not base.is_dir():
        return []
    return [f for f in sorted(base.iterdir()) if f.is_file() and f.suffix.lower() in allowed_ext(kind)]


def listing(d, kind, key):
    out = []
    for f in paths(d, kind):
        url = f"/api/leads/{key}/files/{kind}/{quote(f.name)}"
        out.append({"name": f.name, "size": f.stat().st_size, "url": url, "mtime": f.stat().st_mtime,
                    "is_image": f.suffix.lower() in IMG_EXT})
    return out


def archive(d, kinds):
    """A zip of the files in the given groups, one folder per group, as (open file at offset 0, file count, bytes).

    Entries are stored, not deflated: photos and PDFs are already compressed. The temp file is on disk past
    a few MB so a big lead does not sit in memory; the caller closes it."""
    unknown = [k for k in kinds if k not in KINDS]
    if unknown:
        raise Invalid(f"Unknown file group: {unknown[0]}")
    tmp = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024)
    count = 0
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:
            for kind in kinds:
                for f in paths(d, kind):
                    z.write(f, f"{kind}/{f.name}")
                    count += 1
        size = tmp.tell()
        tmp.seek(0)
    except BaseException:
        tmp.close()
        raise
    return tmp, count, size


def clean_name(name, ext):
    stem = re.sub(r"[^A-Za-z0-9 ._-]+", "_", Path(name or "file").stem).strip(" ._") or "file"
    return stem[:80] + ext


def save_upload(d, kind, filename, data):
    """Store one uploaded file after checking it is what its extension says. Returns the stored name."""
    if kind not in WRITABLE:
        raise Invalid("Files cannot be added to this group")
    ext = Path(filename or "").suffix.lower()
    if ext not in allowed_ext(kind):
        raise Invalid(f"{filename}: only {', '.join(allowed_ext(kind))} files are accepted here")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise Invalid(f"{filename}: larger than {config.MAX_UPLOAD_MB} MB")
    if ext == ".pdf":
        if not data.startswith(b"%PDF"):
            raise Invalid(f"{filename}: not a PDF file")
    else:
        from PIL import Image
        try:
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            raise Invalid(f"{filename}: not a readable image") from None
    base = folder(d, kind)
    base.mkdir(parents=True, exist_ok=True)
    existing = [f for f in base.iterdir() if f.is_file() and f.suffix.lower() in allowed_ext(kind)]
    if len(existing) >= LIMITS[kind]:
        raise Invalid(f"This group already has {LIMITS[kind]} files, the most the analysis uses. Remove one first.")
    name = clean_name(filename, ext)
    n = 2
    while (base / name).exists():
        name = clean_name(f"{Path(filename).stem}-{n}", ext)
        n += 1
    (base / name).write_bytes(data)
    return name


def trash(d, kind, name):
    if kind not in WRITABLE:
        raise Invalid("Files cannot be removed from this group")
    f = resolve(d, kind, name)
    if not f.exists():
        raise Invalid("No such file")
    bin_dir = Path(d) / ".trash"
    bin_dir.mkdir(exist_ok=True)
    f.replace(bin_dir / f"{kind}-{int(time.time())}-{f.name}")


@lru_cache(maxsize=256)
def _thumb(path, mtime_ns, width):
    from PIL import Image
    im = Image.open(path)
    im.load()
    im = im.convert("RGB")
    im.thumbnail((width, width * 3))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=78, optimize=True)
    return buf.getvalue()


def thumbnail(f, width):
    """JPEG bytes of the image scaled to one of THUMB_WIDTHS."""
    if width not in THUMB_WIDTHS or f.suffix.lower() not in IMG_EXT:
        raise Invalid("Bad thumbnail request")
    return _thumb(str(f), f.stat().st_mtime_ns, width)


def write_notes(d, text):
    Path(d).mkdir(parents=True, exist_ok=True)
    (Path(d) / "notes.txt").write_text(str(text)[:20000], "utf-8")
