from flask import Flask, render_template, request, redirect
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = Flask(__name__)

# -------------------------------------------------------------------
# Accessibility profiles – predefined CSS
# -------------------------------------------------------------------
PROFILE_CSS = {
    "low_vision": """
        html, body { font-size: 18px !important; }
        p, li, a, span, input, button, label {
            font-size: 1.05em !important;
            line-height: 1.8 !important;
        }
        body { filter: contrast(1.15); }
        a { text-decoration: underline !important; }
        *:focus {
            outline: 3px solid #facc15 !important;
            outline-offset: 3px !important;
        }
    """,

    "dyslexia": """
        * { font-family: Arial, Verdana, sans-serif !important; }
        p, li {
            letter-spacing: 0.06em !important;
            word-spacing: 0.12em !important;
            line-height: 1.8 !important;
        }
        p { max-width: 60ch !important; }
        body {
            background-color: #f3f4f6 !important;
            color: #111827 !important;
        }
    """,

    "adhd": """
        * { animation: none !important; transition: none !important; }
        body {
            background-color: #ffffff !important;
            color: #111827 !important;
        }
        [class*="banner"], [class*="promo"], [class*="carousel"],
        [class*="slider"], [class*="ads"], [id*="ad"], iframe {
            display: none !important;
        }
        main, article, section {
            max-width: 70rem !important;
            margin-inline: auto !important;
        }
    """,

    "autism": """
        * { animation: none !important; transition: none !important; }
        body { filter: saturate(0.75) brightness(1.02); }
        [class*="banner"], [class*="promo"],
        [class*="carousel"], [class*="slider"] {
            display: none !important;
        }
        section, article, main, nav {
            margin-bottom: 1.6rem !important;
        }
        p, li { line-height: 1.9 !important; }
    """,

    "motor": """
        a, button, input[type="button"], input[type="submit"], input[type="reset"] {
            min-height: 44px !important;
            padding: 10px 18px !important;
            font-size: 1.05em !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        *:focus {
            outline: 3px solid #2563eb !important;
            outline-offset: 3px !important;
        }
    """,

    "elder": """
        html, body { font-size: 19px !important; }
        body {
            background-color: #fdf6e3 !important;
            color: #111827 !important;
        }
        p, li { line-height: 1.9 !important; }
        h1, h2, h3 {
            font-weight: 700 !important;
            margin-top: 1.2em !important;
        }
        a { text-decoration: underline !important; }
    """,

    "photosensitive": """
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
        }
        video[autoplay], [class*="video-autoplay"],
        [data-autoplay="true"] { autoplay: false !important; }
        img[src$=".gif"], [class*="gif"], [class*="marquee"] {
            animation: none !important;
        }
    """,

    # Custom profile (CSS generated dynamically)
    "custom": ""  
}


# -------------------------------------------------------------------
# Custom Profile CSS Generator
# -------------------------------------------------------------------
def generate_custom_css(size, family, gradient):
    gradients = {
        "green-blue": "linear-gradient(135deg, #22c55e, #3b82f6)",
        "purple-pink": "linear-gradient(135deg, #a855f7, #ec4899)",
        "orange-red": "linear-gradient(135deg, #f97316, #ef4444)",
        "mono-dark": "linear-gradient(135deg, #0f172a, #1e293b)"
    }

    css = f"""
        html, body {{
            font-size: {size} !important;
            font-family: {family} !important;
        }}
        body {{
            background: {gradients.get(gradient, gradients['green-blue'])} !important;
            color: white !important;
        }}
        p, li {{
            line-height: 1.75 !important;
        }}
    """
    return css


# -------------------------------------------------------------------
# Injecting CSS into scraped page
# -------------------------------------------------------------------
def apply_profile_css(html: str, profile: str, original_url: str, custom_css=None) -> str:

    soup = BeautifulSoup(html, "html.parser")

    # Base URL fix
    parsed = urlparse(original_url)
    root = f"{parsed.scheme}://{parsed.netloc}"

    if soup.head:
        if not soup.head.find("base"):
            soup.head.insert(0, soup.new_tag("base", href=root))
    else:
        head = soup.new_tag("head")
        head.append(soup.new_tag("base", href=root))
        soup.insert(0, head)

    # Remove scripts for ADHD + Photosensitive
    if profile in ("adhd", "photosensitive"):
        for script in soup.find_all("script"):
            script.decompose()

    # Inject CSS
    style_tag = soup.new_tag("style")
    style_tag.string = custom_css if profile == "custom" else PROFILE_CSS.get(profile, "")
    soup.head.append(style_tag)

    return str(soup)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("aigen.html")


@app.route("/preview", methods=["POST"])
def preview():
    url = request.form.get("url")
    profile = request.form.get("profile")

    # Custom profile settings
    custom_css = None
    if profile == "custom":
        size = request.form.get("font_size", "18px")
        family = request.form.get("font_family", "system-ui")
        gradient = request.form.get("gradient", "green-blue")
        custom_css = generate_custom_css(size, family, gradient)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=12)
    except Exception as e:
        return f"<h2>Error loading URL</h2><p>{e}</p>"

    if resp.status_code >= 400:
        return f"<h2>Blocked by website</h2><p>Status: {resp.status_code}</p>"

    html = apply_profile_css(resp.text, profile, url, custom_css)
    return html


# -------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
