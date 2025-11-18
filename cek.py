import requests
import json
import re

BASE_URL = "https://kurumsal.sokmarket.com.tr"
OUTPUT_FILE = "magazalar.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://kurumsal.sokmarket.com.tr/magazalarimiz"
}

# ----------------------------------------------------
# 1) Güvenli JSON fetch
# ----------------------------------------------------
def fetch_json(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except:
        return None


# ----------------------------------------------------
# 2) HTML içindeki gömülü JS verisini parse et
# ----------------------------------------------------
def fetch_html_embedded_data():
    print("⚠ API başarısız → HTML fallback moduna geçiliyor...")

    try:
        r = requests.get(f"{BASE_URL}/magazalarimiz", headers=HEADERS, timeout=20)
        r.raise_for_status()
    except:
        print("❌ HTML veri okunamadı.")
        return None

    html = r.text

    # window.__INITIAL_STATE__ = {...}
    match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", html, re.DOTALL)
    if not match:
        print("❌ HTML içinde gömülü JSON bulunamadı.")
        return None

    try:
        state = json.loads(match.group(1))
        return state
    except:
        print("❌ Gömülü JSON parse edilemedi.")
        return None


# ----------------------------------------------------
# 3) API'den mağaza bilgisi çek
# ----------------------------------------------------
def get_from_api():
    print("🔍 API’den şehirler çekiliyor...")

    data = fetch_json(f"{BASE_URL}/ajax/servis/sehirler")
    if not data or "response" not in data:
        return None  # API fallback aktif olur

    cities = [c["sehir"] for c in data["response"]["sehirler"]]

    all_stores = []

    for city in cities:
        print(f"\n🏙 Şehir: {city}")

        ilce_data = fetch_json(f"{BASE_URL}/ajax/servis/ilceler", {"city": city})
        if not ilce_data or "response" not in ilce_data:
            print("  ❌ İlçeler alınamadı.")
            continue

        districts = [d["ilce"] for d in ilce_data["response"]["ilceler"]]

        for district in districts:
            print(f"  📍 İlçe: {district}...", end="", flush=True)

            store_data = fetch_json(
                f"{BASE_URL}/ajax/servis/magazalarimiz",
                {"city": city, "district": district}
            )

            if not store_data or not store_data.get("response", {}).get("status", False):
                print(" veri yok")
                continue

            subeler = store_data["response"].get("subeler", [])
            print(f" {len(subeler)} mağaza")

            for s in subeler:
                latitude = str(s.get("lng")).replace(",", ".")
                longitude = str(s.get("ltd")).replace(",", ".")

                all_stores.append({
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "address": s.get("address"),
                    "city": city,
                    "district": district,
                    "latitude": latitude,
                    "longitude": longitude
                })

    return all_stores


# ----------------------------------------------------
# 4) HTML fallback modunda veri çek
# ----------------------------------------------------
def get_from_html(state):
    print("🔄 HTML fallback verileri okunuyor...")

    all_stores = []

    cities = state.get("cities", [])
    districts_map = state.get("districts", {})
    stores = state.get("stores", [])

    for store in stores:
        lat = str(store.get("latitude")).replace(",", ".")
        lng = str(store.get("longitude")).replace(",", ".")

        all_stores.append({
            "id": store.get("id"),
            "name": store.get("name"),
            "address": store.get("address"),
            "city": store.get("city"),
            "district": store.get("district"),
            "latitude": lat,
            "longitude": lng
        })

    return all_stores


# ----------------------------------------------------
# 5) Main
# ----------------------------------------------------
def main():
    # Önce API’yi dene
    stores = get_from_api()

    if stores is None:
        # API çalışmadı → HTML fallback
        state = fetch_html_embedded_data()
        if not state:
            print("❌ Veri hiçbir kaynaktan alınamadı.")
            return

        stores = get_from_html(state)

    # JSON’a yaz
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=4)

    print("\n🎉 İşlem tamamlandı!")
    print(f"📦 Toplam {len(stores)} mağaza kaydedildi → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
