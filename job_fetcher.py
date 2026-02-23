import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; KarriarSverigeAI/1.0)"}
MAX_CHARS = 20000

def _validate_url(url: str) -> None:
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL. Must start with http:// or https://")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost"} or host.startswith("127.") or host.startswith("0."):
        raise ValueError("Local URLs are not allowed")

def fetch_job_from_url(url: str) -> str:
    _validate_url(url)
    resp = requests.get(url, headers=HEADERS, timeout=12)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script","style","noscript","header","footer","svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    clean = "\n".join([ln for ln in lines if ln])

    if len(clean) < 300:
        raise ValueError("Job content too short or blocked (may require JavaScript rendering).")

    return clean[:MAX_CHARS]
