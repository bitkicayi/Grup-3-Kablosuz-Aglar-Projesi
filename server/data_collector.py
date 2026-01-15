"""
Veri Toplama Sunucusu
LoPy4 cihazlarından gelen verileri toplar ve kaydeder
"""

import socket
import json
import time
import csv
from datetime import datetime
from collections import defaultdict

class DataCollector:
    def __init__(self, host='0.0.0.0', port=5000, data_file='data/collected_data.csv'):
        """
        Veri toplama sunucusu
        
        Args:
            host: Dinlenecek IP adresi
            port: Port numarası
            data_file: Veri kayıt dosyası
        """
        self.host = host
        self.port = port
        self.data_file = data_file
        self.socket = None
        
        # İstatistikler
        self.stats = defaultdict(int)
        self.device_stats = defaultdict(lambda: {'received': 0, 'failed': 0})
        
        # Çarpışma tespiti için son paket zamanları
        self.last_packet_times = {}  # device_id -> timestamp
        self.collision_window_ms = 800 
        
        # CSV başlıkları
        self.csv_headers = [
            'timestamp', 'device_id', 'data_age', 'priority',
            'rssi', 'channel_occupancy', 'collision_rate',
            'neighbor_count', 'success', 'delay_used', 'collision_detected'
        ]
        
    def start(self):
        """Sunucuyu başlat"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        self.socket.settimeout(1.0)  # 1 saniye timeout (non-blocking için)
        
        print(f"Veri toplama sunucusu başlatıldı: {self.host}:{self.port}")
        
        # CSV dosyasını başlat
        self._init_csv_file()
        
        try:
            while True:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    self._process_packet(data, addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Paket işleme hatası: {e}")
        except KeyboardInterrupt:
            print("\nSunucu durduruluyor...")
        finally:
            self._print_stats()
            if self.socket:
                self.socket.close()
    
    def _init_csv_file(self):
        """CSV dosyasını başlat"""
        import os
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        # Dosya yoksa başlıkları yaz
        try:
            with open(self.data_file, 'r') as f:
                pass  # Dosya varsa başlık yazma
        except FileNotFoundError:
            with open(self.data_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.csv_headers)
    
    def _process_packet(self, data, addr):
        """
        Gelen paketi işle (Düzeltilmiş)
        """
        try:
            packet = json.loads(data.decode('utf-8'))
            
            device_id = packet.get('device_id', 'unknown')
            # timestamp yoksa sunucu zamanını kullan
            packet_timestamp = packet.get('timestamp', int(time.time() * 1000))
            server_timestamp = int(time.time() * 1000)
            
            # --- DÜZELTME: .get() içine varsayılan değerleri (0 veya -90) ekledik ---
            data_age = packet.get('data_age', 0)
            priority = packet.get('priority', 1)
            delay_used = packet.get('delay_used', 0)
            
            rssi_value = packet.get('rssi', -90)            # Boşsa -90 yap
            channel_occupancy = packet.get('channel_occupancy', 0.0) # Boşsa 0.0 yap
            collision_rate = packet.get('collision_rate', 0.0)       # Boşsa 0.0 yap
            neighbor_count = packet.get('neighbor_count', 0)         # Boşsa 0 yap
            # -----------------------------------------------------------------------

            # Çarpışma tespiti: Son 100ms içinde başka bir cihazdan paket geldi mi?
            collision_detected = False
            for other_device_id, last_time in self.last_packet_times.items():
                if other_device_id != device_id:
                    time_diff = abs(server_timestamp - last_time)
                    if time_diff < self.collision_window_ms:
                        collision_detected = True
                        self.stats['collisions_detected'] += 1
                        print(f"CARPISMA! {device_id} <-> {other_device_id} ({time_diff}ms)")
                        break
            
            # Son paket zamanını güncelle
            self.last_packet_times[device_id] = server_timestamp
            
            # Eski kayıtları temizle
            current_time = server_timestamp
            self.last_packet_times = {
                dev_id: ts for dev_id, ts in self.last_packet_times.items()
                if current_time - ts < 1000
            }
            
            # İstatistikleri güncelle
            self.stats['total_received'] += 1
            if collision_detected:
                self.device_stats[device_id]['failed'] += 1
            else:
                self.device_stats[device_id]['received'] += 1
            
            # Veriyi CSV'ye kaydet
            row = [
                datetime.now().isoformat(),
                device_id,
                data_age,
                priority,
                rssi_value,         # Düzelttik
                channel_occupancy,  # Düzelttik
                collision_rate,     # Düzelttik
                neighbor_count,     # Düzelttik
                0 if collision_detected else 1,
                delay_used,
                1 if collision_detected else 0
            ]
            
            self._save_to_csv(row)
            
            # ACK paketi gönder (cihaza collision bilgisini bildirmek için)
            ack_packet = {
                'type': 'ack',
                'device_id': device_id,
                'timestamp': server_timestamp,
                'success': 0 if collision_detected else 1,
                'collision_detected': 1 if collision_detected else 0
            }
            try:
                ack_json = json.dumps(ack_packet)
                ack_bytes = ack_json.encode('utf-8')
                # Cihazın kaynak portuna gönder (5000 + device_id)
                ack_port = 5000 + device_id
                self.socket.sendto(ack_bytes, (addr[0], ack_port))
            except Exception as e:
                print(f"ACK gonderim hatasi: {e}")
            
            # Ekrana daha temiz bilgi basalım
            status = "CARPISMA" if collision_detected else "BASARILI"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {status} | ID:{device_id} | RSSI:{rssi_value} | Doluluk:%{channel_occupancy*100:.1f}")
            
        except json.JSONDecodeError as e:
            print(f"JSON hatasi: {e}")
            self.stats['decode_errors'] += 1
        except Exception as e:
            print(f"Paket isleme hatasi: {e}")
            self.stats['processing_errors'] += 1
    
    def _save_to_csv(self, row):
        """Veriyi CSV'ye kaydet"""
        try:
            with open(self.data_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"CSV kayıt hatası: {e}")
    
    def _print_stats(self):
        """İstatistikleri yazdır"""
        print("\n=== İstatistikler ===")
        print(f"Toplam alınan paket: {self.stats['total_received']}")
        print(f"Tespit edilen çarpışma: {self.stats.get('collisions_detected', 0)}")
        if self.stats['total_received'] > 0:
            collision_rate = (self.stats.get('collisions_detected', 0) / self.stats['total_received']) * 100
            print(f"Çarpışma oranı: {collision_rate:.2f}%")
        print(f"Decode hataları: {self.stats['decode_errors']}")
        print(f"İşleme hataları: {self.stats['processing_errors']}")
        print("\nCihaz bazında:")
        for device_id, stats in self.device_stats.items():
            success_rate = (stats['received'] / (stats['received'] + stats['failed'])) * 100 if (stats['received'] + stats['failed']) > 0 else 0
            print(f"  Cihaz {device_id}: {stats['received']} başarılı, {stats['failed']} başarısız "
                  f"({success_rate:.1f}% başarı)")

if __name__ == "__main__":
    collector = DataCollector()
    collector.start()

