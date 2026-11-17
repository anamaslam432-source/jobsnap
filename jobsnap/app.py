

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import requests
from flask import Flask, render_template, request



BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("job-finder")

def load_env_file(path):
    """Minimal .env reader (no extra dependency). Real environment variables win."""
    if not path.is_file():
        return False
    # utf-8-sig strips the invisible BOM that Windows Notepad adds to files.
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if value[:1] in ("'", '"'):
            end = value.find(value[0], 1)
            value = value[1:end] if end != -1 else value[1:]
        else:
            value = value.split(" #")[0].strip()
        if name and not os.environ.get(name):
            os.environ[name] = value
    return True

ENV_FILE = BASE_DIR / ".env"
ENV_FILE_FOUND = load_env_file(ENV_FILE)

API_KEY_NAMES = ("RAPIDAPI_KEY", "JSEARCH_API_KEY")
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"
API_URL = f"https://{RAPIDAPI_HOST}/search-v2"

REQUEST_TIMEOUT = 25      # seconds
DESCRIPTION_LIMIT = 150   # characters shown on each card
MAX_QUERY_LENGTH = 100

# --- 195 COUNTRIES - SIRF YE NAYA HISSA LAGAYA HAI ---
COUNTRY_CODES = {
    "afghanistan": "af", "albania": "al", "algeria": "dz", "andorra": "ad", "angola": "ao",
    "antigua and barbuda": "ag", "argentina": "ar", "armenia": "am", "australia": "au", "austria": "at",
    "azerbaijan": "az", "bahamas": "bs", "bahrain": "bh", "bangladesh": "bd", "barbados": "bb",
    "belarus": "by", "belgium": "be", "belize": "bz", "benin": "bj", "bhutan": "bt",
    "bolivia": "bo", "bosnia": "ba", "bosnia and herzegovina": "ba", "botswana": "bw", "brazil": "br", "brunei": "bn",
    "bulgaria": "bg", "burkina faso": "bf", "burundi": "bi", "cambodia": "kh", "cameroon": "cm",
    "canada": "ca", "cape verde": "cv", "central african republic": "cf", "chad": "td", "chile": "cl",
    "china": "cn", "colombia": "co", "comoros": "km", "congo": "cg", "costa rica": "cr",
    "croatia": "hr", "cuba": "cu", "cyprus": "cy", "czech republic": "cz", "czechia": "cz", "denmark": "dk",
    "djibouti": "dj", "dominica": "dm", "dominican republic": "do", "ecuador": "ec", "egypt": "eg",
    "el salvador": "sv", "equatorial guinea": "gq", "eritrea": "er", "estonia": "ee", "eswatini": "sz",
    "ethiopia": "et", "fiji": "fj", "finland": "fi", "france": "fr", "gabon": "ga",
    "gambia": "gm", "georgia": "ge", "germany": "de", "ghana": "gh", "greece": "gr",
    "grenada": "gd", "guatemala": "gt", "guinea": "gn", "guinea-bissau": "gw", "guyana": "gy",
    "haiti": "ht", "honduras": "hn", "hungary": "hu", "iceland": "is", "india": "in",
    "indonesia": "id", "iran": "ir", "iraq": "iq", "ireland": "ie", "israel": "il",
    "italy": "it", "jamaica": "jm", "japan": "jp", "jordan": "jo", "kazakhstan": "kz",
    "kenya": "ke", "kiribati": "ki", "kuwait": "kw", "kyrgyzstan": "kg", "laos": "la",
    "latvia": "lv", "lebanon": "lb", "lesotho": "ls", "liberia": "lr", "libya": "ly",
    "liechtenstein": "li", "lithuania": "lt", "luxembourg": "lu", "madagascar": "mg", "malawi": "mw",
    "malaysia": "my", "maldives": "mv", "mali": "ml", "malta": "mt", "marshall islands": "mh",
    "mauritania": "mr", "mauritius": "mu", "mexico": "mx", "micronesia": "fm", "moldova": "md",
    "monaco": "mc", "mongolia": "mn", "montenegro": "me", "morocco": "ma", "mozambique": "mz",
    "myanmar": "mm", "namibia": "na", "nauru": "nr", "nepal": "np", "netherlands": "nl",
    "holland": "nl", "new zealand": "nz", "nicaragua": "ni", "niger": "ne", "nigeria": "ng", "north korea": "kp",
    "north macedonia": "mk", "norway": "no", "oman": "om", "pakistan": "pk", "palau": "pw",
    "palestine": "ps", "panama": "pa", "papua new guinea": "pg", "paraguay": "py", "peru": "pe",
    "philippines": "ph", "poland": "pl", "portugal": "pt", "qatar": "qa", "romania": "ro",
    "russia": "ru", "rwanda": "rw", "saint kitts": "kn", "saint lucia": "lc", "saint vincent": "vc",
    "samoa": "ws", "san marino": "sm", "sao tome": "st", "saudi arabia": "sa", "saudi": "sa", "senegal": "sn",
    "serbia": "rs", "seychelles": "sc", "sierra leone": "sl", "singapore": "sg", "slovakia": "sk",
    "slovenia": "si", "solomon islands": "sb", "somalia": "so", "south africa": "za", "south korea": "kr",
    "korea": "kr", "south sudan": "ss", "spain": "es", "sri lanka": "lk", "sudan": "sd", "suriname": "sr",
    "sweden": "se", "switzerland": "ch", "syria": "sy", "taiwan": "tw", "tajikistan": "tj",
    "tanzania": "tz", "thailand": "th", "timor-leste": "tl", "togo": "tg", "tonga": "to",
    "trinidad": "tt", "trinidad and tobago": "tt", "tunisia": "tn", "turkey": "tr", "turkiye": "tr", "turkmenistan": "tm", "tuvalu": "tv",
    "uganda": "ug", "ukraine": "ua", "uae": "ae", "dubai": "ae", "abu dhabi": "ae", "uk": "gb",
    "england": "gb", "britain": "gb", "great britain": "gb", "usa": "us", "america": "us", "united states": "us", "us": "us", "uruguay": "uy",
    "uzbekistan": "uz", "vanuatu": "vu", "vatican": "va", "venezuela": "ve", "vietnam": "vn",
    "yemen": "ye", "zambia": "zm", "zimbabwe": "zw", "azad kashmir": "pk", "kashmir": "pk"
}

