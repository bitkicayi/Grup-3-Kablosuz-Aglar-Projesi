# WiFi Manager Modülü

## Genel Bakış

`wifi_manager.py` modülü, Pycom LoPy4 cihazında WiFi bağlantısını yönetir. WiFi ağlarına bağlanma, bağlantı durumu kontrolü ve RSSI ölçümü yapar.

## Ana Sınıf

### WiFiManager

WiFi bağlantı yönetimi sınıfı.

#### Başlatma

```python
from wifi_manager import WiFiManager

# Varsayılan SSID ve şifre ile
wifi = WiFiManager()

# Özel SSID ve şifre ile
wifi = WiFiManager(
    ssid="MyWiFi",
    password="mypassword123"
)
```

**Parametreler:**
- `ssid`: WiFi ağ adı (None ise varsayılan: "Patates")
- `password`: WiFi şifresi (None ise varsayılan: "uzaylipatates36")

**ÖNEMLİ:** Kod içinde SSID ve şifreyi değiştirin:
```python
self.ssid = ssid or "Patates"  # Buraya kendi WiFi adınızı yazın
self.password = password or "uzaylipatates36"  # Buraya kendi şifrenizi yazın
```

## Ana Metodlar

### `connect(timeout=30)`

WiFi'ye bağlanır.

```python
success = wifi.connect(timeout=30)
```

**Parametreler:**
- `timeout`: Maksimum bekleme süresi (saniye), varsayılan: 30

**Dönen Değer:**
- `True`: Bağlantı başarılı
- `False`: Bağlantı başarısız (timeout veya hata)

