"""
ML Model Eğitimi
Random Forest, XGBoost ve Neural Network modelleri
"""

import numpy as np
import pandas as pd
import pickle
import os
import json
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, classification_report
import xgboost as xgb
from data_preprocessing import DataPreprocessor

class ModelTrainer:
    def __init__(self, model_type='random_forest'):
        """
        Model eğitici
        
        Args:
            model_type: 'random_forest', 'xgboost', veya 'neural_network'
        """
        self.model_type = model_type
        self.model = None
        self.preprocessor = DataPreprocessor()
        
    def train_regression(self, csv_file, output_dir='ml/models/'):
        """
        Regression modeli eğit (optimal delay tahmini)
        
        Args:
            csv_file: Veri CSV dosyası
            output_dir: Model kayıt dizini
        """
        print(f"Regression modeli eğitiliyor: {self.model_type}")
        
        # Veri yükle
        df = self.preprocessor.load_data(csv_file)
        
        # Özellikleri hazırla
        X = self.preprocessor.prepare_features(df)
        y = self.preprocessor.prepare_labels(df, label_type='delay')
        
        # Train/test split
        X_train, X_test, y_train, y_test = self.preprocessor.split_data(X, y)
        
        # Model seç ve eğit
        # NOT: MicroPython için model boyutunu küçük tut (max 500 KB)
        if self.model_type == 'random_forest':
            # 500 KB hedefi için optimize edilmiş ayarlar:
            # - 30 ağaç (daha iyi tahmin, ~150-200 KB)
            # - max_depth=6 (dengeli derinlik)
            # - min_samples_split/leaf (daha kompakt ağaçlar)
            self.model = RandomForestRegressor(
                n_estimators=40,      # 30 ağaç (500 KB altında kalır)
                max_depth=6,          # 6 derinlik (dengeli)
                min_samples_split=10, # Daha az node (daha küçük ağaçlar)
                min_samples_leaf=5,   # Daha az leaf (daha küçük ağaçlar)
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'xgboost':
            self.model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
        else:
            raise ValueError(f"Desteklenmeyen model tipi: {self.model_type}")
        
        print("Model eğitiliyor...")
        self.model.fit(X_train, y_train)
        
        # Değerlendirme
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        train_mae = mean_absolute_error(y_train, y_pred_train)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        
        print(f"\n=== Eğitim Sonuçları ===")
        print(f"Train RMSE: {train_rmse:.2f} ms")
        print(f"Test RMSE: {test_rmse:.2f} ms")
        print(f"Train MAE: {train_mae:.2f} ms")
        print(f"Test MAE: {test_mae:.2f} ms")
        
        # Model kaydet
        os.makedirs(output_dir, exist_ok=True)
        
        # LoPy4 için JSON model dosyası
        json_model_path = os.path.join(output_dir, 'model_micropython.json')
        feature_path = os.path.join(output_dir, 'model_features.pkl')
        
        # Feature names kaydet (ml_scheduler.py için - pickle olarak)
        with open(feature_path, 'wb') as f:
            pickle.dump(self.preprocessor.get_feature_names(), f)
        print(f"Feature names kaydedildi: {feature_path}")
        
        # Modeli direkt JSON formatına dönüştür
        print("\nModel JSON formatina donusturuluyor...")
        self._save_model_as_json(self.model, self.preprocessor.get_feature_names(), json_model_path)
        
        print(f"JSON model kaydedildi: {json_model_path}")
        print(f"Feature names: {self.preprocessor.get_feature_names()}")
        
        return self.model
    
    def _save_model_as_json(self, model, feature_names, output_path):
        """
        RandomForest modelini JSON formatına kaydet
        """
        def tree_to_dict(tree, feature_names):
            """DecisionTree'i dict formatına dönüştür"""
            tree_ = tree.tree_
            
            def recurse(node):
                if tree_.feature[node] >= 0:
                    # Internal node
                    feature_idx = tree_.feature[node]
                    threshold = tree_.threshold[node]
                    left = tree_.children_left[node]
                    right = tree_.children_right[node]
                    
                    return {
                        'type': 'node',
                        'feature': feature_names[feature_idx] if feature_names else feature_idx,
                        'threshold': float(threshold),
                        'left': recurse(left),
                        'right': recurse(right)
                    }
                else:
                    # Leaf node
                    value = tree_.value[node][0][0]
                    return {
                        'type': 'leaf',
                        'value': float(value)
                    }
            
            return recurse(0)
        
        # Her ağacı dönüştür
        trees = []
        for i, tree in enumerate(model.estimators_):
            if (i + 1) % 10 == 0:
                print(f"  Agac {i+1}/{len(model.estimators_)} donusturuluyor...")
            tree_dict = tree_to_dict(tree, feature_names)
            trees.append(tree_dict)
        
        # JSON model oluştur
        json_model = {
            'type': 'RandomForestRegressor',
            'n_estimators': len(model.estimators_),
            'feature_names': feature_names,
            'trees': trees,
            'note': 'MicroPython icin basitlestirilmis RandomForest modeli'
        }
        
        # JSON'a kaydet (indent yok - daha küçük dosya)
        with open(output_path, 'w') as f:
            json.dump(json_model, f, separators=(',', ':'))  # indent yok, minify
        
        # Dosya boyutunu kontrol et
        import os
        file_size = os.path.getsize(output_path)
        file_size_kb = file_size / 1024
        print(f"  Toplam {len(trees)} agac JSON formatina donusturuldu")
        print(f"  Dosya boyutu: {file_size_kb:.1f} KB")
        
        if file_size_kb > 500:
            print(f"  UYARI: Dosya boyutu {file_size_kb:.1f} KB, hedef 500 KB'den buyuk!")
            print(f"  Oneriler: n_estimators veya max_depth'i daha da azalt")
    
    def train_classification(self, csv_file, output_dir='ml/models/'):
        """
        Classification modeli eğit (aksiyon seçimi)
        
        Args:
            csv_file: Veri CSV dosyası
            output_dir: Model kayıt dizini
        """
        print(f"Classification modeli eğitiliyor: {self.model_type}")
        
        # Veri yükle
        df = self.preprocessor.load_data(csv_file)
        
        # Özellikleri hazırla
        X = self.preprocessor.prepare_features(df)
        y = self.preprocessor.prepare_labels(df, label_type='action')
        
        # Train/test split
        X_train, X_test, y_train, y_test = self.preprocessor.split_data(X, y)
        
        # Model seç ve eğit
        n_classes = len([0, 100, 200, 500, 1000, 2000, 5000])
        
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'xgboost':
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
        else:
            raise ValueError(f"Desteklenmeyen model tipi: {self.model_type}")
        
        print("Model eğitiliyor...")
        self.model.fit(X_train, y_train)
        
        # Değerlendirme
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        train_acc = accuracy_score(y_train, y_pred_train)
        test_acc = accuracy_score(y_test, y_pred_test)
        
        print(f"\n=== Eğitim Sonuçları ===")
        print(f"Train Accuracy: {train_acc:.4f}")
        print(f"Test Accuracy: {test_acc:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred_test))
        
        # Model kaydet
        os.makedirs(output_dir, exist_ok=True)
        model_path = os.path.join(output_dir, f'{self.model_type}_classifier.pkl')
        
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'preprocessor': self.preprocessor,
                'feature_names': self.preprocessor.get_feature_names()
            }, f)
        
        print(f"Model kaydedildi: {model_path}")
        
        return self.model

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Kullanım: python train_model.py <csv_file> [model_type] [task_type]")
        print("model_type: random_forest, xgboost")
        print("task_type: regression, classification")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    model_type = sys.argv[2] if len(sys.argv) > 2 else 'random_forest'
    task_type = sys.argv[3] if len(sys.argv) > 3 else 'regression'
    
    trainer = ModelTrainer(model_type=model_type)
    
    if task_type == 'regression':
        trainer.train_regression(csv_file)
    elif task_type == 'classification':
        trainer.train_classification(csv_file)
    else:
        print(f"Bilinmeyen task_type: {task_type}")



