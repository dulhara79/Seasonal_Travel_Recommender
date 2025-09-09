import requests
from bs4 import BeautifulSoup
import json
from tqdm import tqdm
from activity_sources import DEFAULT_SOURCES

# Output file
OUTPUT_FILE = "server/data/activity_sources.json"

# Helpers: one function per website type
def scrape_tripadvisor(url):
    # Logic to parse TripAdvisor pages
    # Returns list of dicts: [{'name': ..., 'description': ..., 'url': ...}, ...]
    pass

def scrape_klook(url):
    # Logic to parse Klook pages
    pass

def scrape_peek(url):
    # Logic to parse Peek pages
    pass

def scrape_generic(url):
    # Fallback generic parser
    pass

# Main scraper function
def scrape_all():
    all_activities = []
    for url in tqdm(DEFAULT_SOURCES):
        if "tripadvisor.com" in url:
            activities = scrape_tripadvisor(url)
        elif "klook.com" in url:
            activities = scrape_klook(url)
        elif "peek.com" in url:
            activities = scrape_peek(url)
        else:
            activities = scrape_generic(url)

        all_activities.extend(activities)

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_activities, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape_all()
