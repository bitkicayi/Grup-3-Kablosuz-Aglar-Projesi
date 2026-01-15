# Data Collector Modülü - Veri Toplama Sunucusu

## Genel Bakış

`data_collector.py` modülü, LoPy4 cihazlarından gelen UDP paketlerini alan ve kaydeden bir sunucu uygulamasıdır. Çarpışma tespiti yapar, ACK paketleri gönderir ve tüm verileri CSV dosyasına kaydeder.

## Ana Sınıf

### DataCollector

UDP sunucu sınıfı cihazlardan gelen verileri toplar.

#### Başlatma

```python
from data_collector import DataCollector

collector = DataCollector(
    host='0.0.0.0',           # Tüm ağ arayüzlerinde dinle
    port=5000,                # Port numarası
    data_file='data/collected_data.csv'  # CSV dosya yolu
)
```

**Parametreler:**
- `host`: Dinlenecek IP adresi (varsayılan: '0.0.0.0' - tüm arayüzler)
- `port`: Port numarası (varsayılan: 5000)
- `data_file`: Veri kayıt dosyası yolu (varsayılan: 'data/collected_data.csv')

## Ana Metodlar

### `start()`

Sunucuyu başlatır ve paketleri dinlemeye başlar.

```python
collector.start()
```

**İşlem Adımları:**
1. UDP socket oluşturulur
2. Belirtilen host ve port'a bind edilir
3. Socket timeout ayarlanır
4. CSV dosyası başlatılır
5. Ana döngü başlar
6. KeyboardInterrupt ile durdurulabilir

**Örnek Kullanım:**
```python
collector = DataCollector()
try:
    collector.start()
except KeyboardInterrupt:
    print("Sunucu durduruldu")
```

**Çıktı:**
```
Veri toplama sunucusu başlatıldı: 0.0.0.0:5000
[12:34:56] BASARILI | ID:1 | RSSI:-75 | Doluluk:%60.0
```

### `_init_csv_file()`

CSV dosyasını başlatır (başlıkları yazar).

```python
collector._init_csv_file()
```

**CSV Başlıkları:**
```python
[
    'timestamp',           # Sunucu zaman damgası (ISO format)
    'device_id',           # Cihaz kimliği
    'data_age',            # Veri yaşı (ms)
    'priority',            # Öncelik (1-3)
    'rssi',                # RSSI değeri (dBm)
    'channel_occupancy',   # Kanal doluluk oranı (0.0-1.0)
    'collision_rate',      # Çarpışma oranı (0.0-1.0)
    'neighbor_count',      # Komşu cihaz sayısı
    'success',             # Başarı durumu (0: başarısız, 1: başarılı)
    'delay_used',          # Kullanılan gecikme (ms)
    'collision_detected'   # Çarpışma tespit edildi mi (0: hayır, 1: evet)
]
```

### `_process_packet(data, addr)`

Gelen paketi işler (ana işleme metodu).

```python
collector._process_packet(data_bytes, ('192.168.1.100', 5001))
```

**İşlem Adımları:**

1. **JSON Parse:**
   ```python
   packet = json.loads(data.decode('utf-8'))
   ```

2. **Paket Bilgilerini Al:**
   ```python
   device_id = packet.get('device_id', 'unknown')
   data_age = packet.get('data_age', 0)
   priority = packet.get('priority', 1)
   rssi_value = packet.get('rssi', -90)
   channel_occupancy = packet.get('channel_occupancy', 0.0)
   collision_rate = packet.get('collision_rate', 0.0)
   neighbor_count = packet.get('neighbor_count', 0)
   delay_used = packet.get('delay_used', 0)
   ```

3. **Çarpışma Tespiti:**
   ```python
   collision_detected = False
   for other_device_id, last_time in self.last_packet_times.items():
       if other_device_id != device_id:
           time_diff = abs(server_timestamp - last_time)
           if time_diff < self.collision_window_ms:  # 800ms
               collision_detected = True
               break
   ```

4. **İstatistikleri Güncelle:**
   ```python
   self.stats['total_received'] += 1
   if collision_detected:
       self.device_stats[device_id]['failed'] += 1
   else:
       self.device_stats[device_id]['received'] += 1
   ```

