# app.py
from flask import Flask, request, render_template, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

# Load CSS we will inject into proxied pages
PROFILE_CSS_PATH = os.path.join(app.static_folder or 'static', 'profiles.css')
if os.path.exists(PROFILE_CSS_PATH):
    with open(PROFILE_CSS_PATH, 'r', encoding='utf-8') as fh:
        PROFILE_CSS = fh.read()
else:
    PROFILE_CSS = "/* profile css file not found */"

@app.route('/')
def index():
    """Serve the front-end UI (templates/index.html)."""
    return render_template('index.html')

def sanitize_and_inject(html_text: str, original_base: str, profile_key: str) -> str:
    """
    Parse the fetched HTML and inject:
      - a <base> tag so relative resources point to the original site
      - a <style id="a11y-profile"> containing PROFILE_CSS
      - a class on <body> that activates the chosen profile (e.g. profile-dyslexic)
    """
    soup = BeautifulSoup(html_text, 'html.parser')

    # Ensure there's a <head>
    if soup.head is None:
        head = soup.new_tag('head')
        soup.insert(0, head)
    else:
        head = soup.head

    # Insert or replace <base href="...">
    base_tag = soup.new_tag('base', href=original_base)
    existing = head.find('base')
    if existing:
        existing.replace_with(base_tag)
    else:
        head.insert(0, base_tag)

    # Add the style block with profile CSS
    style_tag = soup.new_tag('style', id='a11y-profile')
    style_tag.string = PROFILE_CSS
    head.append(style_tag)

    # Ensure a <body> exists and add profile class
    if soup.body is None:
        body = soup.new_tag('body')
        # Move all top-level content into the new body
        for element in list(soup.contents):
            body.append(element.extract())
        soup.append(body)
    body = soup.body

    # Remove any existing profile-* classes and add the requested one
    existing_classes = list(body.get('class', []))
    existing_classes = [c for c in existing_classes if not c.startswith('profile-')]
    if profile_key:
        existing_classes.append(profile_key)
    if existing_classes:
        body['class'] = existing_classes

    return str(soup)

@app.route('/fetch')
def fetch_and_modify():
    """
    Proxy endpoint:
      - Accepts query params: ?url=TARGET&profile=profile-key
      - Fetches TARGET, injects PROFILE_CSS and profile class, returns modified HTML.
    """
    target = request.args.get('url', '')
    profile = request.args.get('profile', '')

    if not target:
        return "Missing 'url' parameter", 400

    # Normalize URL: add http if missing
    parsed = urlparse(target)
    if not parsed.scheme:
        target = 'http://' + target
        parsed = urlparse(target)

    try:
        resp = requests.get(target, timeout=12, headers={'User-Agent': 'a11y-simulator/1.0'})
        resp.raise_for_status()
    except Exception as e:
        return f"Error fetching target URL: {e}", 502

    base = f"{parsed.scheme}://{parsed.netloc}"
    modified = sanitize_and_inject(resp.text, base, profile)
    return Response(modified, headers={'Content-Type': 'text/html; charset=utf-8'})

if __name__ == '__main__':
    # When run directly, start the Flask dev server on port 5000
    app.run(debug=True, port=5000)
