# Data Sender Modülü

## Genel Bakış

`data_sender.py` modülü, LoPy4 cihazından sunucuya UDP üzerinden veri paketleri göndermek için kullanılır. ACK ile çarpışma tespiti yapar ve gerçek zamanlı kanal bilgilerini toplar.

## Ana Sınıf

### DataSender

UDP socket üzerinden veri gönderimi yapan sınıf.

#### Başlatma

```python
from data_sender import DataSender
from channel_monitor import ChannelMonitor

channel_monitor = ChannelMonitor(device_id=1)
data_sender = DataSender(
    device_id=1,
    channel_monitor=channel_monitor,
    server_ip="",
    server_port=5000
)
```

**Parametreler:**
- `device_id`: Cihaz kimliği
- `channel_monitor`: ChannelMonitor instance (kanal bilgileri için)
- `server_ip`: Sunucu IP adresi 
- `server_port`: Sunucu port numarası (varsayılan: 5000)

#### Ana Metodlar

##### `_connect()`
Sunucuya bağlanmak için socket oluşturur.

```python
success = data_sender._connect()
```

**Özellikler:**
- Her cihaz için farklı kaynak portu kullanır: `5000 + device_id`
- Socket timeout: 0.5 saniye (ACK için)
- UDP protokolü kullanır

##### `_wait_for_ack(timeout_ms=500)`
Sunucudan ACK paketi bekler.

```python
success, collision_detected = data_sender._wait_for_ack(timeout_ms=500)
```

**Dönen Değerler:**
- `(True, False)`: Başarılı iletim, çarpışma yok
- `(True, True)`: Çarpışma tespit edildi
- `(False, False)`: İletim başarısız
- `(None, None)`: Timeout (ACK gelmedi)

**ACK Paket Formatı:**
```json
{
    "type": "ack",
    "device_id": 1,
    "success": 1,
    "collision_detected": 0
}
```

##### `send_data(data_age, priority, delay_used=0, data=None)`
Veri paketi gönderir (ana metod).

```python
success = data_sender.send_data(
    data_age=1000,      # Veri yaşı (ms)
    priority=2,          # Öncelik (1-3)
    delay_used=200,      # Kullanılan gecikme (ms)
    data={"sensor": 25.5}  # Opsiyonel veri
)
```

**İşlem Adımları:**

1. **Socket Kontrolü**: Socket yoksa oluşturulur
2. **Gerçek Değerleri Alma**: Channel monitor'dan gerçek kanal bilgileri alınır:
   - RSSI değeri
   - Channel occupancy
   - Collision rate
   - Neighbor count

3. **RSSI Fallback**: Eğer channel monitor'dan RSSI alınamazsa WiFi scan yapılır:
   ```python
   networks = wlan.scan()
   # En yüksek RSSI değeri bulunur
   ```

4. **Paket Oluşturma**: JSON formatında paket hazırlanır:
   ```json
   {
       "device_id": 1,
       "timestamp": 12345678,
       "data_age": 1000,
       "priority": 2,
       "delay_used": 200,
       "rssi": -75,
       "channel_occupancy": 0.6,
       "collision_rate": 0.3,
       "neighbor_count": 2,
       "data": {"temperature": 25.5, "humidity": 60.0}
   }
   ```

5. **Gönderim**: UDP socket ile paket gönderilir

6. **ACK Bekleme**: Sunucudan ACK paketi beklenir (500ms timeout)

7. **Sonuç Kaydı**: Channel monitor'a iletim sonucu kaydedilir

**Dönen Değer:**
- `True`: İletim başarılı
- `False`: İletim başarısız

##### `_generate_sensor_data()`
Sensör verisi simüle eder 

```python
sensor_data = data_sender._generate_sensor_data()
```

**Dönen Format:**
```python
{
    'temperature': 25.5,
    'humidity': 60.0,
    'sensor_id': 'a1b2c3d4e5f6...'  # Unique ID hex
}
```

##### `close()`
Socket bağlantısını kapatır.

```python
data_sender.close()
```

## Paket Yapısı

### Gönderilen Paket

