import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import os
from typing import Optional
from .source import DataSource

class WikipediaImageScraper(DataSource):
    """Scrapes images from Wikipedia based on search queries."""

    def __init__(self, user_agent: str = "Mozilla/5.0 (Research Bot)"):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def generate_content(self, query: str, save_path: str) -> str:
        """
        Scrape an image from Wikipedia based on the query and save it.

        Args:
            query: Search term for Wikipedia
            save_path: Path where the scraped image will be saved

        Returns:
            Path to the saved image
        """
        # Search Wikipedia for the query
        search_url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"

        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the first meaningful image (skip icons and small images)
            image_url = self._find_main_image(soup)

            if not image_url:
                raise ValueError(f"No suitable image found for query: {query}")

            # Download and save the image
            img_response = self.session.get(image_url, timeout=10)
            img_response.raise_for_status()

            image = Image.open(BytesIO(img_response.content))

            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Save the image
            image.save(save_path)

            return save_path

        except Exception as e:
            raise RuntimeError(f"Failed to scrape image for '{query}': {str(e)}")

    def _find_main_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the main content image from a Wikipedia page."""

        # Look for infobox images first (usually the main image)
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            img = infobox.find('img')
            if img and img.get('src'):
                return self._normalize_url(img['src'])

        # Look for images in the main content area
        content = soup.find('div', {'id': 'mw-content-text'})
        if content:
            images = content.find_all('img')
            for img in images:
                src = img.get('src', '')
                # Filter out icons, flags, and small images
                if (src and
                    not any(x in src.lower() for x in ['icon', 'flag', 'edit', 'logo']) and
                    img.get('width', '0').isdigit() and int(img.get('width', '0')) > 200):
                    return self._normalize_url(src)

        return None

    def _normalize_url(self, url: str) -> str:
        """Convert relative Wikipedia URLs to absolute URLs."""
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return 'https://en.wikipedia.org' + url
        return url
