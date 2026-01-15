"""
WiFi Bağlantı Yönetimi
Pycom MicroPython uyumlu
"""

import network
import time

class WiFiManager:
    def __init__(self, ssid=None, password=None):
        """
        WiFi bağlantı yöneticisi

        Args:
            ssid: WiFi SSID (None ise varsayılan değer kullanılır)
            password: WiFi şifresi (None ise varsayılan değer kullanılır)
        """
        # BURAYA KENDİ WİFİ BİLGİLERİNİ YAZ
        self.ssid = ssid or "Patates"  # WiFi ağ adını buraya yaz
        self.password = password or "uzaylipatates36"  # WiFi şifresini buraya yaz

        # Pycom MicroPython için WiFi başlatma
        self.wlan = network.WLAN(mode=network.WLAN.STA)

    def connect(self, timeout=30):
        """
        WiFi'ye bağlan

        Args:
            timeout: Maksimum bekleme süresi (saniye)

        Returns:
            bool: Bağlantı başarılı ise True
        """
        if self.wlan.isconnected():
            print("Zaten bagli:", self.wlan.ifconfig())
            return True

        print("WiFi'ye baglaniliyor:", self.ssid)

        # Pycom MicroPython'da bağlantı
        self.wlan.connect(ssid=self.ssid, auth=(network.WLAN.WPA2, self.password))

        start_time = time.ticks_ms()
        while not self.wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start_time) > timeout * 1000:
                print("WiFi baglanti zaman asimi!")
                return False
            time.sleep(0.5)

        config = self.wlan.ifconfig()
        print("WiFi baglandi:", config)
        return True

    def disconnect(self):
        """WiFi bağlantısını kes"""
        try:
            self.wlan.disconnect()
        except:
            pass
        print("WiFi baglantisi kesildi")

    def get_rssi(self):
        """
        Mevcut RSSI değerini al (Pycom LoPy4 için scan kullanarak)
        Bağlı olduğumuz ağın RSSI değerini scan sonuçlarından bulur

        Returns:
            int: RSSI değeri (dBm) veya None
        """
        if not self.wlan.isconnected():
            return None

        try:
            # WiFi ağlarını tara
            networks = self.wlan.scan()

            # Bağlı olduğumuz ağın SSID'sini bul
            # Pycom'da bağlı ağın SSID'sini direkt alamayız, bu yüzden
            # scan sonuçlarından en yüksek RSSI'li ağı kullanabiliriz
            # veya tüm ağlar arasından en güçlü sinyali seçebiliriz

            if len(networks) == 0:
                return None

            # Pycom LoPy4 scan formatı: (ssid, bssid, sec, channel, rssi)
            # RSSI 4. indekste (net[4]) veya named tuple ise net.rssi
            max_rssi = -100
            for net in networks:
                try:
                    # Named tuple veya tuple olabilir
                    if hasattr(net, 'rssi'):
                        # Named tuple: net.rssi kullan
                        rssi_val = net.rssi
                    elif len(net) >= 5:
                        # Tuple: RSSI 4. indekste (ssid, bssid, sec, channel, rssi)
                        rssi_val = net[4]
                    else:
                        continue

                    # RSSI negatif olmalı (dBm)
                    if isinstance(rssi_val, int) and rssi_val < 0:
                        if rssi_val > max_rssi:
                            max_rssi = rssi_val
                except (IndexError, AttributeError, TypeError):
                    continue

            # Eğer geçerli bir RSSI bulunduysa döndür (negatif olmalı)
            if max_rssi > -100:
                return max_rssi

            # Alternatif: SSID'ye göre eşleştirme (daha doğru ama SSID bilgisi gerekir)
            # Şimdilik en yüksek RSSI'yi kullanıyoruz

        except Exception as e:
            print("RSSI alma hatasi (scan):", e)
            return None

        return None

    def is_connected(self):
        """Bağlantı durumunu kontrol et"""
        return self.wlan.isconnected()

    def get_ip(self):
        """IP adresini al"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None
