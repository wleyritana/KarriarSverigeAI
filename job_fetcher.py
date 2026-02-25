import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; KarriarSverigeAI/1.0)"}
MAX_CHARS = 20000
MIN_CHARS_DEFAULT = 300

def _validate_url(url: str) -> None:
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL. Must start with http:// or https://")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    # Basic SSRF protection
    if host in {"localhost"} or host.startswith("127.") or host.startswith("0."):
        raise ValueError("Local URLs are not allowed")

def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript","header","footer","svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    clean = "\n".join([ln for ln in lines if ln])
    return clean

def fetch_job_preview(url: str) -> dict:
    """Fetch a URL and return best-effort extracted text + meta (no minimum length enforcement)."""
    _validate_url(url)
    resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
    resp.raise_for_status()
    clean = _extract_text(resp.text)
    return {
        "status_code": resp.status_code,
        "final_url": str(resp.url),
        "text": clean[:MAX_CHARS],
        "text_length": len(clean),
    }

def fetch_job_from_url(url: str, min_chars: int = MIN_CHARS_DEFAULT) -> str:
    """Fetch and extract job text. Raises ValueError if content looks blocked/too short."""
    meta = fetch_job_preview(url)
    clean = meta["text"]
    if meta["text_length"] < min_chars:
        raise ValueError("Job content too short or blocked (may require JavaScript rendering).")
    return clean
