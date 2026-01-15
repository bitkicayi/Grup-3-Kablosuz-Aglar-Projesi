# Main Modülü - Ana Program

## Genel Bakış

`main.py` modülü, LoPy4 cihazının ana programıdır. Adaptif veri iletimi sistemini koordine eder. WiFi bağlantısını yönetir, kanal durumunu izler, ML tabanlı zamanlama yapar ve veri paketlerini sunucuya gönderir.

## Program Akışı

### 1. Başlatma ve Yapılandırma

```python
# Cihaz ID ayarlama
DEVICE_ID_MANUAL = 1  # Her cihaz için farklı değer

# Otomatik ID hesaplama (MAC adresinden)
if DEVICE_ID_MANUAL is None:
    DEVICE_ID = (mac[4] << 8) + mac[5]
```

**Cihaz ID Seçenekleri:**
- Manuel: `DEVICE_ID_MANUAL = 1` (önerilen)
- Otomatik: MAC adresinden hesaplanır
- Fallback: Unique ID'den hash hesaplanır

### 2. Ana Fonksiyon: `main()`

#### 2.1. WiFi Bağlantısı

```python
wifi = WiFiManager()
if not wifi.connect():
    print("WiFi bağlantısı başarısız!")
    return
```

#### 2.2. Kanal İzleme Başlatma

```python
channel_monitor = ChannelMonitor(device_id=DEVICE_ID)
channel_monitor.start()

# İlk RSSI kaydı
rssi = wifi.get_rssi()
if rssi:
    channel_monitor.record_rssi(rssi)
```

#### 2.3. İlk WiFi Scan

```python
networks = channel_monitor.scan_wifi_networks()
print(f"Taranan ağ sayısı: {len(networks)}")
```

#### 2.4. Modül İnisiyalizasyonu

```python
# Veri gönderici
data_sender = DataSender(
    device_id=DEVICE_ID,
    channel_monitor=channel_monitor
)

# ML tabanlı zamanlayıcı
scheduler = MLScheduler(
    device_id=DEVICE_ID,
    channel_monitor=channel_monitor,
    model_path=None  # JSON modeli otomatik yüklenir
)
```

#### 2.5. Ana Döngü

```python
while True:
    # 1. Zaman kontrolü
    # 2. Veri üretimi
    # 3. ML tahmini (optimal delay)
    # 4. Gecikme uygulama
    # 5. RSSI ölçümü
    # 6. Veri gönderimi
    # 7. Sonuç kaydı
    # 8. Sonraki gönderim zamanını hesaplama
```

## Ana Döngü Detayları

### Zaman Yönetimi

```python
# Rastgele aralık ayarları
MIN_INTERVAL_MS = 200   # Minimum bekleme (ms)
MAX_INTERVAL_MS = 800   # Maksimum bekleme (ms)

# Rastgele aralık hesaplama
data_interval_ms = random_module.randint(MIN_INTERVAL_MS, MAX_INTERVAL_MS)
```

**Aralık Ayarları:**
- **Çarpışma testi**: 200-800ms (çok sık gönder)
- **Normal kullanım**: 20000-40000ms (20-40 saniye)
- **Test**: 1000-4000ms (1-4 saniye)

### Veri Üretimi

```python
# Veri yaşı (son gönderimden bu yana geçen süre)
data_age = time.ticks_diff(current_send_time, last_data_time)

# Öncelik seviyesi (rastgele)
priority = random_module.randint(1, 3)  # 1: düşük, 2: orta, 3: yüksek
```

### ML Tabanlı Zamanlama

```python
# Optimal gecikme hesaplama
optimal_delay = scheduler.get_optimal_delay(
    data_age=data_age,
    priority=priority
)

# Gecikme uygulama
if optimal_delay > 0:
    time.sleep_ms(int(optimal_delay))
```

**Delay Değerleri:**
- ML modeli tahmin eder (0-5000ms arası)
- Model yoksa varsayılan: 500ms
- Kural tabanlı mod: öncelik ve çarpışma oranına göre

### Veri Gönderimi

```python
success = data_sender.send_data(
    data_age=actual_data_age,
    priority=priority,
    delay_used=optimal_delay
)
```

**Gönderim Adımları:**
1. Gerçek kanal bilgileri toplanır (RSSI, occupancy, collision rate)
2. Paket oluşturulur
3. UDP ile gönderilir
4. ACK beklenir
5. Sonuç kaydedilir

### Sonuç Kaydı

