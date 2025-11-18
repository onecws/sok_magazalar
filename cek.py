import requests
import json
import os

# --- Ayarlar ---
BASE_URL = "https://kurumsal.sokmarket.com.tr"
API_URLS = {
    "sehirler": "/ajax/servis/sehirler",
    "ilceler": "/ajax/servis/ilceler",
    "magazalar": "/ajax/servis/magazalarimiz"
}
OUTPUT_FILE = "magazalar.json"
# --- ---


def fetch_data(session, url, params=None):
    """Belirtilen URL'den veri çeken yardımcı fonksiyon."""
    try:
        response = session.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Hata: {url} adresine ulaşılamadı. {e}")
        return None
    except json.JSONDecodeError:
        print(f"Hata: Geçersiz JSON yanıtı alındı: {url}")
        return None


def main():
    """Tüm mağaza verilerini çekip JSON dosyasına kaydeder."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/magazalarimiz"
    })

    print("1. Adım: Şehir listesi çekiliyor...")
    sehir_data = fetch_data(session, f"{BASE_URL}{API_URLS['sehirler']}")

    # --- DÜZELTME: cities değil response.sehirler ---
    if not sehir_data or "response" not in sehir_data or "sehirler" not in sehir_data["response"]:
        print("Şehirler alınamadı. Script durduruluyor.")
        return

    sehirler = [s.get("sehir") for s in sehir_data["response"]["sehirler"]]
    print(f"Toplam {len(sehirler)} şehir bulundu.")

    all_stores = []
    total_store_count = 0

    for city in sehirler:
        print(f"\nİşleniyor: {city}")

        ilce_data = fetch_data(session, f"{BASE_URL}{API_URLS['ilceler']}", params={"city": city})

        # --- DÜZELTME: districts değil response.ilceler ---
        if not ilce_data or "response" not in ilce_data or "ilceler" not in ilce_data["response"]:
            print(f" - {city} için ilçeler alınamadı.")
            continue

        ilceler = [i.get("ilce") for i in ilce_data["response"]["ilceler"]]

        for district in ilceler:
            print(f" - İlçe: {district} mağazaları çekiliyor...", end="", flush=True)

            magaza_data = fetch_data(session, f"{BASE_URL}{API_URLS['magazalar']}",
                                     params={"city": city, "district": district})

            if not magaza_data or not magaza_data.get("response", {}).get("status", False):
                print(" [veri yok]")
                continue

            subeler = magaza_data.get("response", {}).get("subeler", [])

            if not subeler:
                print(" [veri yok]")
                continue

            print(f" [{len(subeler)} mağaza bulundu]")

            for sube in subeler:

                # --- KOORDİNAT DÜZELTME ---
                # API:
                #   ltd = boylam
                #   lng = enlem
                # Biz:
                #   latitude = lng
                #   longitude = ltd

                raw_lng = sube.get("lng")  # enlem
                raw_ltd = sube.get("ltd")  # boylam

                latitude = str(raw_lng).replace(",", ".") if raw_lng else ""
                longitude = str(raw_ltd).replace(",", ".") if raw_ltd else ""

                all_stores.append({
                    "id": sube.get("id"),
                    "name": sube.get("name"),
                    "address": sube.get("address"),
                    "city": city,
                    "district": district,
                    "latitude": latitude,
                    "longitude": longitude
                })

            total_store_count += len(subeler)

    # JSON'a yaz
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_stores, f, ensure_ascii=False, indent=4)

        print("\n--- BAŞARILI ---")
        print(f"Toplam {total_store_count} mağaza verisi '{OUTPUT_FILE}' dosyasına kaydedildi.")

    except IOError as e:
        print(f"Hata: '{OUTPUT_FILE}' dosyası yazılamadı. {e}")


if __name__ == "__main__":
    main()
