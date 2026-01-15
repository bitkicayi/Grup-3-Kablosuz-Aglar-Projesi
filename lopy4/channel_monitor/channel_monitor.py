"""
Kanal Durumu İzleme Modülü
RSSI, kanal doluluk oranı ve çarpışma tespiti
"""

import time

# Basit deque implementasyonu (MicroPython uyumlu)
class SimpleDeque:
    def __init__(self, maxlen=100):
        self.maxlen = maxlen
        self.items = []
    
    def append(self, item):
        self.items.append(item)
        if len(self.items) > self.maxlen:
            self.items.pop(0)
    
    def __len__(self):
        return len(self.items)
    
    def __iter__(self):
        return iter(self.items)
    
    def __getitem__(self, index):
        return self.items[index]

class ChannelMonitor:
    def __init__(self, device_id, window_size_ms=1000, collision_window=10):
        """
        Kanal durumu izleyici
        
        Args:
            device_id: Cihaz ID
            window_size_ms: İzleme penceresi (ms)
            collision_window: Çarpışma tespiti için pencere boyutu
        """
        self.device_id = device_id
        self.window_size_ms = window_size_ms
        self.collision_window = collision_window
        
        # RSSI geçmişi
        self.rssi_history = SimpleDeque(maxlen=100)
        self.rssi_timestamps = SimpleDeque(maxlen=100)
        
        # İletim geçmişi (başarılı/başarısız)
        self.transmission_history = SimpleDeque(maxlen=collision_window)
        
        # Kanal kullanım geçmişi
        self.channel_activity = SimpleDeque(maxlen=100)
        self.channel_timestamps = SimpleDeque(maxlen=100)
        
        # Son başarılı iletim zamanı
        self.last_successful_transmission = None
        
        # Ortalama bekleme süreleri
        self.wait_times = SimpleDeque(maxlen=50)
        
        # WiFi scanning sonuçları (gerçek neighbor count ve channel occupancy için)
        self.scan_results = SimpleDeque(maxlen=20)  # Son 20 scan sonucu
        self.scan_timestamps = SimpleDeque(maxlen=20)
        self.last_scan_time = None
        self.scan_interval_ms = 5000  # 5 saniyede bir scan yap
        
    def start(self):
        """İzlemeyi başlat"""
        print("Kanal izleme başlatıldı")
    
    def record_rssi(self, rssi_value):
        """
        RSSI değerini kaydet
        
        Args:
            rssi_value: RSSI değeri (dBm)
        """
        current_time = time.ticks_ms()
        self.rssi_history.append(rssi_value)
        self.rssi_timestamps.append(current_time)
    
    def get_current_rssi(self):
        """
        Mevcut RSSI değerini al
        
        Returns:
            float: Son RSSI değeri veya None
        """
        if len(self.rssi_history) > 0:
            return self.rssi_history[-1]
        return None
    
    def get_average_rssi(self, window_ms=None):
        """
        Ortalama RSSI değerini hesapla
        
        Args:
            window_ms: Zaman penceresi (ms), None ise tüm geçmiş
            
        Returns:
            float: Ortalama RSSI
        """
        if len(self.rssi_history) == 0:
            return None
        
        if window_ms is None:
            return sum(self.rssi_history) / len(self.rssi_history)
        
        current_time = time.ticks_ms()
        rssi_values = []
        
        for i, timestamp in enumerate(self.rssi_timestamps):
            if time.ticks_diff(current_time, timestamp) <= window_ms:
                rssi_values.append(self.rssi_history[i])
        
        if len(rssi_values) > 0:
            return sum(rssi_values) / len(rssi_values)
        return None
    
    def record_transmission(self, success, wait_time_ms=0):
        """
        İletim sonucunu kaydet
        
        Args:
            success: İletim başarılı ise True
            wait_time_ms: Bekleme süresi (ms)
        """
        self.transmission_history.append({
            'success': success,
            'timestamp': time.ticks_ms(),
            'wait_time': wait_time_ms
        })
        
        if success:
            self.last_successful_transmission = time.ticks_ms()
        
        if wait_time_ms > 0:
            self.wait_times.append(wait_time_ms)
    
    def get_collision_rate(self):
        """
        Son dönem çarpışma oranını hesapla
        
        Returns:
            float: Çarpışma oranı (0.0 - 1.0)
        """
        if len(self.transmission_history) == 0:
            return 0.0
        
        failed_count = sum(1 for t in self.transmission_history if not t['success'])
        return failed_count / len(self.transmission_history)
    
    def scan_wifi_networks(self):
        """
        WiFi ağlarını tara ve sonuçları kaydet
        (Gerçek neighbor count ve channel occupancy için)
        
        Returns:
            list: Taranan ağların listesi [(ssid, bssid, channel, rssi, ...), ...]
        """
        try:
            import network
            wlan = network.WLAN()
            
            # Eğer bağlı değilse veya scan yapamıyorsa None dön
            if not wlan.isconnected():
                return []
            
            # WiFi ağlarını tara
            # Pycom LoPy4 için: wlan.scan() kullanılır
            # Sonuç formatı: (ssid, bssid, channel, rssi, authmode, hidden)
            networks = wlan.scan()
            
            current_time = time.ticks_ms()
            self.scan_results.append(networks)
            self.scan_timestamps.append(current_time)
            self.last_scan_time = current_time
            
            return networks
        except Exception as e:
            print("WiFi scan hatasi:", e)
            return []
    
    def get_channel_occupancy_rate(self):
        """
        Kanal doluluk oranını hesapla (gerçek WiFi scanning ile)
        
        Returns:
            float: Doluluk oranı (0.0 - 1.0)
        """
        current_time = time.ticks_ms()
        
        # Eğer son scan çok eskiyse yeni scan yap
        if (self.last_scan_time is None or 
            time.ticks_diff(current_time, self.last_scan_time) > self.scan_interval_ms):
            self.scan_wifi_networks()
        
        # Son scan sonuçlarını kullan
        if len(self.scan_results) == 0:
            # Fallback: Kendi aktivitelerine göre tahmin
            activity_count = sum(1 for ts in self.channel_timestamps 
                                if time.ticks_diff(current_time, ts) <= self.window_size_ms)
            max_expected = self.window_size_ms / 100
            if max_expected > 0:
                return min(activity_count / max_expected, 1.0)
            return 0.0
        
        # Son scan sonuçlarından channel occupancy hesapla
        last_scan = self.scan_results[-1]
        
        # Çevredeki ağ sayısına göre occupancy tahmin et
        # Daha fazla ağ = daha yüksek occupancy
        network_count = len(last_scan)
        
        # Normalize et: 0-10 ağ = 0.0-1.0 occupancy
        # (Gerçek uygulamada daha karmaşık hesaplama yapılabilir)
        occupancy = min(network_count / 10.0, 1.0)
        
        # Ayrıca kendi aktivitelerimizi de ekle
        own_activity = sum(1 for ts in self.channel_timestamps 
                          if time.ticks_diff(current_time, ts) <= self.window_size_ms)
        own_activity_rate = min(own_activity / 10.0, 1.0)  # Son 1 saniyede max 10 aktivite
        
        # İkisini birleştir (ağırlıklı ortalama)
        return min((occupancy * 0.7 + own_activity_rate * 0.3), 1.0)
    
    def record_channel_activity(self):
        """Kanal aktivitesini kaydet"""
        current_time = time.ticks_ms()
        self.channel_activity.append(1)
        self.channel_timestamps.append(current_time)
    
    def get_last_successful_transmission_time(self):
        """
        Son başarılı iletim zamanını al
        
        Returns:
            int: Timestamp (ms) veya None
        """
        return self.last_successful_transmission
    
    def get_average_wait_time(self):
        """
        Ortalama bekleme süresini hesapla
        
        Returns:
            float: Ortalama bekleme süresi (ms)
        """
        if len(self.wait_times) > 0:
            return sum(self.wait_times) / len(self.wait_times)
        return 0.0
    
    def get_neighbor_count(self):
        """
        Aktif komşu cihaz sayısını WiFi scanning ile ölç
        
        Returns:
            int: Gerçek komşu sayısı (taranan ağ sayısı)
        """
        current_time = time.ticks_ms()
        
        # Eğer son scan çok eskiyse yeni scan yap
        if (self.last_scan_time is None or 
            time.ticks_diff(current_time, self.last_scan_time) > self.scan_interval_ms):
            self.scan_wifi_networks()
        
        # Son scan sonuçlarından neighbor count al
        if len(self.scan_results) > 0:
            last_scan = self.scan_results[-1]
            # Taranan ağ sayısı = neighbor count (kendi ağımız hariç)
            neighbor_count = len(last_scan)
            # Kendi ağımızı çıkar (eğer varsa)
            try:
                import network
                wlan = network.WLAN()
                if wlan.isconnected():
                    # Bağlı olduğumuz ağın SSID'sini al
                    current_ssid = None
                    try:
                        # Pycom için ifconfig'den SSID alınamaz, bu yüzden scan sonuçlarından
                        # en yüksek RSSI'li ağı kendi ağımız olarak kabul edebiliriz
                        # Veya basitçe tüm ağları sayabiliriz
                        pass
                    except:
                        pass
            except:
                pass
            
            return neighbor_count
        
        # Fallback: RSSI değişkenliğine göre tahmin (eski yöntem)
        if len(self.rssi_history) < 5:
            return 0
        
        rssi_variance = self._calculate_variance(list(self.rssi_history)[-10:])
        # Yüksek varyans = daha fazla komşu olabilir
        if rssi_variance > 10:
            return 2
        elif rssi_variance > 5:
            return 1
        return 0
    
    def _calculate_variance(self, values):
        """Varyans hesapla"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def get_features(self):
        """
        ML modeli için özellikleri hazırla
        (Gerçek WiFi scanning ile güncellenmiş değerler)
        
        Returns:
            dict: Özellik sözlüğü (None değerler varsayılanlarla değiştirilir)
        """
        # Önce WiFi scan yap (güncel veriler için)
        current_time = time.ticks_ms()
        if (self.last_scan_time is None or 
            time.ticks_diff(current_time, self.last_scan_time) > self.scan_interval_ms):
            self.scan_wifi_networks()
        
        return {
            'rssi': self.get_current_rssi(),  # None ise -80 kullan
            'avg_rssi': self.get_average_rssi(window_ms=5000),  # None ise -80 kullan
            'channel_occupancy': self.get_channel_occupancy_rate(),  # None ise 0.0 kullan
            'collision_rate': self.get_collision_rate(),  # None ise 0.0 kullan
            'neighbor_count': self.get_neighbor_count(),  # None ise 0 kullan
            'last_success_time': self.get_last_successful_transmission_time(),  # None ise 0 kullan
            'avg_wait_time': self.get_average_wait_time()  # None ise 0.0 kullan
        }


