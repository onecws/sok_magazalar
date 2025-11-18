import cloudscraper
import json
from math import radians, sin, cos, sqrt, atan2

BASE_URL = "https://kurumsal.sokmarket.com.tr"
OUTPUT_FILE = "magazalar.json"

scraper = cloudscraper.create_scraper(
    browser={
        "browser": "chrome",
        "platform": "windows",
        "mobile": False
    }
)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def get_json(url, params=None):
    try:
        r = scraper.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except:
        return None

def get_all_stores():
    cities_raw = get_json(f"{BASE_URL}/ajax/servis/sehirler")
    if not cities_raw or "response" not in cities_raw:
        return None

    stores = []
    for city_obj in cities_raw["response"]["sehirler"]:
        city = city_obj["sehir"]

        districts_raw = get_json(f"{BASE_URL}/ajax/servis/ilceler", {"city": city})
        if not districts_raw or "response" not in districts_raw:
            continue

        for d in districts_raw["response"]["ilceler"]:
            district = d["ilce"]

            mjson = get_json(
                f"{BASE_URL}/ajax/servis/magazalarimiz",
                {"city": city, "district": district}
            )

            if not mjson or not mjson.get("response", {}).get("status"):
                continue

            for s in mjson["response"]["subeler"]:
                stores.append({
                    "id": s["id"],
                    "name": s["name"],
                    "address": s["address"],
                    "city": city,
                    "district": district,
                    "latitude": float(str(s["lng"]).replace(",", ".")),
                    "longitude": float(str(s["ltd"]).replace(",", ".")),
                })

    return stores

def main():
    stores = get_all_stores()

    if stores is None:
        print("❌ Cloudflare API engelledi → Veri alınamadı.")
        with open(OUTPUT_FILE, "w") as f:
            json.dump([], f)
        return

    USER_LAT = 41.016431
    USER_LNG = 28.955997

    for s in stores:
        s["distance_km"] = round(
            haversine(USER_LAT, USER_LNG, s["latitude"], s["longitude"]),
            2
        )

    stores.sort(key=lambda x: x["distance_km"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, separators=(",", ":"))

    print("🎉 Mağaza verileri başarıyla alındı!")

if __name__ == "__main__":
    main()