```python
# Channel monitor'a kaydet (otomatik)
# Scheduler'a kaydet (ML için)
scheduler.record_transmission_result(success, optimal_delay)
```

## Rastgele Sayı Üretimi

MicroPython uyumlu rastgele sayı üretici:

```python
try:
    import urandom as random_module
except ImportError:
    try:
        import random as random_module
    except ImportError:
        # Fallback: SimpleRandom sınıfı
        class SimpleRandom:
            def randint(self, a, b):
                # LCG algoritması
                return a + (self.seed_val % (b - a + 1))
```

**Seed Ayarlama:**
```python
random_module.seed(DEVICE_ID + time.ticks_ms())
```

## Zaman Yönetimi Detayları

### Overflow Koruması

```python
# Zaman farkı hesaplama (overflow güvenli)
time_diff = time.ticks_diff(current_time_ms, next_send_time)

# Negatif ise henüz zaman gelmemiş
if time_diff < 0:
    time.sleep_ms(10)
    continue
```

### İlk Gönderim

```python
first_send = True
if first_send:
    time_diff = data_interval_ms  # Hemen gönder
    first_send = False
```

## Çıktı Örnekleri

### Başlatma

```
LoPy4 Adaptif Veri İletimi Baslatiyor...
Cihaz ID: 1
WiFi baglandi: ('192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8')
Kanal izleme başlatıldı
WiFi ağları taranıyor...
Taranan ağ sayısı: 5
ML modeli basariyla yuklendi, tahminler model ile yapilacak
Baslangic veri araligi: 450 ms (rastgele: 200 - 800 ms)
Ana dongu basladi, ilk veri hemen gonderilecek...
```

### Gönderim Döngüsü

```
Veri gonderim zamani geldi! Time diff: 450 ms
Optimal gecikme: 200 ms
Bekleme suresi uygulaniyor: 200 ms
GERCEK RSSI: -75
GERCEK Channel Occupancy: 0.6
GERCEK Collision Rate: 0.3
GERCEK Neighbor Count: 2
Veri gonderiliyor - Data Age: 450 Priority: 2 Delay: 200
Gonderim sonucu: BASARILI
Sonraki gonderim: 320 ms sonra
```

## Hata Yönetimi

### WiFi Bağlantı Hatası

```python
if not wifi.connect():
    print("WiFi bağlantısı başarısız!")
    return  # Program sonlanır
```

### Model Yükleme Hatası

```python
if scheduler.model_loaded:
    print("ML modeli basariyla yuklendi")
else:
    print("UYARI: ML modeli yuklenemedi, varsayilan delay (500ms) kullanilacak")
```

### Program Sonlandırma

```python
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program sonlandırılıyor...")
    except Exception as e:
        print("Hata:", e)
```

## Yapılandırma Parametreleri

### Cihaz ID

```python
DEVICE_ID_MANUAL = 1  # Her cihaz için farklı!
```

### Gönderim Aralıkları

```python
MIN_INTERVAL_MS = 200   # Minimum (ms)
MAX_INTERVAL_MS = 800   # Maksimum (ms)
```

### ML Model Yolu

```python
model_path=None  # Otomatik: 'models/model_micropython.json'
```

## Kullanım Örneği

```python
# main.py çalıştırma
# LoPy4 cihazında:
# >>> import main
# >>> main.main()
```

**Veya:**

```python
# main.py dosyasını doğrudan çalıştır
# REPL'de:
# >>> exec(open('main/main.py').read())
```

## Modül Bağımlılıkları

```python
from wifi_manager import WiFiManager
from channel_monitor import ChannelMonitor
from data_sender import DataSender
from ml_scheduler import MLScheduler
```

## Önemli Notlar

1. **Cihaz ID**: Her cihaz için `DEVICE_ID_MANUAL` değerini manuel olarak değiştirin!

2. **Zaman Aralıkları**: Çarpışma testi için kısa aralıklar (200-800ms), normal kullanım için uzun aralıklar (20-40 saniye) kullanın.

3. **ML Modeli**: Model yüklenemezse varsayılan delay (500ms) kullanılır.

4. **Overflow**: `time.ticks_ms()` overflow durumları için `time.ticks_diff()` kullanılır.

5. **RSSI Ölçümü**: Her gönderim öncesi RSSI ölçülür ve kaydedilir.

6. **ACK Mekanizması**: Sunucudan gelen ACK paketleri çarpışma tespiti için kullanılır.

