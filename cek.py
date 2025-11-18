import requests
import json
import re
from math import radians, sin, cos, sqrt, atan2

BASE_URL = "https://kurumsal.sokmarket.com.tr"
OUTPUT_FILE = "magazalar.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://kurumsal.sokmarket.com.tr/magazalarimiz"
}

# --------------------------------------------------------
# Haversine (Mesafe hesaplama)
# --------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

# --------------------------------------------------------
# JSON fetch helper
# --------------------------------------------------------
def fetch_json(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except:
        return None

# --------------------------------------------------------
# HTML içindeki gömülü JS fallback sistemi
# --------------------------------------------------------
def fetch_html_embedded_data():
    print("⚠ API ERROR → HTML fallback kullanılıyor...")
    try:
        r = requests.get(f"{BASE_URL}/magazalarimiz", headers=HEADERS, timeout=20)
        r.raise_for_status()
    except:
        print("❌ HTML alınamadı.")
        return None

    match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", r.text, re.DOTALL)
    if not match:
        print("❌ HTML içinde mağaza verisi yok.")
        return None

    try:
        return json.loads(match.group(1))
    except:
        print("❌ JSON parse hatası (fallback).")
        return None

# --------------------------------------------------------
# GERÇEK API’dan veri çekme
# --------------------------------------------------------
def get_from_api():
    print("🔍 API’den şehirler çekiliyor...")

    data = fetch_json(f"{BASE_URL}/ajax/servis/sehirler")
    if not data or "response" not in data:
        return None

    cities = [c["sehir"] for c in data["response"]["sehirler"]]
    all_stores = []

    for city in cities:
        print(f"\n🏙 Şehir: {city}")

        ilce_data = fetch_json(f"{BASE_URL}/ajax/servis/ilceler", {"city": city})
        if not ilce_data or "response" not in ilce_data:
            print("  ❌ İlçeler bulunamadı")
            continue

        districts = [d["ilce"] for d in ilce_data["response"]["ilceler"]]

        for district in districts:
            print(f"  📍 İlçe: {district}...", end="", flush=True)

            store_data = fetch_json(
                f"{BASE_URL}/ajax/servis/magazalarimiz",
                {"city": city, "district": district}
            )

            if not store_data or not store_data.get("response", {}).get("status"):
                print(" veri yok")
                continue

            subeler = store_data["response"].get("subeler", [])
            print(f" {len(subeler)}")

            for s in subeler:
                latitude = str(s.get("lng")).replace(",", ".")
                longitude = str(s.get("ltd")).replace(",", ".")

                all_stores.append({
                    "id": s["id"],
                    "name": s["name"],
                    "address": s["address"],
                    "city": city,
                    "district": district,
                    "latitude": latitude,
                    "longitude": longitude
                })

    return all_stores

# --------------------------------------------------------
# Fallback: HTML kullanarak veri çekme
# --------------------------------------------------------
def get_from_html(state):
    print("🔄 HTML fallback verileri okunuyor...")

    stores = state.get("stores", [])
    all_stores = []

    for s in stores:
        all_stores.append({
            "id": s["id"],
            "name": s["name"],
            "address": s["address"],
            "city": s["city"],
            "district": s["district"],
            "latitude": str(s["latitude"]),
            "longitude": str(s["longitude"])
        })

    return all_stores

# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
def main():
    stores = get_from_api()

    if stores is None:
        state = fetch_html_embedded_data()
        if not state:
            print("❌ Veri alınamadı.")
            return
        stores = get_from_html(state)

    # ----------------------------------------------------
    # Kullanıcı konumu → sıralama
    # ----------------------------------------------------
    USER_LAT = 41.016431
    USER_LNG = 28.955997

    for s in stores:
        try:
            dist = haversine(USER_LAT, USER_LNG, float(s["latitude"]), float(s["longitude"]))
        except:
            dist = 999999

        s["distance_km"] = round(dist, 3)

    stores = sorted(stores, key=lambda x: x["distance_km"])

    # ----------------------------------------------------
    # JSON Minify yaz
    # ----------------------------------------------------
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n🎉 Tamamlandı! {len(stores)} mağaza kayıt edildi → magazalar.json")

if __name__ == "__main__":
    main()
