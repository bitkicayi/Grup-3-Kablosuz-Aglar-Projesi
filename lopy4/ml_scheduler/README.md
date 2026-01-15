# ML Scheduler Modülü

## Genel Bakış

`ml_scheduler.py` modülü, makine öğrenmesi tabanlı zamanlama yapar. Random Forest regresyon modeli kullanarak optimal bekleme süresini (delay) tahmin eder. İki mod destekler: kural tabanlı ve ML tabanlı zamanlama.

## Ana Sınıf

### MLScheduler

ML tabanlı optimal delay tahmin edici sınıf.

#### Başlatma

```python
from ml_scheduler import MLScheduler
from channel_monitor import ChannelMonitor

channel_monitor = ChannelMonitor(device_id=1)
scheduler = MLScheduler(
    device_id=1,
    channel_monitor=channel_monitor,
    model_path=None  # Otomatik: 'models/model_micropython.json'
)
```

**Parametreler:**
- `device_id`: Cihaz kimliği
- `channel_monitor`: ChannelMonitor instance
- `model_path`: Model dosya yolu (None ise otomatik yüklenir)

## Zamanlama Modları

### SCHEDULER_MODE

```python
SCHEDULER_MODE = 1  # 0: Kural tabanlı, 1: ML tabanlı
```

**Mod 0 - Kural Tabanlı:**
- Basit if-else kuralları
- Öncelik ve çarpışma oranına göre delay hesaplar
- ML modeli gerektirmez

**Mod 1 - ML Tabanlı:**
- Random Forest modeli kullanır
- Daha akıllı tahminler
- Model dosyası gerekir

## Ana Metodlar

### `get_optimal_delay(data_age, priority)`

Optimal bekleme süresini hesaplar (ana metod).

```python
delay = scheduler.get_optimal_delay(
    data_age=1000,  # Veri yaşı (ms)
    priority=2      # Öncelik (1-3)
)
```

**Dönen Değer:**
- `int`: Optimal bekleme süresi (ms), 0-5000 arası

**İşlem Akışı:**
1. Channel monitor'dan özellikleri topla
2. Mod kontrolü yap (SCHEDULER_MODE)
3. Kural tabanlı veya ML tabanlı tahmin yap
4. Sonucu döndür

### `_rule_based_scheduling(features, data_age, priority)`

Kural tabanlı zamanlama (baseline).

```python
delay = scheduler._rule_based_scheduling(
    features={'rssi': -75, 'collision_rate': 0.3, ...},
    data_age=1000,
    priority=2
)
```

**Kurallar:**

**Yüksek Öncelik (priority=3):**
- Collision rate > 0.5 → 200ms
- Collision rate > 0.3 → 100ms
- Diğer → 0ms

**Düşük Öncelik (priority=1):**
- Collision rate > 0.7 → 2000ms
- Collision rate > 0.5 → 1000ms
- Collision rate > 0.3 → 500ms
- Diğer → 200ms

**Orta Öncelik (priority=2):**
- Collision rate > 0.6 → 1000ms
- Collision rate > 0.4 → 500ms
- Collision rate > 0.2 → 200ms
- Diğer → 100ms

### `_predict_with_model(features, data_age, priority)`

ML modeli ile tahmin yapar.

```python
delay = scheduler._predict_with_model(
    features={'rssi': -75, ...},
    data_age=1000,
    priority=2
)
```

**İşlem Adımları:**
1. Özellik vektörünü hazırla
2. Model tahmini yap
3. Delay değerine dönüştür (0-5000ms)
4. Döndür

### `_prepare_feature_vector(features, data_age, priority)`

Model için özellik vektörünü hazırlar.

```python
feature_vector = scheduler._prepare_feature_vector(
    features={'rssi': -75, 'channel_occupancy': 0.6, ...},
    data_age=1000,
    priority=2
)
```

