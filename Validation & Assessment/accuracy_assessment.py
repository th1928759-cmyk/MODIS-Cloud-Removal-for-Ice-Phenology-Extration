import pandas as pd
import rasterio
import os
import re
from sklearn.metrics import confusion_matrix, accuracy_score, cohen_kappa_score
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
plt.rcParams['font.family'] = 'Times New Roman'

# ================= 1. 配置路径 (相对路径) =================
CURRENT_DIR = Path(__file__).parent.absolute()
DATA_DIR = CURRENT_DIR.parent / "data"

# 结果数据 (去云后的二值图)
RESULT_ROOT_DIR = DATA_DIR / "results"
# 原始数据 (MOD/MYD, 包含多波段)
RAW_ROOT_DIR = DATA_DIR / "raw"
# 带坐标的 CSV 真值点
CSV_PATH = DATA_DIR / "ground_truth" / "S1_GroundTruth_Projected.csv"
# 输出目录
OUTPUT_DIR = DATA_DIR / "results" / "validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLOUD_VALUES = [200, 201, 211, 250, 254]

# ================= 2. 建立索引 =================
def build_result_index(root_dir):
    print(f"1. 建立【去云结果】索引: {root_dir}")
    file_map = {}
    for root, dirs, files in os.walk(root_dir):
        if 'spatial_products' in root: continue
        for file in files:
            if file.lower().endswith('.tif'):
                match = re.search(r'(20\d{6})', file)
                if match: file_map[match.group(1)] = os.path.join(root, file)
    print(f"   ✅ 找到 {len(file_map)} 个结果文件")
    return file_map

def build_raw_index(root_dir):
    print(f"2. 建立【原始MODIS】索引: {root_dir}")
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
    print(f"   ✅ 找到 {len(file_map)} 组原始影像")
    return file_map

# ================= 3. 提取逻辑 =================
def check_cloud_status(row, raw_index):
    try:
        if isinstance(row['date'], str): date_key = row['date'].replace('/', '').replace('-', '')[:8]
        else: date_key = row['date'].strftime('%Y%m%d')
    except: return False

    if date_key not in raw_index: return False 
    paths = raw_index[date_key]

    for sensor in ['MOD', 'MYD']:
        if sensor in paths:
            try:
                with rasterio.open(paths[sensor]) as src:
                    try:
                        row_idx, col_idx = src.index(row['proj_x'], row['proj_y'])
                        window = rasterio.windows.Window(col_idx, row_idx, 1, 1)
                        pixel_values = src.read(window=window).flatten()
                        for val in pixel_values:
                            if val in CLOUD_VALUES: return True
                    except IndexError: pass
            except: pass
    return False

def extract_prediction(row, result_index):
    try:
        if isinstance(row['date'], str): date_key = row['date'].replace('/', '').replace('-', '')[:8]
        else: date_key = row['date'].strftime('%Y%m%d')
    except: return -999

    if date_key not in result_index: return -999

    try:
        with rasterio.open(result_index[date_key]) as src:
            try:
                row_idx, col_idx = src.index(row['proj_x'], row['proj_y'])
                window = rasterio.windows.Window(col_idx, row_idx, 1, 1)
                val = src.read(1, window=window)[0][0]
                if val == 0: return 0
                elif val == 2: return 1
                else: return -999
            except IndexError: return -999
    except: return -999

# ================= 4. 绘图 =================
def plot_cm(y_true, y_pred, title, ax=None):
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

if __name__ == "__main__":
    print("========== 🚀 精度验证与混淆矩阵 ==========")
    if not CSV_PATH.exists():
        print(f"❌ 找不到真值 CSV: {CSV_PATH}")
    else:
        res_idx = build_result_index(RESULT_ROOT_DIR)
        raw_idx = build_raw_index(RAW_ROOT_DIR)

        print("\n3. 读取并处理 CSV...")
        df = pd.read_csv(CSV_PATH)
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['manual_label'] != -1].copy()
        
        print("   正在扫描所有波段查找云覆盖...")
        df['is_cloud_originally'] = df.apply(lambda row: check_cloud_status(row, raw_idx), axis=1)
        
        print("   提取模型分类结果...")
        df['MODIS_Pred'] = df.apply(lambda row: extract_prediction(row, res_idx), axis=1)
        
        valid_df = df[(df['MODIS_Pred'].notna()) & (df['MODIS_Pred'] != -999)].copy()
        print(f"\n✅ 有效匹配点数: {len(valid_df)}")
        
        if len(valid_df) > 0:
            df_cloud = valid_df[valid_df['is_cloud_originally'] == True]
            df_clear = valid_df[valid_df['is_cloud_originally'] == False]
            
            print(f"   - 原始被云覆盖 (Cloud): {len(df_cloud)}")
            print(f"   - 原始晴空 (Clear):     {len(df_clear)}")
            
            out_csv = OUTPUT_DIR / "Final_MultiBand_Validation.csv"
            valid_df.to_csv(out_csv, index=False)
            print(f"   📄 详细结果已保存至: {out_csv.name}")

            # 绘图
            fig, axes = plt.subplots(1, 3, figsize=(18, 5))
            plot_cm(valid_df['manual_label'], valid_df['MODIS_Pred'], "1. Overall Performance", axes[0])
            
            if len(df_clear) > 0:
                plot_cm(df_clear['manual_label'], df_clear['MODIS_Pred'], "2. Originally Clear Sky", axes[1])
            else:
                axes[1].text(0.5, 0.5, 'No Clear Sky Data', ha='center')
                axes[1].set_title("Originally Clear Sky")
            
            if len(df_cloud) > 0:
                plot_cm(df_cloud['manual_label'], df_cloud['MODIS_Pred'], "3. Cloud Recovered Pixels", axes[2])
            else:
                axes[2].text(0.5, 0.5, 'No Cloud Data Found', ha='center')
                axes[2].set_title("Cloud Recovered Pixels")
                
            plt.tight_layout()
            
            # 保存图表
            plot_path = DATA_DIR / "plots" / "Confusion_Matrix_Validation.png"
            plot_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"   📈 混淆矩阵图表已保存至: {plot_path.name}")
            
            plt.show()
        else:
            print("❌ 匹配数为0。")