def parse_country_from_query(query):
    """User ke likhe query se country nikal kar uska code aur saaf query wapas kare."""
    low = " " + query.lower().strip() + " "
    # Lambi wale naam pehle check karo, taake 'south korea' pehle pakda jaye, sirf 'korea' nahi
    for name in sorted(COUNTRY_CODES.keys(), key=len, reverse=True):
        if f" {name} " in low or low.strip() == name or low.strip().endswith(f" {name}") or low.strip().startswith(f"{name} "):
            # country ka naam query se hata do taake sirf job title bache, jaise 'Accountant Canada' -> 'Accountant'
            cleaned = low.replace(f" {name} ", " ").strip()
            # 'in' jaisa chota lafz bhi hata do, jaise 'Accountant in Canada'
            cleaned = " ".join([w for w in cleaned.split() if w != "in"])
            if not cleaned:
                cleaned = query
            return cleaned, COUNTRY_CODES[name]
    return query, "us"

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥", "CNY": "¥",
    "CAD": "CA$", "AUD": "A$", "NZD": "NZ$", "CHF": "CHF ", "SGD": "S$",
    "AED": "AED ", "SAR": "SAR ", "PKR": "Rs ", "BRL": "R$", "ZAR": "R ",
}
SALARY_PERIODS = {
    "YEAR": "year", "MONTH": "month", "WEEK": "week", "DAY": "day", "HOUR": "hour",
}
EMPLOYMENT_LABELS = {
    "FULLTIME": "Full Time",
    "FULL_TIME": "Full Time",
    "PARTTIME": "Part Time",
    "PART_TIME": "Part Time",
    "CONTRACTOR": "Contract",
    "CONTRACT": "Contract",
    "TEMPORARY": "Contract",
    "INTERN": "Internship",
    "INTERNSHIP": "Internship",
}
POPULAR_SEARCHES = [
    "Software Developer",
    "Data Analyst",
    "Project Manager",
    "Registered Nurse",
    "Marketing Manager",
    "Accountant",
]

class JobSearchError(Exception):
    """Raised with the real, user-readable reason a job search failed."""



def get_api_key():
    """Return (key, variable_name) from the environment / .env, or ('', None)."""
    for name in API_KEY_NAMES:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value, name
    return "", None

def clean_text(value):
    """Collapse whitespace and return a plain string."""
    if not value or not isinstance(value, str):
        return ""
    return " ".join(value.split())

