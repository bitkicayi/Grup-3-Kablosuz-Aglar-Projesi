"""
Veri Ön İşleme
Toplanan verileri ML modeli için hazırlar
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

class DataPreprocessor:
    def __init__(self):
        """Veri ön işleyici"""
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_columns = None
        
    def load_data(self, csv_file):
        """
        CSV dosyasından veri yükle
        
        Args:
            csv_file: CSV dosya yolu
            
        Returns:
            pd.DataFrame: Yüklenen veri
        """
        df = pd.read_csv(csv_file)
        print(f"Veri yüklendi: {df.shape[0]} satır, {df.shape[1]} sütun")
        return df
    
    def prepare_features(self, df):
        """
        Özellikleri hazırla (ml_scheduler.py'deki sıraya göre)
        Sıra: ['rssi', 'channel_occupancy', 'collision_rate', 'neighbor_count', 
               'trend_rssi', 'inter_arrival_time', 'data_age', 'priority', 'hour']
        
        Args:
            df: Ham veri DataFrame
            
        Returns:
            pd.DataFrame: Özellikler DataFrame
        """
        # DataFrame'i kopyala (timestamp işlemleri için)
        df = df.copy()
        
        # Temel özellikler
        features = pd.DataFrame()
        
        # 1. RSSI
        if 'rssi' in df.columns:
            features['rssi'] = df['rssi'].fillna(-80)
        else:
            features['rssi'] = -80
        
        # 2. Channel Occupancy
        if 'channel_occupancy' in df.columns:
            features['channel_occupancy'] = df['channel_occupancy'].fillna(0)
        else:
            features['channel_occupancy'] = 0
        
        # 3. Collision Rate
        if 'collision_rate' in df.columns:
            features['collision_rate'] = df['collision_rate'].fillna(0)
        else:
            features['collision_rate'] = 0
        
        # 4. Neighbor Count
        if 'neighbor_count' in df.columns:
            features['neighbor_count'] = df['neighbor_count'].fillna(0)
        else:
            features['neighbor_count'] = 0
        
        # 5. Trend RSSI (son 5 RSSI değerinin ortalaması)
        if 'rssi' in df.columns:
            # Her cihaz için ayrı hesapla (timestamp'e göre sıralı)
            trend_rssi = []
            df_sorted = df.copy()
            if 'timestamp' in df.columns:
                df_sorted['timestamp'] = pd.to_datetime(df_sorted['timestamp'])
                df_sorted = df_sorted.sort_values(['device_id', 'timestamp'])
            
            for device_id in df['device_id'].unique():
                device_mask = df_sorted['device_id'] == device_id
                device_rssi = df_sorted.loc[device_mask, 'rssi'].fillna(-80)
                # Son 5 değerin ortalaması (rolling window)
                device_trend = device_rssi.rolling(window=5, min_periods=1).mean()
                trend_rssi.extend(device_trend.values)
            
            # Orijinal sıraya geri dön
            df_sorted['trend_rssi'] = trend_rssi
            features['trend_rssi'] = df_sorted.loc[df.index, 'trend_rssi'].fillna(-80)
        else:
            features['trend_rssi'] = -80
        
        # 6. Inter-arrival Time (son gönderimden bu yana geçen süre)
        if 'timestamp' in df.columns:
            df_sorted = df.copy()
            df_sorted['timestamp'] = pd.to_datetime(df_sorted['timestamp'])
            df_sorted = df_sorted.sort_values(['device_id', 'timestamp'])
            
            inter_arrival = []
            for device_id in df['device_id'].unique():
                device_mask = df_sorted['device_id'] == device_id
                device_times = df_sorted.loc[device_mask, 'timestamp']
                # İlk gönderim için 0, sonraki için fark (ms cinsinden)
                device_inter = [0]
                for i in range(1, len(device_times)):
                    diff_ms = int((device_times.iloc[i] - device_times.iloc[i-1]).total_seconds() * 1000)
                    device_inter.append(diff_ms)
                inter_arrival.extend(device_inter)
            
            # Orijinal sıraya geri dön
            df_sorted['inter_arrival_time'] = inter_arrival
            features['inter_arrival_time'] = df_sorted.loc[df.index, 'inter_arrival_time'].fillna(0)
        else:
            features['inter_arrival_time'] = 0
        
        # 7. Data Age
        features['data_age'] = df['data_age'].fillna(0)
        
        # 8. Priority
        features['priority'] = df['priority'].fillna(1)
        
        # 9. Hour
        if 'timestamp' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            features['hour'] = df['timestamp'].dt.hour
        else:
            features['hour'] = 12
        
        # Özellik sırasını ml_scheduler.py'deki sıraya göre ayarla
        feature_order = ['rssi', 'channel_occupancy', 'collision_rate', 'neighbor_count', 
                        'trend_rssi', 'inter_arrival_time', 'data_age', 'priority', 'hour']
        features = features[feature_order]
        
        self.feature_columns = features.columns.tolist()
        return features
    
    def prepare_labels(self, df, label_type='delay'):
        """
        Etiketleri hazırla
        
        Args:
            df: Ham veri DataFrame
            label_type: 'delay' (regression) veya 'action' (classification)
            
        Returns:
            np.array: Etiketler
        """
        if label_type == 'delay':
            # Regression: Optimal delay tahmin et
            if 'delay_used' in df.columns and 'success' in df.columns:
                # Başarılı iletimlerde kullanılan delay'i kullan
                # Başarısız iletimlerde delay'i artır
                labels = []
                for idx, row in df.iterrows():
                    if row.get('success', 1) == 1:
                        delay = row.get('delay_used', 0)
                    else:
                        # Başarısız ise delay'i artır
                        delay = min(row.get('delay_used', 0) * 2, 5000)
                    labels.append(delay)
                return np.array(labels)
            else:
                # Varsayılan delay (baseline)
                return np.full(len(df), 500)
        
        elif label_type == 'action':
            # Classification: Aksiyon seçimi
            action_space = [0, 100, 200, 500, 1000, 2000, 5000]
            if 'delay_used' in df.columns:
                labels = []
                for delay in df['delay_used']:
                    # En yakın aksiyonu bul
                    closest_action = min(action_space, key=lambda x: abs(x - delay))
                    labels.append(action_space.index(closest_action))
                return np.array(labels)
            else:
                return np.zeros(len(df))
        
        else:
            raise ValueError(f"Bilinmeyen label_type: {label_type}")
    
    def split_data(self, X, y, test_size=0.2, random_state=42):
        """
        Veriyi train/test olarak ayır
        
        Args:
            X: Özellikler
            y: Etiketler
            test_size: Test set oranı
            random_state: Random seed
            
        Returns:
            tuple: (X_train, X_test, y_train, y_test)
        """
        return train_test_split(X, y, test_size=test_size, random_state=random_state)
    
    def scale_features(self, X_train, X_test=None):
        """
        Özellikleri normalize et
        
        Args:
            X_train: Eğitim özellikleri
            X_test: Test özellikleri (opsiyonel)
            
        Returns:
            tuple: Normalize edilmiş özellikler
        """
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        if X_test is not None:
            X_test_scaled = self.scaler.transform(X_test)
            return X_train_scaled, X_test_scaled
        
        return X_train_scaled
    
    def get_feature_names(self):
        """Özellik isimlerini al"""
        return self.feature_columns