```python
packet = {
    'device_id': int,              # Cihaz ID
    'timestamp': int,              # Zaman damgası (ms)
    'data_age': int,               # Veri yaşı (ms)
    'priority': int,               # Öncelik (1-3)
    'delay_used': int,             # Kullanılan gecikme (ms)
    'rssi': int,                   # RSSI değeri (dBm)
    'channel_occupancy': float,     # Kanal doluluk oranı (0.0-1.0)
    'collision_rate': float,       # Çarpışma oranı (0.0-1.0)
    'neighbor_count': int,         # Komşu cihaz sayısı
    'data': dict                   # Opsiyonel veri
}
```

### ACK Paketi

```python
ack = {
    'type': 'ack',
    'device_id': int,
    'timestamp': int,
    'success': int,                # 1: başarılı, 0: başarısız
    'collision_detected': int      # 1: çarpışma var, 0: yok
}
```

## Kullanım Örneği

```python
from data_sender import DataSender
from channel_monitor import ChannelMonitor
import time

# Kanal izleyici oluştur
channel_monitor = ChannelMonitor(device_id=1)
channel_monitor.start()

# Veri gönderici oluştur
data_sender = DataSender(
    device_id=1,
    channel_monitor=channel_monitor,
    server_ip="10.236.55.246",
    server_port=5000
)

# RSSI kaydet (channel monitor'a)
channel_monitor.record_rssi(-75)

# Veri gönder
success = data_sender.send_data(
    data_age=1000,
    priority=2,
    delay_used=200
)

if success:
    print("Veri başarıyla gönderildi")
else:
    print("Veri gönderimi başarısız")

# Temizlik
data_sender.close()
```

## Gerçek Değer Toplama

Modül, channel monitor'dan gerçek kanal bilgilerini almaya çalışır:

1. **RSSI**: 
   - Önce channel monitor'dan alınır
   - Yoksa WiFi scan yapılır ve en yüksek RSSI bulunur
   - Son çare: varsayılan -90 dBm

2. **Channel Occupancy**: 
   - Channel monitor'dan alınır
   - Yoksa varsayılan 0.0

3. **Collision Rate**: 
   - Channel monitor'dan alınır
   - Yoksa varsayılan 0.0

4. **Neighbor Count**: 
   - Channel monitor'dan alınır
   - Yoksa varsayılan 0

**Debug Çıktıları:**
```
GERCEK RSSI: -75
GERCEK Channel Occupancy: 0.6
GERCEK Collision Rate: 0.3
GERCEK Neighbor Count: 2
```

## Hata Yönetimi

### Socket Hataları
- Socket oluşturma hatası: `False` döner. Hata yazdırılır
- Port çakışması: Sistem otomatik port seçer

### Gönderim Hataları
- Paket oluşturma hatası: `False` döner
- Gönderim hatası: `False` döner, channel monitor'a başarısız kaydedilir
- ACK timeout: `True` döner (UDP gönderimi başarılı sayılır)

### Varsayılan Değerler
Eğer gerçek değerler alınamazsa:
- RSSI: -90 dBm
- Channel occupancy: 0.0
- Collision rate: 0.0
- Neighbor count: 0

## Önemli Notlar

1. **Port Yönetimi**: Her cihaz için farklı kaynak portu kullanılır (`5000 + device_id`). Bu sayede port çakışması önlenir.

2. **ACK Mekanizması**: Sunucu, çarpışma tespit ederse ACK paketinde `collision_detected: 1` gönderir. Bu bilgi channel monitor'a kaydedilir.

3. **Timeout**: ACK bekleme süresi 500ms'dir.

4. **Kanal Aktivitesi**: Her başarılı gönderimde channel monitor'a aktivite kaydedilir.

5. **WiFi Scan Formatı**: Pycom LoPy4 için scan sonuçları tuple formatındadır:
   - `(ssid, bssid, sec, channel, rssi)` veya named tuple

## Bağımlılıklar

- `socket`: UDP socket işlemleri
- `time`: Zaman işlemleri
- `json`: JSON serileştirme
- `ubinascii`: Unique ID hex encoding
- `wifi_manager`: WiFi bağlantısı (import edilir ama kullanılmaz)
- `network`: WiFi scanning için
