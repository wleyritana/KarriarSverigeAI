import requests
from bs4 import BeautifulSoup

def fetch_job_from_url(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    return soup.get_text()[:20000]
