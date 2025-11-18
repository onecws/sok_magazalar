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
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def fetch_json(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except:
        return None

def fetch_html():
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
    cities_data = fetch_json(f"{BASE_URL}/ajax/servis/sehirler")
    if not cities_data or "response" not in cities_data:
        return None

    cities = [c["sehir"] for c in cities_data["response"]["sehirler"]]
    all_stores = []

    for city in cities:
        ilce_data = fetch_json(f"{BASE_URL}/ajax/servis/ilceler", {"city": city})
        if not ilce_data or "response" not in ilce_data:
            continue
        districts = [d["ilce"] for d in ilce_data["response"]["ilceler"]]

        for district in districts:
            store_data = fetch_json(
                f"{BASE_URL}/ajax/servis/magazalarimiz",
                {"city": city, "district": district}
            )
            if not store_data or not store_data.get("response", {}).get("status", False):
                continue

            for s in store_data["response"]["subeler"]:
                lat = float(str(s.get("lng")).replace(",", "."))
                lng = float(str(s.get("ltd")).replace(",", "."))

                all_stores.append({
                    "id": s["id"],
                    "name": s["name"],
                    "address": s["address"],
                    "city": city,
                    "district": district,
                    "latitude": lat,
                    "longitude": lng,
                })

    return all_stores

def get_from_html(state):
    stores = []
    for s in state.get("stores", []):
        stores.append({
            "id": s["id"],
            "name": s["name"],
            "address": s["address"],
            "city": s["city"],
            "district": s["district"],
            "latitude": float(s["latitude"]),
            "longitude": float(s["longitude"]),
        })
    return stores

def main():
    stores = get_from_api()
    if stores is None:
        state = fetch_html()
        stores = get_from_html(state)

    USER_LAT = 41.016431
    USER_LNG = 28.955997

    for s in stores:
        s["distance_km"] = round(
            haversine(USER_LAT, USER_LNG, s["latitude"], s["longitude"]),
            2
        )

    stores = sorted(stores, key=lambda x: x["distance_km"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, separators=(",", ":"))

    print("OK")

if __name__ == "__main__":
    main()
