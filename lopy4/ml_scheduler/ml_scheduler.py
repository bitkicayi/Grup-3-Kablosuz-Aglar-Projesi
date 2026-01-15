"""
ML Tabanlı Zamanlayıcı
Random Forest modeli ile optimal delay tahmini

SCHEDULER_MODE:
    0 -> Kural tabanlı zamanlama
    1 -> ML tabanlı zamanlama
"""

import time

# Zamanlayıcı modu (0: kural tabanlı, 1: ML tabanlı)
SCHEDULER_MODE = 1


class MLScheduler:
    def __init__(self, device_id, channel_monitor, model_path=None):
        """
        ML tabanlı zamanlayıcı

        Args:
            device_id: Cihaz ID
            channel_monitor: ChannelMonitor instance
            model_path: Model dosya yolu (opsiyonel, None ise otomatik yüklenir)
        """
        self.device_id = device_id
        self.channel_monitor = channel_monitor

        # Aksiyon uzayı (ms)
        self.action_space = [0, 100, 200, 500, 1000, 2000, 5000]

        # Geçmiş tahminler ve sonuçlar (online öğrenme için)
        self.prediction_history = []

        # ML modeli ve özellik isimleri
        self.model = None
        self.feature_names = None
        self.model_loaded = False

        # ML MODEL YÜKLEME - Sadece JSON formatı kullanılıyor
        # Özellik isimlerini yükle (pickle formatında)
        try:
            self.load_feature_names('models/model_features.pkl')
        except Exception as e:
            print("UYARI: Feature names yuklenemedi:", e)
            # Varsayılan özellik sırası
            self.feature_names = ['rssi', 'channel_occupancy', 'collision_rate',
                                 'neighbor_count', 'trend_rssi', 'inter_arrival_time',
                                 'data_age', 'priority', 'hour']

        # JSON modeli yükle (tek format)
        json_loaded = False
        try:
            json_model_path = model_path if model_path else 'models/model_micropython.json'
            self.load_json_model(json_model_path)
            if self.model_loaded:
                json_loaded = True
                print("JSON model yuklendi")
        except Exception as e:
            print("JSON model yuklenemedi:", e)

        if not json_loaded:
            print("UYARI: ML modeli yuklenemedi, varsayilan delay (500ms) kullanilacak")

    def get_optimal_delay(self, data_age, priority):
        """
        Optimal bekleme süresini hesapla

        Args:
            data_age: Veri yaşı (ms)
            priority: Öncelik seviyesi (1-3)

        Returns:
            int: Optimal bekleme süresi (ms)
        """
        # Özellikleri topla
        features = self.channel_monitor.get_features()

        # Mod değişkenine göre seçim yap
        if SCHEDULER_MODE == 0:
            # Kural tabanlı zamanlama
            return self._rule_based_scheduling(features, data_age, priority)

        # ML modu (1) - varsayılan
        if self.model is not None and self.model_loaded:
            return self._predict_with_model(features, data_age, priority)

        # ML modu seçili ama model yoksa varsayılan değer döndür
        print("UYARI: ML modeli yuklu degil, varsayilan delay kullaniliyor: 500ms")
        return 500.0

    def _rule_based_scheduling(self, features, data_age, priority):
        """
        Kural tabanlı zamanlama (baseline)

        Args:
            features: Kanal özellikleri
            data_age: Veri yaşı
            priority: Öncelik

        Returns:
            int: Bekleme süresi (ms)
        """
        collision_rate = features['collision_rate']
        channel_occupancy = features['channel_occupancy']
        rssi = features['rssi']

        # Yüksek öncelik: daha az bekle
        if priority == 3:
            if collision_rate > 0.5:
                return 200
            elif collision_rate > 0.3:
                return 100
            return 0

        # Düşük öncelik: daha fazla bekle
        if priority == 1:
            if collision_rate > 0.7:
                return 2000
            elif collision_rate > 0.5:
                return 1000
            elif collision_rate > 0.3:
                return 500
            return 200

        # Orta öncelik
        if collision_rate > 0.6:
            return 1000
        elif collision_rate > 0.4:
            return 500
        elif collision_rate > 0.2:
            return 200
        return 100

    def _predict_with_model(self, features, data_age, priority):
        """
        ML modeli ile tahmin yap

        Args:
            features: Kanal özellikleri
            data_age: Veri yaşı
            priority: Öncelik

        Returns:
            int: Optimal bekleme süresi (ms)
        """
        if not self.model_loaded or self.model is None:
            # Model yüklenmemiş, varsayılan değer döndür
            print("UYARI: Model yuklenmemis, varsayilan delay: 500ms")
            return 500.0

        try:
            # Özellik vektörünü hazırla
            feature_vector = self._prepare_feature_vector(features, data_age, priority)

            # Model tahmini yap
            prediction = self._model_predict(feature_vector)

            # Tahmini delay değerine dönüştür (0-5000ms arası)
            delay = max(0, min(int(prediction), 5000))

            return delay
        except Exception as e:
            print("Model tahmin hatasi:", e)
            # Hata durumunda varsayılan değer döndür (kural tabanlı kullanma)
            print("Varsayilan delay kullaniliyor: 500ms")
            return 500.0

    def _prepare_feature_vector(self, features, data_age, priority):
        """
        Model için özellik vektörünü hazırla

        Args:
            features: Kanal özellikleri dict
            data_age: Veri yaşı
            priority: Öncelik

        Returns:
            list: Özellik vektörü (model_features.pkl'deki sıraya göre)
        """
        # Model özellik sırası (model_features.pkl'den):
        # ['rssi', 'channel_occupancy', 'collision_rate', 'neighbor_count',
        #  'trend_rssi', 'inter_arrival_time', 'data_age', 'priority', 'hour']

        # RSSI trend hesapla (son RSSI değerlerinin ortalaması - mevcut RSSI)
        trend_rssi = 0.0
        if self.channel_monitor and hasattr(self.channel_monitor, 'rssi_history'):
            rssi_history = self.channel_monitor.rssi_history
            if len(rssi_history) > 1:
                current_rssi = features.get('rssi', -80)
                avg_rssi = sum(rssi_history[-5:]) / min(len(rssi_history), 5) if rssi_history else current_rssi
                trend_rssi = avg_rssi - current_rssi

        # Inter-arrival time (son gönderimden bu yana geçen süre)
        inter_arrival_time = data_age  # Şimdilik data_age ile aynı

        # Saat bilgisi
        try:
            ticks = time.ticks_ms()
            hour = (ticks // 3600000) % 24
        except:
            hour = 12  # Varsayılan

        # Model özellik sırasına göre vektör oluştur
        feature_vector = [
            float(features.get('rssi', -80)),              # rssi
            float(features.get('channel_occupancy', 0.0)), # channel_occupancy
            float(features.get('collision_rate', 0.0)),   # collision_rate
            float(features.get('neighbor_count', 0)),      # neighbor_count
            float(trend_rssi),                            # trend_rssi
            float(inter_arrival_time),                     # inter_arrival_time
            float(data_age),                              # data_age
            float(priority),                              # priority
            float(hour),                                  # hour
        ]

        return feature_vector

    def _model_predict(self, feature_vector):
        """
        Model ile tahmin yap (Random Forest için)

        Args:
            feature_vector: Özellik vektörü

        Returns:
            float: Tahmin edilen delay değeri
        """
        if self.model is None:
            return 500.0  # Varsayılan delay

        # JSON formatındaki model (MicroPython uyumlu)
        if isinstance(self.model, dict) and self.model.get('type') == 'RandomForestRegressor':
            return self._predict_json_model(feature_vector)

        # sklearn modeli (pickle ile yüklenmiş)
        if hasattr(self.model, 'predict'):
            try:
                result = self.model.predict([feature_vector])
                if isinstance(result, (list, tuple)):
                    return float(result[0])
                return float(result)
            except:
                pass

        # Fallback: Basit tahmin
        return self._simple_tree_predict(feature_vector)

    def _predict_json_model(self, feature_vector):
        """
        JSON formatındaki model ile tahmin yap

        Args:
            feature_vector: Özellik vektörü (liste)

        Returns:
            float: Tahmin edilen delay
        """
        if not isinstance(self.model, dict) or 'trees' not in self.model:
            print("UYARI: Model dict formatinda degil veya trees yok")
            return 500.0

        # Özellik isimlerine göre dict oluştur
        feature_dict = {}
        if self.feature_names and len(self.feature_names) == len(feature_vector):
            for i, name in enumerate(self.feature_names):
                feature_dict[name] = feature_vector[i]
        else:
            # Varsayılan isimler
            default_names = ['rssi', 'channel_occupancy', 'collision_rate',
                           'neighbor_count', 'trend_rssi', 'inter_arrival_time',
                           'data_age', 'priority', 'hour']
            for i, name in enumerate(default_names[:len(feature_vector)]):
                feature_dict[name] = feature_vector[i]

        # Debug: İlk birkaç özelliği yazdır
        print("DEBUG Model tahmini - Ozellikler:",
              "rssi=", feature_dict.get('rssi', 0),
              "collision=", feature_dict.get('collision_rate', 0),
              "priority=", feature_dict.get('priority', 0))

        # Her ağaç için tahmin yap ve ortalamasını al
        predictions = []
        for tree in self.model['trees']:
            pred = self._predict_tree(tree, feature_dict)
            predictions.append(pred)

        # RandomForest: Tüm ağaçların ortalaması
        avg_prediction = sum(predictions) / len(predictions) if predictions else 500.0
        print("DEBUG Model tahmini - Ortalama:", avg_prediction, "ms (", len(predictions), "agac)")

        # Sadece ML tahminini kullan (kural tabanlı sisteme geçme)
        # Model tahmini ne olursa olsun, ML tahminini döndür
        return avg_prediction

    def _predict_tree(self, tree_node, features):
        """
        Tek bir ağaç ile tahmin yap (recursive)

        Args:
            tree_node: Ağaç node'u (dict)
            features: Özellik dict'i

        Returns:
            float: Tahmin değeri
        """
        if tree_node['type'] == 'leaf':
            return tree_node['value']

        # Node: feature ve threshold kontrolü
        feature_name = tree_node['feature']
        threshold = tree_node['threshold']
        feature_value = features.get(feature_name, 0.0)

        if feature_value <= threshold:
            return self._predict_tree(tree_node['left'], features)
        else:
            return self._predict_tree(tree_node['right'], features)

    def _simple_tree_predict(self, feature_vector):
        """
        Basit fallback tahmin (ML modeli çalışmazsa)

        Args:
            feature_vector: Özellik vektörü

        Returns:
            float: Varsayılan delay (500ms)
        """
        # ML modeli çalışmazsa varsayılan değer döndür
        print("UYARI: ML modeli calismadi, varsayilan delay: 500ms")
        return 500.0

    def load_feature_names(self, feature_path):
        """
        Özellik isimlerini yükle

        Args:
            feature_path: Özellik dosya yolu
        """
        try:
            # MicroPython'da pickle yerine upickle kullan
            try:
                import upickle as pickle
            except ImportError:
                try:
                    import pickle
                except ImportError:
                    # Pickle yok, varsayılan özellik sırasını kullan
                    print("UYARI: pickle/upickle modulu yok, varsayilan ozellik sirasi kullaniliyor")
                    self.feature_names = ['rssi', 'channel_occupancy', 'collision_rate',
                                         'neighbor_count', 'trend_rssi', 'inter_arrival_time',
                                         'data_age', 'priority', 'hour']
                    return

            with open(feature_path, 'rb') as f:
                self.feature_names = pickle.load(f)
            print("Ozellik isimleri yuklendi:", self.feature_names)
        except Exception as e:
            print("UYARI: Ozellik isimleri yuklenemedi:", e)
            # Varsayılan özellik sırası
            self.feature_names = ['rssi', 'channel_occupancy', 'collision_rate',
                                 'neighbor_count', 'trend_rssi', 'inter_arrival_time',
                                 'data_age', 'priority', 'hour']

    def load_json_model(self, json_path):
        """
        JSON formatındaki modeli yükle (MicroPython uyumlu)
        Optimize edilmiş yükleme (ujson kullanır, daha hızlı)

        Args:
            json_path: JSON model dosya yolu
        """
        print("JSON model yukleniyor:", json_path)
        import time
        start_time = time.ticks_ms()

        try:
            # ujson daha hızlı (MicroPython'da genellikle mevcut)
            try:
                import ujson as json
                print("ujson kullaniliyor (hizli)")
            except ImportError:
                try:
                    import json
                    print("json kullaniliyor (yavas)")
                except ImportError:
                    print("HATA: json modulu bulunamadi")
                    self.model = None
                    self.model_loaded = False
                    return

        except Exception as e:
            print("HATA: json modulu yuklenemedi:", e)
            self.model = None
            self.model_loaded = False
            return

        try:
            # Dosyayı oku ve parse et
            print("Dosya okunuyor...")
            with open(json_path, 'r') as f:
                file_content = f.read()

            read_time = time.ticks_ms()
            print("Dosya okundu, parse ediliyor...")

            # JSON parse (ujson daha hızlı)
            self.model = json.loads(file_content)

            parse_time = time.ticks_ms()
            load_duration = time.ticks_diff(parse_time, start_time)

            if self.model.get('type') == 'RandomForestRegressor':
                self.model_loaded = True
                if 'feature_names' in self.model:
                    self.feature_names = self.model['feature_names']

                tree_count = len(self.model.get('trees', []))
                print("JSON model basariyla yuklendi!")
                print("  Agac sayisi:", tree_count)
                print("  Yukleme suresi:", load_duration, "ms")
                print("  Dosya boyutu: ~", len(file_content) // 1024, "KB")
            else:
                print("UYARI: Gecersiz model tipi")
                self.model = None
                self.model_loaded = False

        except OSError as e:
            print("HATA: JSON model dosyasi bulunamadi:", json_path)
            print("Hata detayi:", e)
            self.model = None
            self.model_loaded = False
        except MemoryError as e:
            print("HATA: Bellek yetersiz! Model cok buyuk.")
            print("Cozum: Model boyutunu kucult (daha az agac, daha az derinlik)")
            self.model = None
            self.model_loaded = False
        except Exception as e:
            print("HATA: JSON model yukleme basarisiz:", e)
            import sys
            sys.print_exception(e)
            self.model = None
            self.model_loaded = False

    def load_model(self, model_path):
        """
        ML modelini yükle - ARTIK KULLANILMIYOR
        Sadece JSON formatı kullanılıyor (load_json_model kullan)

        Args:
            model_path: Model dosya yolu (kullanılmıyor)
        """
        print("UYARI: load_model() artik kullanilmiyor, load_json_model() kullanin")
        print("JSON model yukleniyor...")
        # JSON model yolunu dene
        json_path = model_path.replace('.pkl', '.json') if model_path else 'models/model_micropython.json'
        self.load_json_model(json_path)

    def record_transmission_result(self, success, delay_used):
        """
        İletim sonucunu kaydet

        Args:
            success: İletim başarılı ise True
            delay_used: Kullanılan bekleme süresi (ms)
        """
        self.channel_monitor.record_transmission(success, delay_used)

        # Tahmin geçmişine ekle (online öğrenme için)
        self.prediction_history.append({
            'success': success,
            'delay': delay_used,
            'timestamp': time.ticks_ms()
        })

        # Geçmiş çok uzunsa temizle
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-500:]
