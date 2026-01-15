# Kablosuz Adaptif Veri İletimi Projesi

## Genel Bakış

Bu proje, Pycom LoPy4 cihazlarında çarpışma farkındalıklı zamanlama ile adaptif veri iletimi sistemini implemente eder. Makine öğrenmesi (ML) tabanlı zamanlama algoritması kullanarak WiFi kanalındaki çarpışmaları minimize eder ve veri iletim performansını optimize eder.

## Modüller

### LoPy4 Cihaz Modülleri

#### 1. [Channel Monitor](lopy4/channel_monitor)
WiFi kanal durumunu izler ve analiz eder. RSSI değerlerini, kanal doluluk oranını, çarpışma oranını ve komşu cihaz sayısını takip eder.

**Ana Özellikler:**
- RSSI geçmişi ve istatistikleri
- WiFi ağ tarama ve kanal doluluk hesaplama
- Çarpışma oranı takibi
- ML modeli için özellik hazırlama

#### 2. [Data Sender](lopy4/data_sender)
UDP üzerinden sunucuya veri paketleri gönderir. ACK mekanizması ile çarpışma tespiti yapar ve gerçek zamanlı kanal bilgilerini toplar.

**Ana Özellikler:**
- UDP socket yönetimi
- ACK bekleme ve çarpışma tespiti
- Gerçek kanal bilgileri toplama
- Paket oluşturma ve gönderim

#### 3. [Main Program](lopy4/main)
Ana program, tüm modülleri koordine eder. WiFi bağlantısını yönetir, kanal durumunu izler, ML tabanlı zamanlama yapar ve veri paketlerini gönderir.

**Ana Özellikler:**
- Modül koordinasyonu
- Zaman yönetimi ve overflow koruması
- ML tabanlı optimal delay hesaplama
- Veri gönderim döngüsü

#### 4. [ML Scheduler](lopy4/ml_scheduler)
Makine öğrenmesi tabanlı zamanlama yapar. Random Forest regresyon modeli kullanarak optimal bekleme süresini (delay) tahmin eder.

**Ana Özellikler:**
- Kural tabanlı ve ML tabanlı modlar
- JSON formatında model yükleme 
- Özellik vektörü hazırlama
- Online öğrenme desteği

#### 5. [WiFi Manager](lopy4/wifi_manager)
WiFi bağlantısını yönetir. WiFi ağlarına bağlanma, bağlantı durumu kontrolü ve RSSI ölçümü yapar.

**Ana Özellikler:**
- WiFi bağlantı yönetimi
- RSSI ölçümü 
- Bağlantı durumu kontrolü
- IP yapılandırması

### Sunucu Modülü

#### 6. [Data Collector](server)
LoPy4 cihazlarından gelen UDP paketlerini alan ve kaydeden sunucu uygulaması. Çarpışma tespiti yapar, ACK paketleri gönderir ve tüm verileri CSV dosyasına kaydeder.

**Ana Özellikler:**
- UDP sunucu
- Çarpışma tespiti algoritması
- ACK paketi gönderimi
- CSV veri kaydı
- İstatistik toplama

## Kurulum

### LoPy4 Cihaz Kurulumu

1. **Gerekli Dosyaları Yükleyin:**
   - Tüm `lopy4/` klasöründeki dosyaları LoPy4 cihazına yükleyin
   - Model dosyalarını (`models/` klasörü) yükleyin

2. **WiFi Ayarları:**
   - `wifi_manager/wifi_manager.py` dosyasında SSID ve şifreyi güncelleyin:
   ```python
   self.ssid = "YourWiFiName"
   self.password = "YourPassword"
   ```

3. **Cihaz ID Ayarlama:**
   - `main/main.py` dosyasında her cihaz için farklı ID ayarlayın:
   ```python
   DEVICE_ID_MANUAL = 1  # Her cihaz için farklı değer
   ```

4. **Sunucu IP Ayarlama:**
   - `data_sender/data_sender.py` dosyasında sunucu IP'sini güncelleyin:
   ```python
   server_ip="192.168.1.100"  # Sunucu IP adresi
   ```

### Sunucu Kurulumu

1. **Python Bağımlılıkları:**
   ```bash
   pip install pandas  # CSV analizi için (opsiyonel)
   ```

2. **Sunucuyu Başlatın:**
   ```bash
   cd server
   python data_collector.py
   ```

## Kullanım

### LoPy4 Cihazında Çalıştırma

```python
# REPL'de:
import main
main.main()
```

Veya dosyayı doğrudan çalıştırın.

### Sunucu Çalıştırma

```bash
cd server
python data_collector.py
```

Sunucu `0.0.0.0:5000` adresinde dinlemeye başlar.

## Veri Formatı

### Gönderilen Paket (Cihazdan)

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
    "data": {...}
}
```

### CSV Veri Formatı

Toplanan veriler `server/data/collected_data.csv` dosyasına kaydedilir:

```csv
timestamp,device_id,data_age,priority,rssi,channel_occupancy,collision_rate,neighbor_count,success,delay_used,collision_detected
2024-01-15T12:34:56.789,1,1000,2,-75,0.6,0.3,2,1,200,0
```

## ML Modeli

Proje, Random Forest regresyon modeli kullanarak optimal delay tahmini yapar. Model JSON formatında saklanır (`models/model_micropython.json`) ve MicroPython uyumludur.

**Model Özellikleri:**
- RSSI
- Channel occupancy
- Collision rate
- Neighbor count
- Trend RSSI
- Inter-arrival time
- Data age
- Priority
- Hour

## Çarpışma Tespiti

Sistem, 800ms pencere içinde birden fazla cihazdan paket gelirse çarpışma tespit eder. Sunucu ACK paketinde çarpışma bilgisini gönderir.

## İstatistikler

Sunucu, program sonlandığında şu istatistikleri gösterir:
- Toplam alınan paket sayısı
- Tespit edilen çarpışma sayısı
- Çarpışma oranı (%)
- Cihaz bazında başarı oranları

## Detaylı Dokümantasyon

Her modül için detaylı dokümantasyon:

- [Channel Monitor Dokümantasyonu](lopy4/channel_monitor/README.md)
- [Data Sender Dokümantasyonu](lopy4/data_sender/README.md)
- [Main Program Dokümantasyonu](lopy4/main/README.md)
- [ML Scheduler Dokümantasyonu](lopy4/ml_scheduler/README.md)
- [WiFi Manager Dokümantasyonu](lopy4/wifi_manager/README.md)
- [Data Collector Dokümantasyonu](server/README.md)

## Özellikler

- ML tabanlı adaptif zamanlama
- Gerçek zamanlı kanal durumu izleme
- Çarpışma tespiti ve önleme
- WiFi scanning ile komşu tespiti
- ACK mekanizması ile geri bildirim
- CSV veri kaydı ve analiz
- MicroPython uyumlu (LoPy4)
- JSON model formatı (hafif ve hızlı)

## Gereksinimler

### LoPy4 Cihaz
- Pycom LoPy4
- MicroPython firmware
- WiFi bağlantısı

### Sunucu
- Python 3.6+
- socket, json, csv, datetime modülleri (standart kütüphane)
- pandas (opsiyonel, veri analizi için)

## Katkıda Bulunanlar

Proje geliştiricileri: 
- [Burak Ege Yaşar](https://github.com/bitkicayi) 
- [Durhasan Yazğan](https://github.com/durhasan02) 
- [Raul Namazzade](https://github.com/Raul-dev00)
- [Yunus Ayaz](https://github.com/MrDolphin-gud)
- [Yusuf Çil](https://github.com/ysfcl)