5. **CSV'ye Kaydet:**
   ```python
   row = [timestamp, device_id, data_age, priority, ...]
   self._save_to_csv(row)
   ```

6. **ACK Paketi Gönder:**
   ```python
   ack_packet = {
       'type': 'ack',
       'device_id': device_id,
       'success': 0 if collision_detected else 1,
       'collision_detected': 1 if collision_detected else 0
   }
   ```

**Çarpışma Tespiti:**
- Son 800ms içinde başka bir cihazdan paket geldi mi?
- Evet ise çarpışma tespit edilir
- Her cihaz için son paket zamanı tutulur

### `_save_to_csv(row)`

Veriyi CSV dosyasına kaydeder.

```python
row = [
    '2024-01-15T12:34:56.789',
    1,      # device_id
    1000,   # data_age
    2,      # priority
    -75,    # rssi
    0.6,    # channel_occupancy
    0.3,    # collision_rate
    2,      # neighbor_count
    1,      # success
    200,    # delay_used
    0       # collision_detected
]
collector._save_to_csv(row)
```

**Dosya Formatı:**
```csv
timestamp,device_id,data_age,priority,rssi,channel_occupancy,collision_rate,neighbor_count,success,delay_used,collision_detected
2024-01-15T12:34:56.789,1,1000,2,-75,0.6,0.3,2,1,200,0
2024-01-15T12:34:57.123,2,800,1,-80,0.7,0.4,3,0,300,1
```

### `_print_stats()`

İstatistikleri yazdırır (program sonlandığında).

```python
collector._print_stats()
```

**Çıktı Örneği:**
```
=== İstatistikler ===
Toplam alınan paket: 1500
Tespit edilen çarpışma: 45
Çarpışma oranı: 3.00%
Decode hataları: 2
İşleme hataları: 1

Cihaz bazında:
  Cihaz 1: 750 başarılı, 20 başarısız (97.4% başarı)
  Cihaz 2: 730 başarılı, 25 başarısız (96.7% başarı)
```

## Paket Formatları

### Gelen Paket (Cihazdan)

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
    "data": {
        "temperature": 25.5,
        "humidity": 60.0
    }
}
```

### ACK Paketi (Sunucudan)

```json
{
    "type": "ack",
    "device_id": 1,
    "timestamp": 12345679,
    "success": 1,
    "collision_detected": 0
}
```

**ACK Durumları:**
- `success: 1, collision_detected: 0` → Başarılı iletim
- `success: 0, collision_detected: 1` → Çarpışma tespit edildi
- `success: 1, collision_detected: 0` → Başarılı (çarpışma yok)

## Çarpışma Tespiti

### Algoritma

```python
collision_window_ms = 800  # 800ms pencere

for other_device_id, last_time in self.last_packet_times.items():
    if other_device_id != device_id:
        time_diff = abs(server_timestamp - last_time)
        if time_diff < collision_window_ms:
            collision_detected = True
            break
```

**Örnek Senaryo:**
```
Zaman: 1000ms → Cihaz 1 paket gönderir
Zaman: 1050ms → Cihaz 2 paket gönderir (50ms fark)
Sonuç: Çarpışma tespit edilir (50ms < 800ms)
```

### Temizleme

```python
# Eski kayıtları temizle (1 saniyeden eski)
current_time = server_timestamp
self.last_packet_times = {
    dev_id: ts for dev_id, ts in self.last_packet_times.items()
    if current_time - ts < 1000
}
```

## İstatistikler

### Global İstatistikler

```python
self.stats = {
    'total_received': 1500,      # Toplam alınan paket
    'collisions_detected': 45,    # Tespit edilen çarpışma
    'decode_errors': 2,          # JSON decode hataları
    'processing_errors': 1       # İşleme hataları
}
```

### Cihaz Bazında İstatistikler

```python
self.device_stats = {
    1: {'received': 750, 'failed': 20},
    2: {'received': 730, 'failed': 25}
}
```

## Kullanım Örneği

### Temel Kullanım

```python
from data_collector import DataCollector

