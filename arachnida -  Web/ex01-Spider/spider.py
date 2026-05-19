import argparse
import os
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}


def error(message):
    print(f"./spider: error: {message}")
    raise SystemExit(1)


def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


def normalize_url(url):
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


def has_allowed_extension(url):
    parsed = urlparse(url)
    _, extension = os.path.splitext(parsed.path.lower())
    return extension in ALLOWED_EXTENSIONS


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img" and attributes.get("src"):
            self.links.append(attributes["src"])
        elif tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])


def unique_destination(directory, filename):
    base_name, extension = os.path.splitext(filename)
    candidate = filename
    index = 1

    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{base_name}_{index}{extension}"
        index += 1

    return os.path.join(directory, candidate)


def download_image(session, image_url, output_directory):
    image_url = normalize_url(image_url)
    if not has_allowed_extension(image_url):
        return

    filename = os.path.basename(urlparse(image_url).path)
    if not filename:
        return

    destination = unique_destination(output_directory, filename)

    try:
        response = session.get(image_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return

    with open(destination, "wb") as file:
        file.write(response.content)


def extract_links(html, base_url):
    parser = LinkParser()
    parser.feed(html)

    for source in parser.links:
        yield urljoin(base_url, source)


def crawl(session, url, base_domain, output_directory, recursive, max_depth, current_depth, visited_pages):
    url = normalize_url(url)
    if url in visited_pages:
        return
    visited_pages.add(url)

    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        return

    for image_url in extract_links(response.text, url):
        if urlparse(image_url).netloc == base_domain and has_allowed_extension(image_url):
            download_image(session, image_url, output_directory)

    if not recursive or current_depth >= max_depth:
        return

    for next_url in extract_links(response.text, url):
        parsed = urlparse(next_url)
        # commenter: pour enlever domain de base
        if parsed.netloc != base_domain:
            continue
        if has_allowed_extension(next_url):
            continue
        print(f"Crawling: {next_url}")
        crawl(
            session,
            next_url,
            base_domain,
            output_directory,
            recursive,
            max_depth,
            current_depth + 1,
            visited_pages,
        )


def parse_args():
    parser = argparse.ArgumentParser(prog="spider", add_help=True)
    parser.add_argument("-r", action="store_true", help="recursive download")
    parser.add_argument("-l", type=int, default=5, metavar="N", help="maximum recursive depth")
    parser.add_argument("-p", default="./data/", metavar="PATH", help="output directory")
    parser.add_argument("url", help="target URL")
    args = parser.parse_args()

    if args.l < 0:
        error("depth must be a non-negative integer")

    return args


def main():
    args = parse_args()

    if not is_valid_url(args.url):
        error("invalid URL")

    start_url = normalize_url(args.url)
    parsed_url = urlparse(start_url)
    output_directory = args.p

    ensure_directory(output_directory)

    session = requests.Session()
    visited_pages = set()

    crawl(
        session=session,
        url=start_url,
        base_domain=parsed_url.netloc,
        output_directory=output_directory,
        recursive=args.r,
        max_depth=args.l,
        current_depth=0,
        visited_pages=visited_pages,
    )


if __name__ == "__main__":
    main()
