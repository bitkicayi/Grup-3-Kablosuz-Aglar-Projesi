"""
LoPy4 Ana Program
Çarpışma farkındalıklı zamanlama ile adaptif veri iletimi
"""

import time
import machine
# MicroPython'da rastgele sayı üretimi
try:
    import urandom as random_module
except ImportError:
    try:
        import random as random_module
    except ImportError:
        # Fallback: basit rastgele sayı üretici
        class SimpleRandom:
            def __init__(self):
                self.seed_val = 0
            def seed(self, val):
                self.seed_val = val
            def randint(self, a, b):
                self.seed_val = (self.seed_val * 1103515245 + 12345) & 0x7fffffff
                return a + (self.seed_val % (b - a + 1))
        random_module = SimpleRandom()

from wifi_manager import WiFiManager
from channel_monitor import ChannelMonitor
from data_sender import DataSender
from ml_scheduler import MLScheduler

# Cihaz ID ayarla (her cihaz için farklı)
# ÖNEMLİ: Her LoPy4 cihazında bu değeri MANUEL olarak değiştir!
# Cihaz 1 için: DEVICE_ID_MANUAL = 1
# Cihaz 2 için: DEVICE_ID_MANUAL = 2
DEVICE_ID_MANUAL = 1 # None ise otomatik hesaplanır

if DEVICE_ID_MANUAL is not None:
    DEVICE_ID = DEVICE_ID_MANUAL
    print("Manuel Device ID:", DEVICE_ID)
else:
    # Otomatik ID hesaplama (MAC adresinden)
    try:
        import network
        wlan = network.WLAN()
        mac = wlan.mac()
        # MAC adresinin son 2 byte'ını kullan
        DEVICE_ID = (mac[4] << 8) + mac[5]  # Son 2 byte'dan ID oluştur
        print("MAC adresi:", mac)
        print("Otomatik Device ID:", DEVICE_ID)
    except:
        # Fallback: unique_id kullan
        unique_id_bytes = machine.unique_id()
        # Tüm byte'ların hash'i
        DEVICE_ID = sum(unique_id_bytes) % 1000
        print("Unique ID bytes:", unique_id_bytes)
        print("Otomatik Device ID:", DEVICE_ID)

