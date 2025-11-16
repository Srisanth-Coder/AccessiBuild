from flask import Flask, render_template, request, redirect
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = Flask(__name__)

# -------------------------------------------------------------------
# Accessibility profiles – all purely CSS, easy to demo
# -------------------------------------------------------------------
PROFILE_CSS = {
    # 1. Low Vision – keep original colors/layout, just make it easier to see
    "low_vision": """
        html, body {
            font-size: 18px !important;   /* default ~16px → 18px */
        }
        p, li, a, span, input, button, label {
            font-size: 1.05em !important;
            line-height: 1.8 !important;
        }
        body {
            filter: contrast(1.15);       /* subtle contrast boost */
        }
        a {
            text-decoration: underline !important;
        }
        a, button {
            padding-top: 2px !important;
            padding-bottom: 2px !important;
        }
        *:focus {
            outline: 3px solid #facc15 !important;
            outline-offset: 3px !important;
        }
    """,

    # 2. Dyslexia – readable fonts + extra spacing
    "dyslexia": """
        * {
            font-family: Arial, Verdana, sans-serif !important;
        }
        p, li {
            letter-spacing: 0.06em !important;
            word-spacing: 0.12em !important;
            line-height: 1.8 !important;
        }
        p {
            max-width: 60ch !important;   /* shorter line length */
        }
        body {
            background-color: #f3f4f6 !important;
            color: #111827 !important;
        }
    """,

    # 3. ADHD – kill motion + obvious clutter
    "adhd": """
        * {
            animation: none !important;
            transition: none !important;
        }
        body {
            background-color: #ffffff !important;
            color: #111827 !important;
        }
        /* Hide common distraction containers */
        [class*="banner"],
        [class*="promo"],
        [class*="carousel"],
        [class*="slider"],
        [class*="ads"],
        [id*="ad"],
        iframe {
            display: none !important;
        }
        main, article, section {
            max-width: 70rem !important;
            margin-inline: auto !important;
        }
    """,

    # 4. Autism / Sensory-Friendly – soften colors + layout breathing space
    "autism": """
        * {
            animation: none !important;
            transition: none !important;
        }
        body {
            filter: saturate(0.75) brightness(1.02);
        }
        [class*="banner"],
        [class*="promo"],
        [class*="carousel"],
        [class*="slider"] {
            display: none !important;
        }
        section, article, main, nav {
            margin-bottom: 1.6rem !important;
        }
        p, li {
            line-height: 1.9 !important;
        }
    """,

    # 5. Motor Disability – bigger click targets + clearer focus
    "motor": """
        a, button,
        input[type="button"],
        input[type="submit"],
        input[type="reset"] {
            min-height: 44px !important;   /* recommended by WCAG */
            padding: 10px 18px !important;
            font-size: 1.05em !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        a + a, button + button {
            margin-left: 8px !important;
        }
        *:focus {
            outline: 3px solid #2563eb !important;
            outline-offset: 3px !important;
        }
    """,

    # 6. Elder / Easy-Read – bigger text + calm contrast
    "elder": """
        html, body {
            font-size: 19px !important;
        }
        body {
            background-color: #fdf6e3 !important; /* soft beige */
            color: #111827 !important;
        }
        p, li {
            line-height: 1.9 !important;
        }
        h1, h2, h3 {
            font-weight: 700 !important;
            margin-top: 1.2em !important;
        }
        a {
            text-decoration: underline !important;
        }
    """,

    # 7. Photosensitive / No-Motion – no animations, safe visuals
    "photosensitive": """
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
        }
        video[autoplay],
        [class*="video-autoplay"],
        [data-autoplay="true"] {
            autoplay: false !important;
        }
        img[src$=".gif"],
        [class*="gif"],
        [class*="marquee"] {
            animation: none !important;
        }
    """,
}


def apply_profile_css(html: str, profile: str, original_url: str) -> str:
    """
    - Adds <base> so CSS/images load from the original website.
    - Optionally strips scripts (only for some profiles).
    - Injects the profile-specific CSS.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) Base tag → fix /static/... 404 issues
    parsed = urlparse(original_url)
    root = f"{parsed.scheme}://{parsed.netloc}"

    if soup.head:
        if not soup.head.find("base"):
            base_tag = soup.new_tag("base", href=root)
            soup.head.insert(0, base_tag)
    else:
        head = soup.new_tag("head")
        base_tag = soup.new_tag("base", href=root)
        head.append(base_tag)
        soup.insert(0, head)

    # 2) Only strip scripts for ADHD + Photosensitive (to reduce distractions)
    if profile in ("adhd", "photosensitive"):
        for script in soup.find_all("script"):
            script.decompose()

    # 3) Inject our CSS
    style_tag = soup.new_tag("style")
    style_tag.string = PROFILE_CSS.get(profile, "")
    soup.head.append(style_tag)

    return str(soup)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    url = request.form.get("url")
    profile = request.form.get("profile")

    # Use browser-like headers to bypass anti-bot protections
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }

    # Fetch page
    try:
        resp = requests.get(url, headers=headers, timeout=12)
    except Exception as e:
        return f"""
            <h2 style='font-family: system-ui'>Could not load URL</h2>
            <p>{str(e)}</p>
            <p>This site may be blocking automated requests. 
            Try another public page (blog, article, docs, etc.).</p>
        """

    # Handle HTTP errors (418, 403, 404, etc.)
    if resp.status_code >= 400:
        return f"""
            <h2 style='font-family: system-ui'>This website blocked our preview</h2>
            <p>Status code: {resp.status_code}</p>
            <p>Some websites (e.g., IEEE, banking portals, paywalled sites) 
            block automated tools.  
            Try a public site like docs or blogs.</p>
        """

    # Inject accessibility CSS
    html = resp.text
    html = apply_profile_css(html, profile, url)

    return html



if __name__ == "__main__":
    app.run(debug=True)
