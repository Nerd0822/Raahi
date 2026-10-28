"""External tools available to the AI, with a database-backed cache.

Three keyless sources:
- Open-Meteo for current weather and a short forecast
- DuckDuckGo HTML for current web results
- Wikipedia for historical and cultural background

Results are cached in `ToolCache` so repeated questions about the same place
don't hit the network again. Weather expires quickly; search and Wikipedia
last longer.
"""

import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from html import unescape
from html.parser import HTMLParser

from django.core.cache import cache
from django.utils import timezone

from .models import ToolCache

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)

CACHE_TTL = {
    "get_weather": timedelta(minutes=30),
    "search_web": timedelta(days=1),
    "get_wikipedia": timedelta(days=7),
}

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Current weather and a three-day forecast for a city or region. "
                "Use it for near-term trips, packing advice and outdoor plans."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or region, e.g. 'Jaipur' or 'Munnar'.",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web with DuckDuckGo for current facts: opening "
                "hours, ticket prices, closures, events and recent changes. "
                "Use short, specific queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'Amber Fort ticket price 2026'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wikipedia",
            "description": (
                "Look up a sourced summary from Wikipedia for history, "
                "architecture, culture or background on a place or landmark."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Place, monument or topic, e.g. 'Amber Fort'.",
                    }
                },
                "required": ["topic"],
            },
        },
    },
]

WMO = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


class ToolError(Exception):
    """A tool could not produce a usable result."""


def _get(url, timeout=15):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise ToolError(f"source returned {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ToolError(f"source unreachable: {exc}") from exc


def _get_json(url):
    try:
        return json.loads(_get(url))
    except json.JSONDecodeError as exc:
        raise ToolError("source returned invalid JSON") from exc


def _wmo(code):
    return WMO.get(code, f"Weather code {code}")


def _weather(args):
    location = str(args.get("location") or "").strip()
    if not location:
        raise ToolError("location is required")

    geo = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode(
            {"name": location, "count": 1, "language": "en", "format": "json"}
        )
    )
    places = geo.get("results") or []
    if not places:
        raise ToolError(f"could not find a place called {location}")
    place = places[0]

    forecast = _get_json(
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode(
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "wind_speed_10m,weather_code"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "forecast_days": 3,
                "timezone": "auto",
            }
        )
    )

    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}
    days = []
    for i, day in enumerate((daily.get("time") or [])[:3]):
        try:
            days.append(
                {
                    "date": day,
                    "condition": _wmo((daily.get("weather_code") or [])[i]),
                    "min_c": (daily.get("temperature_2m_min") or [])[i],
                    "max_c": (daily.get("temperature_2m_max") or [])[i],
                    "rain_chance": (
                        daily.get("precipitation_probability_max") or []
                    )[i],
                }
            )
        except IndexError:
            break

    label = ", ".join(
        value
        for value in [place.get("name"), place.get("admin1"), place.get("country")]
        if value
    )
    return {
        "location": label or location,
        "current": {
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "condition": _wmo(current.get("weather_code")),
        },
        "daily": days,
        "source": "Open-Meteo",
    }