def main():
    print("LoPy4 Adaptif Veri İletimi Baslatiyor...")
    print("Cihaz ID:", DEVICE_ID)

    # WiFi bağlantısı
    wifi = WiFiManager()
    if not wifi.connect():
        print("WiFi bağlantısı başarısız!")
        return

    # Kanal izleme başlat
    channel_monitor = ChannelMonitor(device_id=DEVICE_ID)
    channel_monitor.start()

    # RSSI ölçümünü başlat (periyodik olarak RSSI kaydet)
    # WiFi bağlantısından RSSI al ve kaydet
    try:
        rssi = wifi.get_rssi()
        if rssi:
            channel_monitor.record_rssi(rssi)
    except:
        pass

    # İlk WiFi scan'i yap (gerçek neighbor count ve channel occupancy için)
    try:
        print("WiFi ağları taranıyor...")
        networks = channel_monitor.scan_wifi_networks()
        print("Taranan ağ sayısı:", len(networks))
        if len(networks) > 0:
            print("Bulunan ağlar:")
            for net in networks[:5]:  # İlk 5 ağı göster
                try:
                    ssid = net[0].decode('utf-8') if isinstance(net[0], bytes) else net[0]
                    rssi_val = net[3] if len(net) > 3 else 'N/A'
                    print("  - SSID:", ssid, ", RSSI:", rssi_val, "dBm")
                except:
                    pass
    except Exception as e:
        print("İlk WiFi scan hatası:", e)

    # Veri gönderici
    data_sender = DataSender(
        device_id=DEVICE_ID,
        channel_monitor=channel_monitor
    )

    # ML tabanlı zamanlayıcı
    # model_path=None yaparak önce JSON modeli denemesini sağla
    scheduler = MLScheduler(
        device_id=DEVICE_ID,
        channel_monitor=channel_monitor,
        model_path=None  # None ise JSON modeli yükler
    )

    # Model yükleme durumunu kontrol et
    if scheduler.model_loaded:
        print("ML modeli basariyla yuklendi, tahminler model ile yapilacak")
    else:
        print("UYARI: ML modeli yuklenemedi, varsayilan delay (500ms) kullanilacak")

    # Ana döngü
    # Rastgele aralık ayarları (ms cinsinden)
    # ÇARPışMA OLUŞTURMAK İÇİN: Çok daha sık gönder (200-800ms)
    # Test için: 1000-4000ms arası rastgele (1-4 saniye)
    # Normal kullanım için: 20000-40000ms (20-40 saniye)
    MIN_INTERVAL_MS = 200   # Minimum bekleme süresi (çok sık gönder - çarpışma için)
    MAX_INTERVAL_MS = 800   # Maksimum bekleme süresi (çarpışma için)

    # Her cihaz için farklı rastgelelik için seed ayarla
    random_module.seed(DEVICE_ID + time.ticks_ms())

    # İlk rastgele aralığı hesapla
    data_interval_ms = random_module.randint(MIN_INTERVAL_MS, MAX_INTERVAL_MS)
    print("Baslangic veri araligi:", data_interval_ms, "ms (rastgele:", MIN_INTERVAL_MS, "-", MAX_INTERVAL_MS, "ms)")

    # İlk veri gönderim zamanını ayarla
    # İlk gönderim hemen yapılacak
    last_data_time = 0  # İlk gönderim için 0 (data_age=0 olacak)
    first_send = True  # İlk gönderim flag'i

    print("Ana dongu basladi, ilk veri hemen gonderilecek...")

    loop_count = 0
    while True:
        loop_count += 1
        current_time_ms = time.ticks_ms()

        # İlk gönderim için özel kontrol
        if first_send:
            time_diff = data_interval_ms  # Hemen gönder
        else:
            # Zaman farkını hesapla (overflow güvenli)
            time_diff = time.ticks_diff(current_time_ms, next_send_time)

            # Negatif ise henüz zaman gelmemiş
            if time_diff < 0:
                # Henüz zaman gelmemiş, kısa bekle ve devam et
                time.sleep_ms(10)
                # Her 1000 döngüde bir durum yazdır
                if loop_count % 1000 == 0:
                    print("Dongu calisiyor - Loop:", loop_count, "Bekleniyor... Time diff:", time_diff, "ms")
                continue

        # Zaman geldi, veri gönder
        print("Veri gonderim zamani geldi! Time diff:", time_diff, "ms")
        # Veri üret (simülasyon)
        data_age = 0  # Yeni üretilen veri
        # Öncelik seviyesini rastgele seç (1-3 arası)
        priority = random_module.randint(1, 3)

        # ML modelinden optimal bekleme süresini al
        optimal_delay = scheduler.get_optimal_delay(
            data_age=data_age,
            priority=priority
        )

        print("Optimal gecikme:", optimal_delay, "ms")

        # Bekleme süresini uygula
        # NOT: Model tahminlerini kullanmak için maksimum delay sınırını kaldırdık
        # Eğer çarpışma testi için sınırlama istersen, bu satırı aç:
        # max_delay_for_collision = 100
        # actual_delay = min(optimal_delay, max_delay_for_collision)
        actual_delay = optimal_delay

        if actual_delay > 0:
            print("Bekleme suresi uygulaniyor:", actual_delay, "ms")
            time.sleep_ms(int(actual_delay))
        else:
            print("Bekleme suresi 0, hemen gonderiliyor")

        # RSSI ölçümü yap ve kaydet
        try:
            rssi = wifi.get_rssi()
            if rssi:
                channel_monitor.record_rssi(rssi)
        except:
            pass

        # Veriyi gönder
        # Gönderim zamanını delay'den SONRA al (gerçek gönderim zamanı)
        current_send_time = time.ticks_ms()

        # Data age hesapla (son gönderimden bu yana geçen süre)
        actual_data_age = time.ticks_diff(current_send_time, last_data_time)
        # Negatif ise overflow olmuş, 0 yap
        if actual_data_age < 0:
            actual_data_age = 0
        print("Veri gonderiliyor - Data Age:", actual_data_age,
              "Priority:", priority, "Delay:", optimal_delay)
        success = data_sender.send_data(
            data_age=actual_data_age,
            priority=priority,
            delay_used=optimal_delay  # Kullanılan gecikmeyi gönder
        )
        print("Gonderim sonucu:", "BASARILI" if success else "BASARISIZ")

        # Sonucu scheduler'a da kaydet (ML için)
        # Not: Gerçek gönderim sonucu data_sender içinde channel_monitor'a kaydediliyor
        scheduler.record_transmission_result(success, optimal_delay)

        # Bir sonraki gonderim icin YENI rastgele aralik belirle
        data_interval_ms = random_module.randint(MIN_INTERVAL_MS, MAX_INTERVAL_MS)
        print("Sonraki gonderim:", data_interval_ms, "ms sonra")

        # Zamanı güncelle (gerçek gönderim zamanını kaydet - delay'den sonra)
        last_data_time = time.ticks_ms()
        # Bir sonraki gönderim zamanını hesapla
        next_send_time = last_data_time + data_interval_ms
        # Overflow kontrolü: next_send_time çok büyükse resetle
        if next_send_time < last_data_time:  # Overflow
            next_send_time = time.ticks_ms() + data_interval_ms
        first_send = False  # İlk gönderim tamamlandı
        print("DEBUG: last_data_time=", last_data_time, "next_send_time=", next_send_time, "data_interval_ms:", data_interval_ms)

        # Kısa bir bekleme (döngüyü yavaşlat)
        time.sleep_ms(10)  # 10ms bekle (daha hızlı kontrol için)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program sonlandırılıyor...")
    except Exception as e:
        print("Hata:", e)
