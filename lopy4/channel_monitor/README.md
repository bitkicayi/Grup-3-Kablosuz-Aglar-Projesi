# Channel Monitor Modülü

## Genel Bakış

`channel_monitor.py` modülü, LoPy4 cihazında WiFi kanal durumunu izlemek ve analiz etmek için kullanılır. RSSI değerlerini, kanal doluluk oranını, çarpışma oranını ve komşu cihaz sayısını takip eder.

## Ana Sınıflar

### SimpleDeque

MicroPython uyumlu basit bir deque implementasyonu.

```python
class SimpleDeque:
    def __init__(self, maxlen=100):
        self.maxlen = maxlen
        self.items = []
```

**Metodlar:**
- `append(item)`: Yeni öğe ekler, maksimum uzunluk aşılırsa en eski öğeyi siler
- `__len__()`: Kuyruk uzunluğunu döndürür
- `__iter__()`: İterasyon desteği
- `__getitem__(index)`: İndeks ile erişim


### ChannelMonitor

Kanal durumu izleme sınıfı. WiFi kanalının durumunu sürekli izler ve ML modeli için özellikler hazırlar.

#### Başlatma

```python
channel_monitor = ChannelMonitor(
    device_id=1,
    window_size_ms=1000,
    collision_window=10
)
```

**Parametreler:**
- `device_id`: Cihaz kimliği
- `window_size_ms`: İzleme penceresi (milisaniye)
- `collision_window`: Çarpışma tespiti için pencere boyutu

#### Ana Metodlar

##### `start()`
İzlemeyi başlatır.

```python
channel_monitor.start()
# Çıktı: "Kanal izleme başlatıldı"
```

##### `record_rssi(rssi_value)`
RSSI değerini kaydeder.

```python
channel_monitor.record_rssi(-75)  # dBm cinsinden
```

##### `get_current_rssi()`
Mevcut RSSI değerini döndürür.

```python
rssi = channel_monitor.get_current_rssi()
# Örnek: -75.0 veya None
```

##### `get_average_rssi(window_ms=None)`
Ortalama RSSI değerini hesaplar.

```python
# Tüm geçmiş için ortalama
avg_rssi = channel_monitor.get_average_rssi()

# Son 5 saniye için ortalama
avg_rssi = channel_monitor.get_average_rssi(window_ms=5000)
```

##### `record_transmission(success, wait_time_ms=0)`
İletim sonucunu kaydeder (başarılı/başarısız).

```python
channel_monitor.record_transmission(
    success=True,
    wait_time_ms=200
)
```

##### `get_collision_rate()`
Son dönem çarpışma oranını hesaplar (0.0 - 1.0).

```python
collision_rate = channel_monitor.get_collision_rate()
```

##### `scan_wifi_networks()`
WiFi ağlarını tarar ve sonuçları kaydeder.

```python
networks = channel_monitor.scan_wifi_networks()
```

##### `get_channel_occupancy_rate()`
Kanal doluluk oranını hesaplar (0.0 - 1.0).

```python
occupancy = channel_monitor.get_channel_occupancy_rate()
```

**Hesaplama Yöntemi:**
- WiFi scan sonuçlarından çevredeki ağ sayısına göre tahmin
- Kendi aktivitelerimizi de dikkate alır
- Ağırlıklı ortalama: %70 scan sonuçları, %30 kendi aktivite

##### `record_channel_activity()`
Kanal aktivitesini kaydeder.

```python
channel_monitor.record_channel_activity()
```

##### `get_last_successful_transmission_time()`
Son başarılı iletim zamanını döndürür.

```python
last_time = channel_monitor.get_last_successful_transmission_time()
```

##### `get_average_wait_time()`
Ortalama bekleme süresini hesaplar.

```python
avg_wait = channel_monitor.get_average_wait_time()
```

##### `get_neighbor_count()`
Aktif komşu cihaz sayısını WiFi scanning ile ölçer.

```python
neighbors = channel_monitor.get_neighbor_count()
```

##### `get_features()`
ML modeli için özellik sözlüğü hazırlar.

```python
features = channel_monitor.get_features()
```

**Dönen Özellikler:**
```python
{
    'rssi': -75.0,                    # Mevcut RSSI
    'avg_rssi': -78.5,                # Ortalama RSSI (5 saniye)
    'channel_occupancy': 0.6,         # Kanal doluluk oranı
    'collision_rate': 0.3,            # Çarpışma oranı
    'neighbor_count': 2,              # Komşu cihaz sayısı
    'last_success_time': 12345678,    # Son başarılı iletim zamanı
    'avg_wait_time': 250.0            # Ortalama bekleme süresi
}
```

## Veri Yapıları

### RSSI Geçmişi
- `rssi_history`: RSSI değerleri (SimpleDeque, maxlen=100)
- `rssi_timestamps`: RSSI zaman damgaları (SimpleDeque, maxlen=100)

### İletim Geçmişi
- `transmission_history`: İletim sonuçları (SimpleDeque, maxlen=collision_window)
  - Format: `{'success': bool, 'timestamp': int, 'wait_time': int}`

### Kanal Aktivitesi
- `channel_activity`: Kanal aktivite kayıtları (SimpleDeque, maxlen=100)
- `channel_timestamps`: Aktivite zaman damgaları (SimpleDeque, maxlen=100)

### WiFi Scan Sonuçları
- `scan_results`: WiFi tarama sonuçları (SimpleDeque, maxlen=20)
- `scan_timestamps`: Tarama zaman damgaları (SimpleDeque, maxlen=20)
- `scan_interval_ms`: Tarama aralığı (varsayılan: 5000ms = 5 saniye)

## Kullanım Örneği

```python
from channel_monitor import ChannelMonitor
import time

# Kanal izleyici oluştur
monitor = ChannelMonitor(device_id=1, window_size_ms=1000)
monitor.start()

# RSSI kaydet
monitor.record_rssi(-75)

# WiFi ağlarını tara
networks = monitor.scan_wifi_networks()
print(f"Bulunan ağ sayısı: {len(networks)}")

# İletim kaydet
monitor.record_transmission(success=True, wait_time_ms=200)
monitor.record_transmission(success=False, wait_time_ms=100)

# İstatistikleri al
print(f"Çarpışma oranı: {monitor.get_collision_rate():.2%}")
print(f"Kanal doluluk: {monitor.get_channel_occupancy_rate():.2%}")
print(f"Komşu sayısı: {monitor.get_neighbor_count()}")

# ML için özellikleri hazırla
features = monitor.get_features()
print("ML Özellikleri:", features)
```

## Önemli Notlar

1. **WiFi Scanning**: Gerçek komşu sayısı ve kanal doluluk oranı için WiFi scanning kullanılır. Bu işlem 5 saniyede bir otomatik yapılır.

2. **Varsayılan Değerler**: Özellikler hazırlanırken None değerler varsayılanlarla değiştirilir:
   - RSSI: -80 dBm
   - Channel occupancy: 0.0
   - Collision rate: 0.0
   - Neighbor count: 0

3. **Zaman Yönetimi**: `time.ticks_ms()` kullanılır (MicroPython uyumlu). Overflow durumları için `time.ticks_diff()` kullanılır.

4. **Bellek Yönetimi**: SimpleDeque yapısı maksimum uzunluk sınırı ile bellek kullanımını kontrol eder.

## Bağımlılıklar

- `time`: Zaman işlemleri için
- `network`: WiFi scanning için (MicroPython)