**İşlem Adımları:**
1. Zaten bağlı mı kontrol et
2. WiFi modunu STA (Station) olarak ayarla
3. WPA2 ile bağlan
4. Bağlantı beklenir (timeout'a kadar)
5. IP yapılandırmasını göster

**Örnek Kullanım:**
```python
wifi = WiFiManager()
if wifi.connect():
    print("WiFi'ye başarıyla bağlandı")
    print(f"IP adresi: {wifi.get_ip()}")
else:
    print("WiFi bağlantısı başarısız!")
```

**Çıktı Örneği:**
```
WiFi'ye baglaniliyor: Patates
WiFi baglandi: ('192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8')
```

### `disconnect()`

WiFi bağlantısını keser.

```python
wifi.disconnect()
```

**Çıktı:**
```
WiFi baglantisi kesildi
```

### `get_rssi()`

Mevcut RSSI değerini alır (Pycom LoPy4 için scan kullanarak).

```python
rssi = wifi.get_rssi()
# Örnek: -75 (dBm) veya None
```

**Dönen Değer:**
- `int`: RSSI değeri (dBm), genellikle -100 ile 0 arası
- `None`: Bağlantı yok veya RSSI alınamadı

**İşlem Adımları:**
1. Bağlantı kontrolü
2. WiFi ağlarını tara (`wlan.scan()`)
3. En yüksek RSSI değerini bul
4. Döndür

**Pycom LoPy4 Scan Formatı:**
```python
# Tuple formatı: (ssid, bssid, sec, channel, rssi)
networks = [
    (b'WiFi_Network_1', b'\x00\x11\x22...', 3, 6, -65),
    (b'WiFi_Network_2', b'\x00\x33\x44...', 3, 11, -72)
]

# veya Named tuple formatı:
# net.rssi, net.ssid, net.channel, vb.
```

**RSSI Bulma Algoritması:**
```python
max_rssi = -100
for net in networks:
    if hasattr(net, 'rssi'):
        rssi_val = net.rssi  # Named tuple
    elif len(net) >= 5:
        rssi_val = net[4]    # Tuple (4. indeks)
    
    if rssi_val > max_rssi:
        max_rssi = rssi_val

return max_rssi if max_rssi > -100 else None
```

**Örnek Kullanım:**
```python
rssi = wifi.get_rssi()
if rssi:
    print(f"RSSI: {rssi} dBm")
    # RSSI değerlendirmesi:
    if rssi > -50:
        print("Mükemmel sinyal")
    elif rssi > -70:
        print("İyi sinyal")
    elif rssi > -85:
        print("Orta sinyal")
    else:
        print("Zayıf sinyal")
else:
    print("RSSI alınamadı")
```

### `is_connected()`

Bağlantı durumunu kontrol eder.

```python
if wifi.is_connected():
    print("WiFi'ye bağlı")
else:
    print("WiFi'ye bağlı değil")
```

**Dönen Değer:**
- `True`: Bağlı
- `False`: Bağlı değil

### `get_ip()`

IP adresini alır.

```python
ip = wifi.get_ip()
# Örnek: "192.168.1.100" veya None
```

**Dönen Değer:**
- `str`: IP adresi (örn: "192.168.1.100")
- `None`: Bağlantı yok

**IP Yapılandırması:**
```python
ifconfig = wlan.ifconfig()
# (ip, subnet, gateway, dns)
# Örnek: ('192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8')
```

## Kullanım Örneği

### Temel Kullanım

```python
from wifi_manager import WiFiManager

# WiFi yöneticisi oluştur
wifi = WiFiManager()

# Bağlan
if wifi.connect():
    print("Bağlantı başarılı!")
    
    # IP adresini al
    ip = wifi.get_ip()
    print(f"IP adresi: {ip}")
    
    # RSSI ölç
    rssi = wifi.get_rssi()
    print(f"RSSI: {rssi} dBm")
    
    # Bağlantı durumunu kontrol et
    if wifi.is_connected():
        print("Hala bağlı")
else:
    print("Bağlantı başarısız!")
```

### Özel SSID ve Şifre

```python
wifi = WiFiManager(
    ssid="MyNetwork",
    password="MyPassword123"
)

if wifi.connect(timeout=60):
    print("Bağlandı!")
```

### Sürekli Bağlantı Kontrolü

```python
import time

wifi = WiFiManager()
wifi.connect()

while True:
    if not wifi.is_connected():
        print("Bağlantı kesildi, yeniden bağlanılıyor...")
        wifi.connect()
    
    rssi = wifi.get_rssi()
    print(f"RSSI: {rssi} dBm")
    
    time.sleep(5)  # 5 saniyede bir kontrol et
```

## Hata Yönetimi

### Bağlantı Hataları

**Timeout:**
```python
if not wifi.connect(timeout=10):
    print("Bağlantı zaman aşımına uğradı")
```

**Yanlış Şifre:**
- Bağlantı başarısız olur, `connect()` `False` döner

**Ağ Bulunamadı:**
- Bağlantı başarısız olur, `connect()` `False` döner

### RSSI Hataları

**Bağlantı Yok:**
```python
rssi = wifi.get_rssi()
if rssi is None:
    print("RSSI alınamadı (bağlantı yok)")
```

**Scan Hatası:**
```python
try:
    rssi = wifi.get_rssi()
except Exception as e:
    print(f"RSSI alma hatası: {e}")
```

## Pycom LoPy4 Özellikleri

### WiFi Modu

```python
wlan = network.WLAN(mode=network.WLAN.STA)  # Station mode
```

**Modlar:**
- `WLAN.STA`: Station mode (başka ağa bağlanma)
- `WLAN.AP`: Access Point mode (kendi ağını oluşturma)

### Bağlantı Yöntemi

```python
wlan.connect(ssid="MyWiFi", auth=(network.WLAN.WPA2, "password"))
```

**Kimlik Doğrulama:**
- `WLAN.WPA2`: WPA2 şifreleme
- `WLAN.WPA`: WPA şifreleme
- `WLAN.WEP`: WEP şifreleme (eski, güvensiz)

### Scan Formatı

Pycom LoPy4'te scan sonuçları tuple veya named tuple formatında:

```python
# Tuple formatı (eski)
(ssid, bssid, sec, channel, rssi)

# Named tuple formatı (yeni)
# net.ssid, net.bssid, net.sec, net.channel, net.rssi
```

## Önemli Notlar

1. **SSID ve Şifre**: Kod içinde varsayılan değerleri kendi WiFi bilgilerinizle değiştirin!

2. **RSSI Ölçümü**: LoPy4'te direkt RSSI alma yok, scan kullanılır. En yüksek RSSI'li ağ genellikle bağlı olduğumuz ağdır.

3. **Bağlantı Kontrolü**: `is_connected()` her zaman güncel durumu döndürür.

4. **Timeout**: Bağlantı timeout'u saniye cinsinden. Uzun süreli bağlantılar için artırın.

5. **IP Yapılandırması**: `ifconfig()` tuple döndürür: `(ip, subnet, gateway, dns)`

6. **Bağlantı Kesme**: `disconnect()` çağrıldığında bağlantı kesilir, hata olsa bile program devam eder.

## Bağımlılıklar

- `network`: Pycom MicroPython WiFi modülü
- `time`: Zaman işlemleri (sleep, timeout)

## RSSI Değerlendirme

RSSI değerleri genellikle şu şekilde değerlendirilir:

| RSSI (dBm) | Sinyal Kalitesi |
|------------|----------------|
| > -50      | Mükemmel       |
| -50 to -70 | İyi            |
| -70 to -85 | Orta           |
| -85 to -100| Zayıf          |
| < -100     | Çok Zayıf      |

**Örnek:**
```python
rssi = wifi.get_rssi()
if rssi:
    if rssi > -50:
        quality = "Mükemmel"
    elif rssi > -70:
        quality = "İyi"
    elif rssi > -85:
        quality = "Orta"
    else:
        quality = "Zayıf"
    print(f"RSSI: {rssi} dBm ({quality})")
```