**Özellik Sırası:**
```python
[
    rssi,                    # Mevcut RSSI (dBm)
    channel_occupancy,       # Kanal doluluk (0.0-1.0)
    collision_rate,          # Çarpışma oranı (0.0-1.0)
    neighbor_count,          # Komşu sayısı
    trend_rssi,             # RSSI trend (avg - current)
    inter_arrival_time,      # Gönderimler arası süre (ms)
    data_age,               # Veri yaşı (ms)
    priority,               # Öncelik (1-3)
    hour                    # Saat (0-23)
]
```

**Hesaplanan Özellikler:**

**Trend RSSI:**
```python
trend_rssi = avg_rssi - current_rssi
# Pozitif: RSSI düşüyor (kötüleşiyor)
# Negatif: RSSI yükseliyor (iyileşiyor)
```

**Inter-arrival Time:**
```python
inter_arrival_time = data_age  # Şimdilik aynı
```

**Hour:**
```python
hour = (time.ticks_ms() // 3600000) % 24
```

### `_model_predict(feature_vector)`

Model ile tahmin yapar.

```python
prediction = scheduler._model_predict([-75, 0.6, 0.3, 2, ...])
# Örnek: 250.5 (ms)
```

**Desteklenen Model Formatları:**
1. JSON formatı (MicroPython uyumlu) - Öncelikli
2. sklearn pickle modeli (fallback)
3. Basit tree predict (fallback)

### `_predict_json_model(feature_vector)`

JSON formatındaki model ile tahmin yapar.

```python
delay = scheduler._predict_json_model([-75, 0.6, 0.3, ...])
```

**Model Formatı:**
```json
{
    "type": "RandomForestRegressor",
    "trees": [
        {
            "type": "node",
            "feature": "rssi",
            "threshold": -80.0,
            "left": {...},
            "right": {...}
        },
        ...
    ],
    "feature_names": ["rssi", "channel_occupancy", ...]
}
```

**Tahmin Süreci:**
1. Her ağaç için tahmin yap
2. Tüm ağaçların ortalamasını al
3. RandomForest: `avg = sum(predictions) / len(predictions)`

### `_predict_tree(tree_node, features)`

Tek bir ağaç ile recursive tahmin yapar.

```python
prediction = scheduler._predict_tree(tree_node, features)
```

**Ağaç Yapısı:**
```python
{
    "type": "node",           # veya "leaf"
    "feature": "rssi",        # Özellik adı
    "threshold": -80.0,      # Eşik değeri
    "left": {...},           # Sol alt ağaç
    "right": {...},          # Sağ alt ağaç
    "value": 250.0           # Leaf node için tahmin değeri
}
```

**Tahmin Algoritması:**
```python
if node['type'] == 'leaf':
    return node['value']
    
if features[node['feature']] <= node['threshold']:
    return predict_tree(node['left'], features)
else:
    return predict_tree(node['right'], features)
```

## Model Yükleme

### `load_json_model(json_path)`

JSON formatındaki modeli yükler (MicroPython uyumlu).

```python
scheduler.load_json_model('models/model_micropython.json')
```

**Özellikler:**
- `ujson` kullanır (daha hızlı)
- Fallback: `json` modülü
- Bellek kontrolü yapar
- Yükleme süresini ölçer

**Çıktı Örneği:**
```
JSON model yukleniyor: models/model_micropython.json
ujson kullaniliyor (hizli)
Dosya okunuyor...
Dosya okundu, parse ediliyor...
JSON model basariyla yuklendi!
  Agac sayisi: 100
  Yukleme suresi: 250 ms
  Dosya boyutu: ~ 45 KB
```

### `load_feature_names(feature_path)`

Özellik isimlerini yükler.

```python
scheduler.load_feature_names('models/model_features.pkl')
```

**Desteklenen Formatlar:**
- Pickle dosyası (upickle veya pickle)
- Varsayılan sıra (fallback)