def truncate(text, limit=DESCRIPTION_LIMIT):
    """Trim text to `limit` characters, preferring a word boundary."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    if " " in cut[limit // 2:]:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:-") + "…"

def safe_url(url):
    """Only allow http(s) links so we never render javascript: URLs."""
    if not url or not isinstance(url, str):
        return ""
    parsed = urlparse(url.strip())
    return url.strip() if parsed.scheme in ("http", "https") and parsed.netloc else ""

def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'} ago"

def format_posted(job):
    """Turn the API timestamp into a friendly relative date."""
    raw = job.get("job_posted_at_datetime_utc")
    if raw and isinstance(raw, str):
        try:
            posted = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - posted
            days = delta.days
            if days < 0:
                return "Just now"
            if days == 0:
                hours = delta.seconds // 3600
                return "Just now" if hours < 1 else plural(hours, "hour")
            if days < 30:
                return plural(days, "day")
            if days < 365:
                return plural(days // 30, "month")
            return plural(days // 365, "year")
        except ValueError:
            pass
    return clean_text(job.get("job_posted_at")) or "Recently posted"

def format_amount(value, symbol):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return ""
    if value >= 10000:
        short = f"{value / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{symbol}{short}K"
    return f"{symbol}{value:,.0f}"

def format_salary(job):
    """Return e.g. '$80K – $120K / year', or '' when no salary is listed."""
    low, high = job.get("job_min_salary"), job.get("job_max_salary")
    if not low and not high:
        return ""
    currency = (job.get("job_salary_currency") or "USD").upper()
    symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    if low and high and low != high:
        amount = f"{format_amount(low, symbol)} – {format_amount(high, symbol)}"
    else:
        amount = format_amount(low or high, symbol)
    period = SALARY_PERIODS.get((job.get("job_salary_period") or "").upper())
    return f"{amount} / {period}" if period else amount

def job_types(job):
    """Build the list of badges: employment type(s) plus Remote."""
    raw_types = job.get("job_employment_types") or []
    if not raw_types and job.get("job_employment_type"):
        raw_types = [job["job_employment_type"]]

    labels = []
    for raw in raw_types:
        label = EMPLOYMENT_LABELS.get(str(raw).upper().replace(" ", "_"))
        if label and label not in labels:
            labels.append(label)
    if job.get("job_is_remote"):
        labels.append("Remote")
    return labels or ["Full Time"]

def build_location(job):
    parts = [clean_text(job.get(k)) for k in ("job_city", "job_state", "job_country")]
    location = ", ".join(p for p in parts if p)
    if not location:
        location = clean_text(job.get("job_location"))
    if not location and job.get("job_is_remote"):
        location = "Remote"
    return location or "Location not specified"

def normalize_job(raw):
    """Map one JSearch result onto the fields the template needs."""
    if not isinstance(raw, dict):
        return None
    # search-v2 sometimes nests the job inside "job" key
    if "job" in raw and isinstance(raw.get("job"), dict):
        raw = raw["job"]

    title = clean_text(raw.get("job_title") or raw.get("title") or raw.get("jobTitle"))
    if not title:
        return None

    
    apply_link = (
        safe_url(raw.get("job_apply_link"))
        or safe_url(raw.get("job_google_link"))
        or safe_url(raw.get("job_apply_url"))
        or safe_url(raw.get("apply_link"))
    )
    # search-v2 also puts links in job_apply_options list
    if not apply_link:
        options = raw.get("job_apply_options") or []
        for opt in options:
            if isinstance(opt, dict):
                link = safe_url(opt.get("apply_link") or opt.get("link") or opt.get("url"))
                if link:
                    apply_link = link
                    break
    if not apply_link:
        company_fallback = clean_text(raw.get("employer_name") or "")
        q = f"{title} {company_fallback} job apply".strip()
        apply_link = f"https://www.google.com/search?q={quote_plus(q)}"

    company = clean_text(raw.get("employer_name") or raw.get("company") or raw.get("employer")) or "Confidential Company"
    types = job_types(raw)
    description = truncate(clean_text(raw.get("job_description") or raw.get("description"))) or "No description provided."
    logo = safe_url(raw.get("employer_logo"))

    return {
        "title": title,
        "company": company,
        "initials": "".join(w[0] for w in company.split()[:2]).upper() or "?",
        "hue": sum(ord(c) for c in company) % 360,
        "logo": logo,
        "verified": bool(logo or raw.get("employer_website")),
        "location": build_location(raw),
        "types": types,
        "posted": format_posted(raw),
        "salary": format_salary(raw),
        "description": description,
        "apply_link": apply_link,
        "source": clean_text(raw.get("job_publisher")),
    }

def api_message(response):
    """Pull the human-readable message out of an API error response."""
    try:
        data = response.json()
    except ValueError:
        return clean_text(response.text)[:200]
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            err = err.get("message")
        text = data.get("message") or err or data.get("detail") or ""
        return clean_text(str(text))[:300]
    return ""

def describe_http_error(status, message):
    """Turn an HTTP status into the real reason shown to the user."""
    extra = f" Details: {message}" if message else ""
    if status == 401:
        return (f"API key is invalid or missing (HTTP 401). Check the key in your "
                f".env file.{extra}")
    if status == 403:
        return (f"Access denied (HTTP 403). This key is not subscribed to the JSearch "
                f"API on RapidAPI, or it was blocked. Open the JSearch page on RapidAPI "
                f"and subscribe to a plan (the free one is fine).{extra}")
    if status == 429:
        return (f"API limit reached (HTTP 429). Your RapidAPI quota or rate limit is "
                f"used up. Wait a bit or upgrade your plan.{extra}")
    if status == 404:
        return f"JSearch endpoint not found (HTTP 404). The API URL may have changed.{extra}"
    if status == 400 or status == 422:
        return f"JSearch rejected the search request (HTTP {status}).{extra}"
    if status >= 500:
        return (f"JSearch server error (HTTP {status}). The problem is on the API side, "
                f"not your key. Please retry in a minute.{extra}")
    return f"JSearch returned an unexpected response (HTTP {status}).{extra}"

def fetch_jobs(query):
    """Call JSearch and return a list of normalized jobs (or raise JobSearchError)."""
    api_key, key_name = get_api_key()
    if not api_key:
        logger.error("No API key found. Checked env vars %s (and %s)",
                     ", ".join(API_KEY_NAMES), ENV_FILE)
        raise JobSearchError(
            "API key is missing. Create a .env file next to app.py containing "
            "RAPIDAPI_KEY=your_key_here, then restart the server."
        )

    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": RAPIDAPI_HOST}
    # NAYA: query se country alag karo, taake usi country ki asli job aaye
    clean_query, country_code = parse_country_from_query(query)
    params = {
        "query": clean_query,
        "page": "1",
        "num_pages": "1",
        "country": country_code,
        "language": "en",
        "date_posted": "all",
    }

    logger.info("Searching JSearch for %r in country %s (key from %s, ends with ...%s)",
                clean_query, country_code, key_name, api_key[-4:])

    try:
        response = requests.get(
            API_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.Timeout:
        logger.exception("JSearch request timed out")
        raise JobSearchError(
            f"JSearch did not respond within {REQUEST_TIMEOUT} seconds. Please try again."
        )
    except requests.exceptions.ConnectionError as exc:
        logger.exception("Could not connect to JSearch")
        raise JobSearchError(
            "Could not connect to JSearch (network error). Check your internet, VPN or "
            f"firewall. Technical detail: {type(exc).__name__}."
        )
    except requests.exceptions.RequestException as exc:
        logger.exception("Unexpected request failure")
        raise JobSearchError(f"The request to JSearch failed: {type(exc).__name__}.")

    status = response.status_code
    message = api_message(response)
    logger.info("JSearch responded: HTTP %s", status)

    if status >= 400:
        logger.error("JSearch error | HTTP %s | message=%r | body=%s",
                     status, message, response.text[:500])
        raise JobSearchError(describe_http_error(status, message))

    try:
        payload = response.json()
    except ValueError:
        logger.error("JSearch returned non-JSON body: %s", response.text[:500])
        raise JobSearchError("JSearch returned a response that is not valid JSON.")

    if isinstance(payload, dict) and str(payload.get("status", "")).upper() == "ERROR":
        message = api_message(response) or "Unknown error"
        logger.error("JSearch reported an error in the body: %s", response.text[:500])
        raise JobSearchError(f"JSearch reported an error: {message}")

    
    results = None
    if isinstance(payload, list):
        results = payload
    elif isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = data.get("jobs") or data.get("results") or []
        if results is None:
            results = payload.get("jobs") or payload.get("results") or []

    jobs = []
    for item in results or []:
        if isinstance(item, dict):
            job = normalize_job(item)
            if job:
                jobs.append(job)
    logger.info("JSearch returned %d raw results, %d usable jobs", len(results or []), len(jobs))
    # Debug: if still 0, print one raw item keys to terminal so we can see shape
    if not jobs and results:
        logger.info("Sample raw item keys: %s", list(results[0].keys())[:15] if isinstance(results[0], dict) else type(results[0]))
    return jobs


@app.route("/", methods=["GET", "POST"])
def index():
    source = request.form if request.method == "POST" else request.args
    query = (source.get("query") or "").strip()[:MAX_QUERY_LENGTH]

    jobs, error = [], None
    searched = request.method == "POST" or bool(query)

    if searched:
        if not query:
            error = "Please enter a job title to start your search."
        else:
            try:
                jobs = fetch_jobs(query)
            except JobSearchError as exc:
                error = str(exc)
            except Exception as exc:  # never let the page crash
                logger.exception("Unhandled error during job search")
                error = f"Unexpected error: {type(exc).__name__}: {exc}"

    return render_template(
        "index.html",
        query=query,
        jobs=jobs,
        error=error,
        searched=searched,
        popular=POPULAR_SEARCHES,
    )

if __name__ == "__main__":
    key, key_name = get_api_key()
    print("-" * 60)
    print(f".env file : {'found' if ENV_FILE_FOUND else 'NOT found'} ({ENV_FILE})")
    if key:
        print(f"API key   : loaded from {key_name} (ends with ...{key[-4:]})")
    else:
        print("API key   : MISSING - add RAPIDAPI_KEY=your_key to the .env file")
    print("-" * 60)

    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
