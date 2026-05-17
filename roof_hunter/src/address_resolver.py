"""
Validate / fully-resolve US addresses against the Census Bureau geocoder.

Why this matters
----------------
Our authoritative_storms.db contains a wide range of address quality:

  * Fully formed:        "3514 Vaughn Road, Montgomery, AL 36106"
  * Truncated:           "10057 , , Oklahoma 74084"   (house # but no street)
  * Highway-only:        "Highway 34, York, NE 68467" (no house #)
  * Municipal placeholder: "200 3rd St, Manhattan, KS 66502" (city-hall row,
                           paired with homeowner_name="Homeowner")

A row that is not resolvable by an authoritative geocoder is not callable
or searchable in Google Earth, period. This module wraps the Census
Bureau's public geocoder (free, no API key, TIGER/Line + PUMA backed) to:

  1. Forward-geocode `street, city, state zip` to a canonical
     `matchedAddress` plus lat/lon, and
  2. Tag the result so downstream code can drop / de-prioritize rows that
     the geocoder couldn't pin to a real parcel.

Reverse (coordinates → administrative context)
---------------------------------------------
The Census single-line REST API supports ``searchtype=coordinates`` only
under ``/geocoder/geographies/coordinates`` — it returns **geoLookup**
(polygons such as state, county, place, ZCTA when ``layers=all``), *not* a
street-level ``matchedAddress``. For strike lat/lon we therefore fetch ZCTA +
place + state here, then forward-geocode a candidate house+street (e.g. from
OpenStreetMap Nominatim in our ingest script) with :func:`resolve_one` so the
stored row is still **Census-validated** MAF/TIGER.

API reference: https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.pdf
Forward endpoint: https://geocoding.geo.census.gov/geocoder/locations/onelineaddress
Reverse geoLookup: https://geocoding.geo.census.gov/geocoder/geographies/coordinates

Calls are cached on disk (JSON) so repeated runs over the same call list
don't re-hit the service.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

CENSUS_GEOGRAPHIES_COORDINATES = (
    "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
)
CENSUS_ENDPOINT = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
DEFAULT_BENCHMARK = "Public_AR_Current"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent / ".address_cache.json"

# Heuristic: a street is "complete enough" to attempt forward geocoding if
# the part before the first comma starts with digits AND contains at least
# one non-digit token (i.e. there's a street word, not just a bare number).
_RE_HOUSE_NUM_LEAD = re.compile(r"^\s*\d+[A-Za-z]?\s+\S+")


@dataclass
class ResolvedAddress:
    input_address: str
    matched_address: str
    latitude: float
    longitude: float
    match_quality: str
    tiger_side: str
    is_residential_likely: bool
    resolution_status: str
    note: str = ""

    def gmaps_url(self) -> str:
        return f"https://www.google.com/maps/place/{self.latitude},{self.longitude}"


@dataclass
class CensusGeographyContext:
    """Administrative context at a lon/lat from Census geoLookup (layers=all)."""

    longitude: float
    latitude: float
    state_stusab: str
    zcta5: str
    place_name: str
    county_name: str
    raw_geographies_keys: tuple[str, ...]


def _call_census_geographies(lon: float, lat: float, timeout: float = 12.0, retries: int = 3) -> Optional[dict]:
    qs = urllib.parse.urlencode({
        "x": str(lon),
        "y": str(lat),
        "benchmark": DEFAULT_BENCHMARK,
        "vintage": "Current_Current",
        "layers": "all",
        "format": "json",
    })
    url = f"{CENSUS_GEOGRAPHIES_COORDINATES}?{qs}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "roof-hunter/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            time.sleep(0.6 * (attempt + 1))
    return None


def fetch_census_geography_context(longitude: float, latitude: float) -> Optional[CensusGeographyContext]:
    """
    Call ``/geocoder/geographies/coordinates`` with ``layers=all`` so ZCTA5 is
    included alongside state / place / county names.
    """
    payload = _call_census_geographies(longitude, latitude)
    if payload is None:
        return None
    geographies = (payload.get("result") or {}).get("geographies") or {}
    states = geographies.get("States") or []
    state_stusab = str((states[0] or {}).get("STUSAB") or "").strip().upper()

    zcta5 = ""
    zcta_layer = geographies.get("2020 Census ZIP Code Tabulation Areas") or []
    if zcta_layer:
        zcta5 = str((zcta_layer[0] or {}).get("ZCTA5") or "").strip()

    place_name = ""
    for key in ("Incorporated Places", "Census Designated Places"):
        block = geographies.get(key) or []
        if block:
            place_name = str((block[0] or {}).get("BASENAME") or "").strip()
            break

    county_name = ""
    counties = geographies.get("Counties") or []
    if counties:
        county_name = str((counties[0] or {}).get("BASENAME") or "").strip()

    keys = tuple(sorted(geographies.keys()))
    return CensusGeographyContext(
        longitude=longitude,
        latitude=latitude,
        state_stusab=state_stusab,
        zcta5=zcta5,
        place_name=place_name,
        county_name=county_name,
        raw_geographies_keys=keys,
    )


def _strip_redundant_state(street: str, city: str, state: str, zip_code: str) -> tuple[str, str, str, str]:
    s = street or ""
    c = city or ""
    st = (state or "").upper()
    z = zip_code or ""
    s = re.sub(r",\s*,", ", ", s).strip(" ,")
    s = re.sub(r"^(\d+[A-Za-z]?)\s*,\s*", r"\1 ", s)
    if c and st and re.search(rf",\s*{re.escape(c)}\s*,?\s*({re.escape(st)})?\s*\d*\s*$", s, re.IGNORECASE):
        s = re.sub(rf",\s*{re.escape(c)}.*$", "", s, flags=re.IGNORECASE).strip(" ,")
    if not c:
        m = re.search(r",\s*([A-Za-z][A-Za-z .'-]+)$", s)
        if m:
            c = m.group(1).strip()
            s = s[: m.start()].strip(" ,")
    return s, c, st, z


def _build_oneline(street: str, city: str, state: str, zip_code: str) -> str:
    parts: list[str] = []
    if street:
        parts.append(street.strip(" ,"))
    if city:
        parts.append(city.strip(" ,"))
    state_zip = " ".join(p for p in [state, zip_code] if p).strip()
    if state_zip:
        parts.append(state_zip)
    return ", ".join(parts)


def _looks_complete_for_geocode(street: str) -> bool:
    if not street:
        return False
    head = street.split(",", 1)[0]
    if not _RE_HOUSE_NUM_LEAD.match(head):
        return False
    return True


class AddressCache:
    def __init__(self, path: Path = DEFAULT_CACHE_PATH) -> None:
        self.path = path
        self._data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def get(self, key: str) -> Optional[ResolvedAddress]:
        v = self._data.get(key)
        if not v:
            return None
        return ResolvedAddress(**v)

    def put(self, key: str, value: ResolvedAddress) -> None:
        self._data[key] = asdict(value)

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")


def _call_census(oneline: str, timeout: float = 12.0, retries: int = 3) -> Optional[dict]:
    qs = urllib.parse.urlencode({
        "address": oneline,
        "benchmark": DEFAULT_BENCHMARK,
        "format": "json",
    })
    url = f"{CENSUS_ENDPOINT}?{qs}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "roof-hunter/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            time.sleep(0.6 * (attempt + 1))
    return None


def _is_residential_match(matched_address: str) -> bool:
    """
    Census doesn't tag residential vs commercial, but municipal/placeholder
    addresses tend to follow patterns we can spot: round house numbers on
    civic streets, "City Hall" / "Courthouse" tokens, etc. This is a
    best-effort flag, not a guarantee.
    """
    if not matched_address:
        return False
    upper = matched_address.upper()
    if any(tok in upper for tok in ("CITY HALL", "COURTHOUSE", "COURT HOUSE", "POST OFFICE")):
        return False
    head = matched_address.split(",", 1)[0]
    m = re.match(r"^\s*(\d+)\s+", head)
    if m:
        n = int(m.group(1))
        if n in {100, 200, 300, 400, 500} and re.search(
            r"\b(MAIN|MARKET|PIERRE|POYNTZ|JULIETTE|3RD|FIRST|SECOND|THIRD|CENTER|COURT)\b",
            upper,
        ):
            return False
    return True


def resolve_one(
    street: str,
    city: str,
    state: str,
    zip_code: str,
    cache: Optional[AddressCache] = None,
) -> ResolvedAddress:
    s, c, st, z = _strip_redundant_state(street, city, state, zip_code)
    oneline = _build_oneline(s, c, st, z)

    if cache is not None:
        hit = cache.get(oneline)
        if hit is not None:
            return hit

    if not _looks_complete_for_geocode(s):
        result = ResolvedAddress(
            input_address=oneline,
            matched_address="",
            latitude=0.0,
            longitude=0.0,
            match_quality="N/A",
            tiger_side="",
            is_residential_likely=False,
            resolution_status="unresolvable_no_street",
            note="street has no recognizable house# + street word, skipping geocode",
        )
        if cache is not None:
            cache.put(oneline, result)
        return result

    payload = _call_census(oneline)
    if payload is None:
        return ResolvedAddress(
            input_address=oneline,
            matched_address="",
            latitude=0.0,
            longitude=0.0,
            match_quality="N/A",
            tiger_side="",
            is_residential_likely=False,
            resolution_status="geocoder_unreachable",
        )

    matches = (payload.get("result") or {}).get("addressMatches") or []
    if not matches and c:
        # A Faker-generated city name ("Rubenville", "Jonathanside") confuses the
        # geocoder. Retry with street + state + zip only — TIGER ZIP+street is
        # usually enough to nail the parcel.
        fallback_oneline = _build_oneline(s, "", st, z)
        if fallback_oneline != oneline:
            payload2 = _call_census(fallback_oneline)
            if payload2 is not None:
                matches = (payload2.get("result") or {}).get("addressMatches") or []
                if matches:
                    oneline = fallback_oneline
    if not matches:
        result = ResolvedAddress(
            input_address=oneline,
            matched_address="",
            latitude=0.0,
            longitude=0.0,
            match_quality="No_Match",
            tiger_side="",
            is_residential_likely=False,
            resolution_status="no_match",
        )
        if cache is not None:
            cache.put(oneline, result)
        return result

    m = matches[0]
    coords = m.get("coordinates") or {}
    tiger = m.get("tigerLine") or {}
    matched_addr = m.get("matchedAddress", "")
    residential = _is_residential_match(matched_addr)

    result = ResolvedAddress(
        input_address=oneline,
        matched_address=matched_addr,
        latitude=float(coords.get("y") or 0.0),
        longitude=float(coords.get("x") or 0.0),
        match_quality="Exact" if len(matches) == 1 else "Multiple",
        tiger_side=str(tiger.get("side") or ""),
        is_residential_likely=residential,
        resolution_status="resolved" if residential else "resolved_municipal",
        note="" if residential else "matched but heuristically looks municipal/civic",
    )
    if cache is not None:
        cache.put(oneline, result)
    return result


__all__ = [
    "ResolvedAddress",
    "CensusGeographyContext",
    "AddressCache",
    "resolve_one",
    "fetch_census_geography_context",
    "DEFAULT_CACHE_PATH",
]