class _DuckDuckGoParser(HTMLParser):
    """Pull titles, URLs and snippets out of DuckDuckGo's HTML results."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = []
        self.snippets = []
        self._mode = None
        self._text = []
        self._href = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self._mode = "title"
            self._text = []
            self._href = attrs.get("href") or ""
        elif "result__snippet" in classes:
            self._mode = "snippet"
            self._text = []

    def handle_data(self, data):
        if self._mode:
            self._text.append(data)

    def handle_endtag(self, tag):
        if not self._mode:
            return
        text = unescape(" ".join(self._text)).strip()
        text = " ".join(text.split())
        if self._mode == "title" and tag == "a":
            self.titles.append((text, _clean_ddg_url(self._href)))
            self._mode = None
        elif self._mode == "snippet" and tag in ("a", "div"):
            self.snippets.append(text)
            self._mode = None


def _clean_ddg_url(href):
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [None])[0]
        if target:
            return urllib.parse.unquote(target)
    return href


def _instant_answers(query):
    data = _get_json(
        "https://api.duckduckgo.com/?"
        + urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        )
    )
    results = []
    if data.get("AbstractText"):
        results.append(
            {
                "title": data.get("Heading") or query,
                "url": data.get("AbstractURL") or "",
                "snippet": data["AbstractText"][:500],
            }
        )
    for topic in (data.get("RelatedTopics") or [])[:4]:
        if isinstance(topic, dict) and topic.get("Text"):
            results.append(
                {
                    "title": topic["Text"].split(" - ")[0][:120],
                    "url": topic.get("FirstURL") or "",
                    "snippet": topic["Text"][:500],
                }
            )
    return results[:5]


def _search_web(args):
    query = str(args.get("query") or "").strip()
    if not query:
        raise ToolError("query is required")

    results = []
    try:
        html_text = _get(
            "https://html.duckduckgo.com/html/?"
            + urllib.parse.urlencode({"q": query})
        )
        parser = _DuckDuckGoParser()
        parser.feed(html_text)
        for i, (title, url) in enumerate(parser.titles[:5]):
            if title:
                results.append(
                    {
                        "title": title,
                        "url": url,
                        "snippet": (
                            parser.snippets[i] if i < len(parser.snippets) else ""
                        ),
                    }
                )
    except ToolError as exc:
        logger.info("DuckDuckGo HTML search failed: %s", exc)

    if not results:
        results = _instant_answers(query)

    return {"query": query, "results": results[:5], "source": "DuckDuckGo"}


def _wikipedia(args):
    topic = str(args.get("topic") or "").strip()
    if not topic:
        raise ToolError("topic is required")

    search = _get_json(
        "https://en.wikipedia.org/w/api.php?"
        + urllib.parse.urlencode(
            {
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "format": "json",
                "srlimit": 1,
            }
        )
    )
    hits = (search.get("query") or {}).get("search") or []
    if not hits:
        raise ToolError(f"no Wikipedia article found for {topic}")
    title = hits[0]["title"]

    summary = _get_json(
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote(title.replace(" ", "_"), safe="")
    )
    return {
        "title": summary.get("title") or title,
        "summary": (summary.get("extract") or "")[:1500],
        "description": summary.get("description") or "",
        "url": ((summary.get("content_urls") or {}).get("desktop") or {}).get(
            "page", ""
        ),
        "source": "Wikipedia",
    }


HANDLERS = {
    "get_weather": _weather,
    "search_web": _search_web,
    "get_wikipedia": _wikipedia,
}

CACHE_FIELDS = {
    "get_weather": "location",
    "search_web": "query",
    "get_wikipedia": "topic",
}


def _usable(name, data):
    """Only cache real answers; an empty or failed lookup should be retried."""
    if not isinstance(data, dict) or data.get("error"):
        return False
    if name == "search_web":
        return bool(data.get("results"))
    if name == "get_wikipedia":
        return bool(data.get("summary"))
    return name == "get_weather"


def _cache_key(name, query):
    # Hash the free text: Django warns about spaces/colons in cache keys, and
    # hashing also keeps long queries inside Redis/memcached limits.
    return f"tool:{name}:{hashlib.sha256(query.encode()).hexdigest()}"


def _cache_get(key):
    """Redis is a fast layer; an outage must not break the tool."""
    try:
        return cache.get(key)
    except Exception as exc:
        logger.debug("Tool cache read failed: %s", exc)
        return None


def _cache_set(key, data, timeout):
    try:
        cache.set(key, data, timeout=timeout)
    except Exception as exc:
        logger.debug("Tool cache write failed: %s", exc)


def execute_tool(name, arguments):
    """Run one tool call and cache its result. Never raises to the caller."""
    handler = HANDLERS.get(name)
    if not handler:
        return {"error": f"unknown tool: {name}"}
    if not isinstance(arguments, dict):
        arguments = {}

    field = CACHE_FIELDS.get(name)
    query = str(arguments.get(field) or "").strip().lower()[:300]
    key = _cache_key(name, query)
    try:
        if not query:
            raise ToolError(f"{field or 'query'} is required")

        cached_data = _cache_get(key)
        if cached_data is not None:
            return cached_data

        now = timezone.now()
        cached = ToolCache.objects.filter(tool=name, query=query).first()
        if cached and cached.expires_at > now and _usable(name, cached.data):
            _cache_set(
                key,
                cached.data,
                max(1, int((cached.expires_at - now).total_seconds())),
            )
            return cached.data

        data = handler(arguments)
        if _usable(name, data):
            ToolCache.objects.update_or_create(
                tool=name,
                query=query,
                defaults={
                    "data": data,
                    "expires_at": now + CACHE_TTL[name],
                },
            )
            _cache_set(key, data, int(CACHE_TTL[name].total_seconds()))
        return data
    except Exception as exc:  # a broken tool must not break the answer
        logger.warning("Tool %s failed for %r: %s", name, query, exc)
        return {"error": str(exc) or type(exc).__name__}
