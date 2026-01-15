"""
Veri Gönderme Modülü
"""

import socket
import time
import json
import ubinascii
from wifi_manager import WiFiManager

class DataSender:
    def __init__(self, device_id, channel_monitor, server_ip="10.236.55.246", server_port=5000):
        """
        Veri gönderici

        Args:
            device_id: Cihaz ID
            channel_monitor: ChannelMonitor instance
            server_ip: Sunucu IP adresi
            server_port: Sunucu port numarası
        """
        self.device_id = device_id
        self.channel_monitor = channel_monitor
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = None

    def _connect(self):
        """Sunucuya bağlan"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Her cihaz için farklı kaynak portu kullan (cihaz ID'sine göre)
            # Böylece port çakışması olmaz
            source_port = 5000 + self.device_id  # Örn: Cihaz 1 -> port 5001, Cihaz 2 -> port 5002
            try:
                self.socket.bind(('', source_port))
                print("Kaynak port:", source_port)
            except:
                # Port kullanılıyorsa bind etme, sistem otomatik port seçer
                pass
            self.socket.settimeout(0.5)  # 0.5 saniye timeout (ACK için kısa timeout)
            return True
        except Exception as e:
            print("Socket olusturma hatasi:", e)
            return False

    def _wait_for_ack(self, timeout_ms=500):
        """
        Sunucudan ACK paketi bekle

        Args:
            timeout_ms: Maksimum bekleme süresi (ms)

        Returns:
            tuple: (success, collision_detected) veya (None, None) timeout ise
        """
        if self.socket is None:
            return (None, None)

        start_time = time.ticks_ms()
        max_iterations = timeout_ms // 10 + 1  # Maksimum iterasyon sayısı (güvenlik için)
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            current_time = time.ticks_ms()
            elapsed = time.ticks_diff(current_time, start_time)

            # Overflow kontrolü: negatif ise timeout'a ulaşılmış sayılır
            if elapsed < 0 or elapsed >= timeout_ms:
                break

            try:
                # Non-blocking recvfrom (socket timeout ile)
                data, addr = self.socket.recvfrom(1024)
                try:
                    ack = json.loads(data.decode('utf-8'))
                    if ack.get('type') == 'ack' and ack.get('device_id') == self.device_id:
                        success = ack.get('success', 1) == 1
                        collision_detected = ack.get('collision_detected', 0) == 1
                        return (success, collision_detected)
                except:
                    pass
            except Exception as e:
                # Timeout veya başka hata - kısa bir bekle ve devam et
                time.sleep_ms(10)  # 10ms bekle
                continue

        return (None, None)  # Timeout

    def send_data(self, data_age, priority, delay_used=0, data=None):
        """
        Veri gönder (Garantili Versiyon)
        """
        if self.socket is None:
            if not self._connect():
                return False

        # --- GERÇEK DEĞERLERİ ALMA ---
        # Önce gerçek değerleri almaya çalış, varsayılan değerleri sadece son çare olarak kullan
        rssi_value = None
        channel_occupancy = None
        collision_rate = None
        neighbor_count = None

        # Channel monitor'dan gerçek değerleri al
        try:
            if self.channel_monitor:
                rssi_value = self.channel_monitor.get_current_rssi()
                channel_occupancy = self.channel_monitor.get_channel_occupancy_rate()
                collision_rate = self.channel_monitor.get_collision_rate()
                neighbor_count = self.channel_monitor.get_neighbor_count()
        except Exception as e:
            print("Kanal bilgisi alma hatasi:", e)

        # Eğer RSSI yoksa WiFi'den direkt almayı dene (scan kullanarak)
        if rssi_value is None:
            try:
                import network
                wlan = network.WLAN()
                if wlan.isconnected():
                    # Pycom LoPy4'te rssi() metodu yok, scan kullanmalıyız
                    networks = wlan.scan()
                    if len(networks) > 0:
                        # En yüksek RSSI değerini bul (genellikle bağlı olduğumuz ağ)
                        # Pycom LoPy4 formatı: (ssid, bssid, sec, channel, rssi)
                        # RSSI 4. indekste (net[4]) veya named tuple ise net.rssi
                        max_rssi = -100
                        for net in networks:
                            try:
                                # Named tuple veya tuple olabilir
                                if hasattr(net, 'rssi'):
                                    # Named tuple: net.rssi kullan
                                    rssi_val = net.rssi
                                elif len(net) >= 5:
                                    # Tuple: RSSI 4. indekste
                                    rssi_val = net[4]
                                else:
                                    continue

                                # RSSI negatif olmalı (dBm)
                                if isinstance(rssi_val, int) and rssi_val < 0:
                                    if rssi_val > max_rssi:
                                        max_rssi = rssi_val
                            except (IndexError, AttributeError, TypeError):
                                continue

                        # RSSI negatif olmalı
                        if max_rssi > -100:
                            rssi_value = max_rssi
                            # RSSI'yi channel_monitor'a da kaydet
                            if self.channel_monitor and rssi_value is not None:
                                self.channel_monitor.record_rssi(rssi_value)
            except Exception as e:
                print("WiFi RSSI alma hatasi:", e)

        # Son çare olarak varsayılan değerleri kullan (sadece gerçek değerler yoksa)
        if rssi_value is None:
            rssi_value = -90
            print("UYARI: RSSI degeri bulunamadi, varsayilan deger kullaniliyor:", rssi_value)
        else:
            print("GERCEK RSSI:", rssi_value)

        if channel_occupancy is None:
            channel_occupancy = 0.0
            print("UYARI: Channel occupancy bulunamadi, varsayilan deger kullaniliyor:", channel_occupancy)
        else:
            print("GERCEK Channel Occupancy:", channel_occupancy)

        if collision_rate is None:
            collision_rate = 0.0
            print("UYARI: Collision rate bulunamadi, varsayilan deger kullaniliyor:", collision_rate)
        else:
            print("GERCEK Collision Rate:", collision_rate)

        if neighbor_count is None:
            neighbor_count = 0
            print("UYARI: Neighbor count bulunamadi, varsayilan deger kullaniliyor:", neighbor_count)
        else:
            print("GERCEK Neighbor Count:", neighbor_count)
        # --- GERÇEK DEĞERLERİ ALMA BİTİŞİ ---

        # Veri paketi oluştur
        packet = {
            'device_id': self.device_id,
            'timestamp': time.ticks_ms(),
            'data_age': data_age,
            'priority': priority,
            'delay_used': delay_used,
            'rssi': rssi_value,           # Artık kesinlikle sayı
            'channel_occupancy': channel_occupancy, # Artık kesinlikle sayı
            'collision_rate': collision_rate,       # Artık kesinlikle sayı
            'neighbor_count': neighbor_count,       # Artık kesinlikle sayı
            'data': data or self._generate_sensor_data()
        }

        # JSON'a çevir
        try:
            packet_json = json.dumps(packet)
            packet_bytes = packet_json.encode('utf-8')
        except Exception as e:
            print("Paket olusturma hatasi:", e)
            return False

        # Gönder
        try:
            # print("Paket gonderiliyor...", len(packet_bytes), "byte") # Çok kalabalık etmesin diye kapadım
            bytes_sent = self.socket.sendto(packet_bytes, (self.server_ip, self.server_port))

            # Gönderim başarılı mı kontrol et
            if bytes_sent == 0:
                # Hiç byte gönderilmedi, başarısız
                if self.channel_monitor:
                    self.channel_monitor.record_transmission(False, delay_used)
                return False

            # Kanal aktivitesini kaydet
            if self.channel_monitor:
                self.channel_monitor.record_channel_activity()

            # Sunucudan ACK paketi bekle (gerçek collision bilgisi için)
            success, collision_detected = self._wait_for_ack(timeout_ms=500)

            if success is not None:
                # ACK geldi, gerçek sonucu kullan
                # collision_detected True ise başarısız sayılır
                actual_success = success and not collision_detected
                if self.channel_monitor:
                    self.channel_monitor.record_transmission(actual_success, delay_used)
                return actual_success
            else:
                # ACK gelmedi (timeout), gönderim başarılı olarak varsay
                # NOT: UDP gönderimi her zaman başarılı görünür
                if self.channel_monitor:
                    self.channel_monitor.record_transmission(True, delay_used)
            return True

        except Exception as e:
            print("Gonderim hatasi:", e)
            # Gönderim hatası - başarısız olarak kaydet
            if self.channel_monitor:
                self.channel_monitor.record_transmission(False, delay_used)
            return False

    def _generate_sensor_data(self):
        """Sensör verisi simüle et"""
        import machine
        import ubinascii

        # Basit sensör verisi (sıcaklık, nem, vb.)
        return {
            'temperature': 25.5,
            'humidity': 60.0,
            'sensor_id': ubinascii.hexlify(machine.unique_id()).decode()
        }

    def close(self):
        """Bağlantıyı kapat"""
        if self.socket:
            self.socket.close()
            self.socket = None
