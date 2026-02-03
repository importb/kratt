"""
Web search, filtering, and content extraction utilities.

Provides functions for DuckDuckGo search, LLM-based query optimization and filtering,
and headless browser scraping via Playwright.
"""

import re
import time
import datetime
from urllib.parse import urlparse

import ollama
from ddgs import DDGS
from playwright.sync_api import sync_playwright, Page


def improve_search_query(user_term: str, model_name: str) -> str:
    """
    Use LLM to convert a chat prompt into a keyword-optimized search query.

    Args:
        user_term: The raw user input from the chat.
        model_name: The name of the LLM to use for generation.

    Returns:
        A concise search query optimized for search engines.
    """
    current_year = datetime.date.today().year
    prompt = (
        f"Instruction: Generate 3-5 keywords for a Google search.\n"
        f"Reference Year: {current_year}\n\n"
        f"Input: Who is the CEO of Apple?\n"
        f"Output: Apple CEO {current_year}\n\n"
        f"Input: {user_term}\n"
        f"Output:"
    )

    try:
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            options={'temperature': 0, 'stop': ["\n", "Input:"], 'num_predict': 15}
        )
        return response['response'].strip().strip('"\'')
    except Exception as e:
        print(f"Query optimization failed: {e}")
        return user_term


def filter_search_results(user_term: str, results: list[dict], model_name: str) -> list[dict]:
    """
    Use LLM to filter search results for relevance to the user query.

    Iterates through results and asks the LLM a binary YES/NO question regarding relevance.

    Args:
        user_term: The original user query.
        results: List of search result dicts with 'title', 'url', 'snippet'.
        model_name: The LLM to use for relevance assessment.

    Returns:
        Filtered list of relevant search results.
    """
    if len(results) <= 2:
        return results

    filtered_results = []
    for item in results:
        prompt = (
            f"Instruction: Answer YES or NO if the result is relevant.\n"
            f"Query: {user_term}\n"
            f"Result: {item['title']} - {item['snippet']}\n"
            f"Relevant:"
        )

        try:
            response = ollama.generate(
                model=model_name,
                prompt=prompt,
                options={'temperature': 0, 'stop': ["\n"], 'num_predict': 2}
            )
            if "YES" in response['response'].strip().upper():
                filtered_results.append(item)
        except Exception:
            # If LLM fails, be permissive and keep the result
            filtered_results.append(item)

    return filtered_results


def search_duckduckgo(query: str, num_results: int = 10) -> list[dict]:
    """
    Perform a DuckDuckGo text search.

    Args:
        query: The search string.
        num_results: Maximum number of results to fetch.

    Returns:
        List of dicts with 'title', 'url', and 'snippet' keys.
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
    except Exception as e:
        print(f"DDG Error: {e}")
    return results


def normalize_url(url: str, domain: str) -> str | None:
    """
    Ensure URL belongs to the target domain and isn't a binary/resource file.

    Args:
        url: The URL to validate.
        domain: The expected domain (e.g., 'example.com').

    Returns:
        Normalized URL if valid, None if external or resource file.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.netloc != domain:
        return None

    skip_ext = (".jpg", ".png", ".gif", ".pdf", ".zip", ".css", ".js", ".svg", ".webp")
    if parsed.path.lower().endswith(skip_ext):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def extract_text(page: Page) -> str:
    """
    Extract readable text from a webpage DOM.

    Removes clutter (scripts, ads, cookie banners) and formats content
    into structured Markdown-like text with headings and lists.

    Args:
        page: Playwright Page object.

    Returns:
        Extracted and formatted text content.
    """
    # Remove non-content elements
    page.evaluate("""
        const remove = ['script', 'style', 'noscript', 'iframe', 
                       '.cookie-banner', '.popup', '.modal', '.ad', 
                       '[aria-hidden="true"]'];
        remove.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });
    """)

    # Extract structured content blocks
    content = page.evaluate("""
        () => {
            const blocks = [];
            const seen = new Set();
            
            const title = document.querySelector('h1')?.innerText?.trim();
            if (title) blocks.push('# ' + title + '\\n');

            const elements = document.querySelectorAll(
                'h1, h2, h3, h4, h5, h6, p, li, td, th, blockquote, pre, ' +
                'article, section, main, [role="main"], .content, #content'
            );

            elements.forEach(el => {
                let text = el.innerText?.trim();
                // Filter out very short strings or duplicates
                if (!text || text.length < 10 || seen.has(text)) return;
                seen.add(text);

                const tag = el.tagName.toLowerCase();
                if (tag.match(/^h[1-6]$/)) {
                    blocks.push('\\n' + '#'.repeat(parseInt(tag[1])) + ' ' + text + '\\n');
                } else if (tag === 'li') {
                    blocks.push('  • ' + text);
                } else if (tag === 'pre') {
                    blocks.push('```\\n' + text + '\\n```');
                } else if (text.length > 30) {
                    blocks.push(text);
                }
            });
            return blocks.join('\\n');
        }
    """)

    text = re.sub(r'\n{3,}', '\n\n', content)
    return re.sub(r'[ \t]+', ' ', text).strip()


