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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": f"{BASE_URL}/magazalarimiz"
    })

    print("1. Adım: Şehir listesi çekiliyor...")
    sehir_data = fetch_data(session, f"{BASE_URL}{API_URLS['sehirler']}")
    
    if not sehir_data or "cities" not in sehir_data:
        print("Şehirler alınamadı. Script durduruluyor.")
        return

    all_stores = []
    total_store_count = 0
    
    cities = sehir_data["cities"]
    print(f"Toplam {len(cities)} şehir bulundu.")

    for city in cities:
        print(f"\nİşleniyor: {city}")
        
        ilce_data = fetch_data(session, f"{BASE_URL}{API_URLS['ilceler']}", params={"city": city})
        
        if not ilce_data or "districts" not in ilce_data:
            print(f" - {city} için ilçeler alınamadı.")
            continue
        
        districts = ilce_data["districts"]
        
        for district in districts:
            print(f" - İlçe: {district} mağazaları çekiliyor...", end="", flush=True)
            magaza_data = fetch_data(session, f"{BASE_URL}{API_URLS['magazalar']}", params={"city": city, "district": district})
            
            if not magaza_data or not magaza_data.get("response", {}).get("status", False):
                print(" [veri yok]")
                continue
                
            subeler = magaza_data.get("response", {}).get("subeler", [])
            
            if not subeler:
                print(" [veri yok]")
                continue

            print(f" [{len(subeler)} mağaza bulundu]")

            for sube in subeler:
                # *** DÜZELTME: "YURTDIŞI" VE "TERS KOORDİNAT" SORUNU İÇİN ***
                # Verilerin doğru anahtarlara atandığından ve virgül yerine nokta kullanıldığından emin ol
                all_stores.append({
                    "id": sube.get("id"),
                    "name": sube.get("name"),
                    "address": sube.get("address"),
                    "city": city,
                    "district": district,
                    "latitude": str(sube.get("ltd")).replace(",", "."),  # ltd = Latitude (Enlem)
                    "longitude": str(sube.get("lng")).replace(",", ".") # lng = Longitude (Boylam)
                })
            total_store_count += len(subeler)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_stores, f, ensure_ascii=False, indent=4)
        
        print(f"\n--- BAŞARILI ---")
        print(f"Toplam {total_store_count} mağaza verisi '{OUTPUT_FILE}' dosyasına kaydedildi.")

    except IOError as e:
        print(f"Hata: '{OUTPUT_FILE}' dosyası yazılamadı. {e}")

if __name__ == "__main__":
    main()
