import os
import re
import rasterio
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, accuracy_score, cohen_kappa_score
from .constants import CLOUD_VALUES

def build_result_index(root_dir):
    """建立【去云结果】影像的日期索引字典"""
    file_map = {}
    for root, dirs, files in os.walk(root_dir):
        if 'spatial_products' in root or 'statistics' in root: continue
        for file in files:
            if file.lower().endswith('.tif'):
                match = re.search(r'(20\d{6})', file)
                if match: file_map[match.group(1)] = os.path.join(root, file)
    return file_map

def build_raw_index(root_dir):
    """建立【原始MODIS/MYDIS】影像的日期与传感器索引字典"""
    file_map = {} 
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.tif'):
                match = re.search(r'(20\d{6})', file)
                if match:
                    date_key = match.group(1)
                    if date_key not in file_map: file_map[date_key] = {}
                    if 'MOD10A1' in file: file_map[date_key]['MOD'] = os.path.join(root, file)
                    elif 'MYD10A1' in file: file_map[date_key]['MYD'] = os.path.join(root, file)
    return file_map

def check_cloud_status(row, raw_index):
    """多波段扫描，检查真实坐标点在原始影像中是否被云遮挡"""
    try:
        date_key = row['date'].strftime('%Y%m%d') if not isinstance(row['date'], str) else row['date'].replace('/', '').replace('-', '')[:8]
    except: return False

    if date_key not in raw_index: return False 
    paths = raw_index[date_key]

    for sensor in ['MOD', 'MYD']:
        if sensor in paths:
            try:
                with rasterio.open(paths[sensor]) as src:
                    row_idx, col_idx = src.index(row['proj_x'], row['proj_y'])
                    window = rasterio.windows.Window(col_idx, row_idx, 1, 1)
                    pixel_values = src.read(window=window).flatten()
                    for val in pixel_values:
                        if val in CLOUD_VALUES: return True
            except: pass
    return False

def extract_prediction(row, result_index):
    """从去云后的结果影像中提取水(0)或冰(1)的预测值"""
    try:
        date_key = row['date'].strftime('%Y%m%d') if not isinstance(row['date'], str) else row['date'].replace('/', '').replace('-', '')[:8]
    except: return -999

    if date_key not in result_index: return -999

    try:
        with rasterio.open(result_index[date_key]) as src:
            row_idx, col_idx = src.index(row['proj_x'], row['proj_y'])
            window = rasterio.windows.Window(col_idx, row_idx, 1, 1)
            val = src.read(1, window=window)[0][0]
            if val == 0: return 0
            elif val == 2: return 1
            else: return -999
    except: return -999

def plot_cm(y_true, y_pred, title, ax=None):
    """绘制单幅混淆矩阵及精度指标"""
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    oa = accuracy_score(y_true, y_pred)
    kappa = cohen_kappa_score(y_true, y_pred)
    
    if ax is None:
        plt.figure(figsize=(5, 4))
        ax = plt.gca()
        
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=['Water', 'Ice'], yticklabels=['Water', 'Ice'])
    ax.set_title(f'{title}\nOA={oa:.1%}, Kappa={kappa:.3f}')
    ax.set_xlabel('MODIS Prediction')
    ax.set_ylabel('Sentinel-1 Truth')
    return oa, kappa