**Varsayılan Özellik Sırası:**
```python
['rssi', 'channel_occupancy', 'collision_rate',
 'neighbor_count', 'trend_rssi', 'inter_arrival_time',
 'data_age', 'priority', 'hour']
```

## Sonuç Kaydı

### `record_transmission_result(success, delay_used)`

İletim sonucunu kaydeder (online öğrenme için).

```python
scheduler.record_transmission_result(
    success=True,
    delay_used=200
)
```

**Kaydedilen Bilgiler:**
- Channel monitor'a iletim sonucu
- Tahmin geçmişine ekleme
- Geçmiş temizleme (1000'den fazla ise)

**Prediction History Formatı:**
```python
{
    'success': True,
    'delay': 200,
    'timestamp': 12345678
}
```

## Kullanım Örneği

```python
from ml_scheduler import MLScheduler
from channel_monitor import ChannelMonitor

# Kanal izleyici
channel_monitor = ChannelMonitor(device_id=1)
channel_monitor.start()

# ML zamanlayıcı
scheduler = MLScheduler(
    device_id=1,
    channel_monitor=channel_monitor
)

# Model yükleme durumu
if scheduler.model_loaded:
    print("ML modeli yüklendi")
else:
    print("Varsayılan delay kullanılacak")

# Optimal delay hesaplama
delay = scheduler.get_optimal_delay(
    data_age=1000,
    priority=2
)
print(f"Optimal delay: {delay} ms")

# İletim sonucu kaydet
scheduler.record_transmission_result(
    success=True,
    delay_used=delay
)
```

## Model Formatı Detayları

### JSON Model Yapısı

```json
{
    "type": "RandomForestRegressor",
    "n_estimators": 100,
    "max_depth": 10,
    "feature_names": [
        "rssi",
        "channel_occupancy",
        "collision_rate",
        "neighbor_count",
        "trend_rssi",
        "inter_arrival_time",
        "data_age",
        "priority",
        "hour"
    ],
    "trees": [
        {
            "type": "node",
            "feature": "rssi",
            "threshold": -80.0,
            "left": {
                "type": "node",
                "feature": "collision_rate",
                "threshold": 0.5,
                "left": {"type": "leaf", "value": 500.0},
                "right": {"type": "leaf", "value": 200.0}
            },
            "right": {
                "type": "leaf",
                "value": 100.0
            }
        },
        ...
    ]
}
```

## Hata Yönetimi

### Model Yükleme Hataları

**Dosya Bulunamadı:**
```
HATA: JSON model dosyasi bulunamadi: models/model_micropython.json
```

**Bellek Yetersiz:**
```
HATA: Bellek yetersiz! Model cok buyuk.
Cozum: Model boyutunu kucult (daha az agac, daha az derinlik)
```

**Parse Hatası:**
```
HATA: JSON model yukleme basarisiz: ...
```

### Tahmin Hataları

**Model Yok:**
```python
# Varsayılan delay döner
return 500.0
```

**Özellik Hatası:**
```python
# Varsayılan değerler kullanılır
features.get('rssi', -80)
```

## Önemli Notlar

1. **Model Formatı**: Sadece JSON formatı kullanılır (pickle MicroPython'da sorunlu).

2. **Özellik Sırası**: Model özellik sırası `model_features.pkl` dosyasından alınır. Varsayılan sıra kullanılabilir.

3. **Delay Sınırları**: Tahmin edilen delay 0-5000ms arasına sınırlanır.

4. **Mod Seçimi**: `SCHEDULER_MODE` değişkeni ile kural tabanlı veya ML tabanlı mod seçilir.

5. **Online Öğrenme**: İletim sonuçları kaydedilir.

6. **Performans**: JSON model yükleme hızlıdır (ujson kullanır). Tahmin süresi ağaç sayısına bağlıdır.

## Bağımlılıklar

- `time`: Zaman işlemleri
- `ujson` veya `json`: JSON parsing
- `upickle` veya `pickle`: Özellik isimleri yükleme (opsiyonel)
