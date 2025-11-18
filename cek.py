import requests
import json
import re
from math import radians, sin, cos, sqrt, atan2

BASE_URL = "https://kurumsal.sokmarket.com.tr"
OUTPUT_FILE = "magazalar.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://kurumsal.sokmarket.com.tr/magazalarimiz"
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def fetch_json(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except:
        return None

def fetch_html_state():
    try:
        r = requests.get(f"{BASE_URL}/magazalarimiz", headers=HEADERS, timeout=20)
        r.raise_for_status()
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", r.text, re.DOTALL)
        if not match:
            return None
        return json.loads(match.group(1))
    except:
        return None

def get_from_api():
    cities_raw = fetch_json(f"{BASE_URL}/ajax/servis/sehirler")
    if not cities_raw or "response" not in cities_raw:
        return None

    stores = []
    for city_obj in cities_raw["response"]["sehirler"]:
        city = city_obj["sehir"]

        districts_raw = fetch_json(f"{BASE_URL}/ajax/servis/ilceler", {"city": city})
        if not districts_raw or "response" not in districts_raw:
            continue

        for d in districts_raw["response"]["ilceler"]:
            district = d["ilce"]

            mjson = fetch_json(
                f"{BASE_URL}/ajax/servis/magazalarimiz",
                {"city": city, "district": district}
            )

            if (
                not mjson
                or not mjson.get("response", {}).get("status", False)
            ):
                continue

            for s in mjson["response"]["subeler"]:
                stores.append({
                    "id": s["id"],
                    "name": s["name"],
                    "address": s["address"],
                    "city": city,
                    "district": district,
                    "latitude": float(str(s.get("lng")).replace(",", ".")),
                    "longitude": float(str(s.get("ltd")).replace(",", ".")),
                })

    return stores

def get_from_html(state):
    if not state or "stores" not in state:
        return None

    out = []
    for s in state["stores"]:
        out.append({
            "id": s["id"],
            "name": s["name"],
            "address": s["address"],
            "city": s["city"],
            "district": s["district"],
            "latitude": float(s["latitude"]),
            "longitude": float(s["longitude"]),
        })
    return out

def safe_write_empty_json():
    """Son fallback: boş fakat geçerli JSON üretir."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
    print("⚠ Veri alınamadı → Boş JSON oluşturuldu.")

def main():
    stores = get_from_api()

    if stores is None:
        html_state = fetch_html_state()
        stores = get_from_html(html_state)

    # API + HTML fallback başarısız → Boş JSON yaz ve çık
    if stores is None:
        safe_write_empty_json()
        return

    # Distance hesaplama
    USER_LAT = 41.016431
    USER_LNG = 28.955997
    for s in stores:
        s["distance_km"] = round(
            haversine(USER_LAT, USER_LNG, s["latitude"], s["longitude"]),
            2
        )

    stores.sort(key=lambda x: x["distance_km"])

    # JSON minify
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, separators=(",", ":"))

    print("🎉 Mağaza verileri başarıyla oluşturuldu.")

if __name__ == "__main__":
    main()