def extract_links_prioritized(page: Page) -> dict[str, list[str]]:
    """
    Categorize links into Body, Header, and Footer for intelligent crawling.

    Body links are generally more relevant for deep scraping than navigation
    (header) or legal/sitemap links (footer).

    Args:
        page: Playwright Page object.

    Returns:
        Dict with 'body', 'header', and 'footer' link lists.
    """
    return page.evaluate("""
        () => {
            const getLinks = (sel) => {
                const el = document.querySelector(sel);
                return el ? [...el.querySelectorAll('a[href]')].map(a => a.href) : [];
            };

            const footer = new Set([
                ...getLinks('footer'), ...getLinks('.footer'), ...getLinks('#footer')
            ]);
            const header = new Set([
                ...getLinks('header'), ...getLinks('nav'), ...getLinks('.navbar')
            ]);
            
            const all = [...document.querySelectorAll('a[href]')].map(a => a.href);
            const body = all.filter(h => !footer.has(h) && !header.has(h));

            return {
                footer: [...footer],
                header: [...header],
                body: [...new Set(body)]
            };
        }
    """)


class WebScraper:
    """Manages headless browser scraping using Playwright."""

    def __init__(self, max_pages_per_site: int = 1, delay: float = 0.5, headless: bool = True):
        """
        Initialize the web scraper.

        Args:
            max_pages_per_site: Maximum pages to scrape per domain.
            delay: Delay in seconds between page requests.
            headless: Whether to run the browser in headless mode.
        """
        self.max_pages_per_site = max_pages_per_site
        self.delay = delay
        self.headless = headless
        self.results: dict[str, str] = {}

    def scrape_site(self, start_url: str, page: Page) -> dict[str, str]:
        """
        Scrape a specific URL and optionally follow internal links.

        Uses a priority queue to traverse the site, prioritizing the landing page
        (rank 0) over discovered internal links (rank 1).

        Args:
            start_url: The initial URL to scrape.
            page: Playwright Page object.

        Returns:
            Dict mapping URL to extracted text content.
        """
        domain = urlparse(start_url).netloc
        visited: set[str] = {start_url}
        site_results: dict[str, str] = {}
        queue: list[tuple[int, str]] = [(0, start_url)]

        while queue and len(site_results) < self.max_pages_per_site:
            queue.sort(key=lambda x: x[0])
            _, url = queue.pop(0)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(500)

                text = extract_text(page)
                if text and len(text) > 100:
                    site_results[url] = text

                # Look for body links if more pages are needed
                if len(site_results) < self.max_pages_per_site:
                    links = extract_links_prioritized(page)
                    for href in links["body"]:
                        normalized = normalize_url(href, domain)
                        if normalized and normalized not in visited:
                            visited.add(normalized)
                            queue.append((1, normalized))
            except Exception as e:
                print(f"Scrape error {url}: {e}")

            time.sleep(self.delay)

        return site_results

    def scrape_urls(self, urls: list[str]) -> dict[str, str]:
        """
        Launch browser and scrape list of URLs.

        Args:
            urls: List of starting URLs.

        Returns:
            Mapping of URL to extracted markdown-like text.
        """
        if not urls:
            return {}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()

                for url in urls:
                    self.results.update(self.scrape_site(url, page))

                browser.close()
        except Exception as e:
            print(f"Playwright critical error: {e}")

        return self.results