# Sunucu oluştur
collector = DataCollector(
    host='0.0.0.0',
    port=5000,
    data_file='data/collected_data.csv'
)

# Sunucuyu başlat
try:
    collector.start()
except KeyboardInterrupt:
    print("\nSunucu durduruldu")
    collector._print_stats()
```

### Özel Port ve Dosya

```python
collector = DataCollector(
    host='192.168.1.100',  # Sadece bu IP'de dinle
    port=8080,             # Farklı port
    data_file='my_data.csv' # Farklı dosya
)
collector.start()
```

### Komut Satırından Çalıştırma

```bash
python data_collector.py
```

## Hata Yönetimi

### JSON Decode Hatası

```python
except json.JSONDecodeError as e:
    print(f"JSON hatasi: {e}")
    self.stats['decode_errors'] += 1
```

### İşleme Hatası

```python
except Exception as e:
    print(f"Paket isleme hatasi: {e}")
    self.stats['processing_errors'] += 1
```

### CSV Kayıt Hatası

```python
except Exception as e:
    print(f"CSV kayıt hatası: {e}")
```

### ACK Gönderim Hatası

```python
except Exception as e:
    print(f"ACK gonderim hatasi: {e}")
```

## CSV Veri Analizi

### Örnek CSV Satırı

```csv
2024-01-15T12:34:56.789,1,1000,2,-75,0.6,0.3,2,1,200,0
```

**Alanlar:**
- `timestamp`: `2024-01-15T12:34:56.789`
- `device_id`: `1`
- `data_age`: `1000` (ms)
- `priority`: `2`
- `rssi`: `-75` (dBm)
- `channel_occupancy`: `0.6` (60%)
- `collision_rate`: `0.3` (30%)
- `neighbor_count`: `2`
- `success`: `1` (başarılı)
- `delay_used`: `200` (ms)
- `collision_detected`: `0` (hayır)

### Python ile Analiz

```python
import pandas as pd

# CSV'yi oku
df = pd.read_csv('data/collected_data.csv')

# İstatistikler
print(f"Toplam paket: {len(df)}")
print(f"Başarı oranı: {df['success'].mean() * 100:.2f}%")
print(f"Çarpışma oranı: {df['collision_detected'].mean() * 100:.2f}%")
print(f"Ortalama RSSI: {df['rssi'].mean():.2f} dBm")
print(f"Ortalama delay: {df['delay_used'].mean():.2f} ms")

# Cihaz bazında
for device_id in df['device_id'].unique():
    device_df = df[df['device_id'] == device_id]
    success_rate = device_df['success'].mean() * 100
    print(f"Cihaz {device_id}: {success_rate:.2f}% başarı")
```

## Önemli Notlar

1. **Port Yönetimi**: Cihazlar farklı kaynak portları kullanır (`5000 + device_id`). ACK paketleri bu portlara gönderilir.

2. **Çarpışma Pencere**: 800ms pencere kullanılır. Bu süre içinde birden fazla cihazdan paket gelirse çarpışma tespit edilir.

3. **Zaman Damgası**: Hem cihaz zamanı (`packet['timestamp']`) hem de sunucu zamanı (`server_timestamp`) kullanılır. CSV'ye sunucu zamanı yazılır.

4. **Varsayılan Değerler**: Pakette eksik alanlar varsa varsayılan değerler kullanılır:
   - `rssi`: -90 dBm
   - `channel_occupancy`: 0.0
   - `collision_rate`: 0.0
   - `neighbor_count`: 0

5. **Non-blocking**: Socket timeout (1 saniye) ile non-blocking çalışır. KeyboardInterrupt ile durdurulabilir.

6. **Dosya Yönetimi**: CSV dosyası append modunda açılır. Program her çalıştığında yeni satırlar eklenir.

7. **ACK Gönderimi**: Her paket için ACK gönderilir. Cihaz bu ACK'i bekler ve çarpışma bilgisini alır.

## Bağımlılıklar

- `socket`: UDP socket işlemleri
- `json`: JSON parsing
- `time`: Zaman işlemleri
- `csv`: CSV dosya yazma
- `datetime`: Zaman damgası formatlama
- `collections.defaultdict`: İstatistik yönetimi
