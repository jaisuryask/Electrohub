"""Third-party API: YouTube oEmbed (video title + channel), with a hard time limit and a fallback.

If YouTube is slow or unreachable (> TIMEOUT seconds) the project's stored video credit is used instead.
Results are cached so a page view never waits twice.
"""
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 3          # seconds - hard limit for the external call
OK_TTL = 6 * 3600    # cache successful lookups for 6 hours
FAIL_TTL = 300       # don't retry a failed lookup for 5 minutes
_cache = {}
_pool = ThreadPoolExecutor(max_workers=4)
status = {"last": "not called yet", "ts": None}


def _fetch(url):
    req = urllib.request.Request(url, headers={"user-agent": "ElectroLab/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def youtube_meta(video_id, fallback_title=""):
    """Return dict(title, author, source) where source is 'youtube-oembed', 'cache' or 'fallback'."""
    fallback = {"title": fallback_title, "author": "", "source": "fallback"}
    if not video_id:
        return fallback
    hit = _cache.get(video_id)
    if hit and hit[0] > time.time():
        return {**hit[1], "source": "cache"} if hit[1] else fallback
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(
        f"https://www.youtube.com/watch?v={video_id}", safe="")
    try:
        # result(timeout=...) is a hard wall-clock limit (socket timeouts alone don't cover slow DNS/connect)
        data = _pool.submit(_fetch, url).result(timeout=TIMEOUT)
        meta = {"title": data.get("title", fallback_title), "author": data.get("author_name", "")}
        _cache[video_id] = (time.time() + OK_TTL, meta)
        status.update(last="ok", ts=time.time())
        return {**meta, "source": "youtube-oembed"}
    except Exception as exc:
        _cache[video_id] = (time.time() + FAIL_TTL, None)
        status.update(last=f"fallback used ({type(exc).__name__})", ts=time.time())
        return fallback
