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
    """
    Belirtilen URL'den veri çeken yardımcı fonksiyon.
    Hata durumunda None döner.
    """
    try:
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"\n[HATA] İstek hatası: {e} | URL: {url}")
        return None
    except ValueError:
        print(f"\n[HATA] JSON parse edilemedi | URL: {url}")
        return None


def main():
    session = requests.Session()
    all_stores = []
    total_store_count = 0

    print("--- Şok Market Mağaza Verileri Çekiliyor ---")

    # 1) Şehirleri çek
    sehirler_data = fetch_data(session, f"{BASE_URL}{API_URLS['sehirler']}")
    if not sehirler_data or not sehirler_data.get("response", {}).get("sehirler"):
        print("[HATA] Şehir verisi çekilemedi veya boş.")
        return

    sehirler = sehirler_data.get("response", {}).get("sehirler", [])
    # API'de şehir yapısı genelde {'sehir': 'ADANA'} gibi
    cities = [s.get("sehir") for s in sehirler if s.get("sehir")]

    print(f"Toplam şehir sayısı: {len(cities)}")

    # 2) Her şehir için ilçeleri ve mağazaları çek
    for city in cities:
        print(f"\nŞehir: {city}")

        # İlçeler
        ilceler_data = fetch_data(
            session,
            f"{BASE_URL}{API_URLS['ilceler']}",
            params={"city": city}
        )

        if not ilceler_data or not ilceler_data.get("response", {}).get("ilceler"):
            print("  [HATA] İlçe verisi yok veya çekilemedi.")
            continue

        ilceler = ilceler_data.get("response", {}).get("ilceler", [])
        districts = [i.get("ilce") for i in ilceler if i.get("ilce")]

        # Her ilçe için mağazaları çek
        for district in districts:
            print(f" - İlçe: {district} mağazaları çekiliyor...", end="", flush=True)

            magaza_data = fetch_data(
                session,
                f"{BASE_URL}{API_URLS['magazalar']}",
                params={"city": city, "district": district}
            )

            # response.status false ise veya response yoksa
            if not magaza_data or not magaza_data.get("response", {}).get("status", False):
                print(" [veri yok]")
                continue

            subeler = magaza_data.get("response", {}).get("subeler", [])

            if not subeler:
                print(" [veri yok]")
                continue

            print(f" [{len(subeler)} mağaza bulundu]")

            for sube in subeler:
                # *** ÖNEMLİ DÜZELTME: Koordinatlar ters geldiği için swap yapıyoruz ***
                # API'deki:
                #   - sube['ltd']  ~ 35.xxx (boylam)
                #   - sube['lng']  ~ 37.xxx (enlem)
                #
                # Biz JSON'da:
                #   latitude  -> enlem  -> sube['lng']
                #   longitude -> boylam -> sube['ltd']

                raw_ltd = sube.get("ltd")
                raw_lng = sube.get("lng")

                latitude = str(raw_lng).replace(",", ".") if raw_lng is not None else ""
                longitude = str(raw_ltd).replace(",", ".") if raw_ltd is not None else ""

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

    # 3) Tüm mağazaları JSON'a yaz
    try:
        # İstersen tam path ile çalış:
        # output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
        output_path = OUTPUT_FILE

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_stores, f, ensure_ascii=False, indent=4)

        print("\n--- BAŞARILI ---")
        print(f"Toplam {total_store_count} mağaza verisi '{output_path}' dosyasına kaydedildi.")

    except IOError as e:
        print(f"[HATA] '{OUTPUT_FILE}' dosyası yazılamadı. Ayrıntı: {e}")


if __name__ == "__main__":
    main()
