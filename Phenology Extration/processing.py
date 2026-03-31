import pandas as pd
from scipy.signal import savgol_filter

def clean_seasonal_noise(df):
    """季节性噪声清洗函数 (去除初冬/末春假冰)"""
    df_clean = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_clean['date']):
        df_clean['date'] = pd.to_datetime(df_clean['date'])

    # 初冬清洗 (11月)
    mask_early = df_clean['date'].dt.month == 11
    mask_early_noise = mask_early & (df_clean['ice_percentage'] > 15.0)
    if mask_early_noise.any():
        print(f"  - [物理清洗] 检测到11月异常高值(>15%)，清洗 {mask_early_noise.sum()} 个数据点。")
        df_clean.loc[mask_early_noise, 'ice_percentage'] = 0.0
    
    # 末春清洗 (6月)
    mask_late = df_clean['date'].dt.month == 6
    mask_late_noise = mask_late & (df_clean['ice_percentage'] > 15.0)
    if mask_late_noise.any():
        print(f"  - [物理清洗] 检测到6月异常高值(>15%)，清洗 {mask_late_noise.sum()} 个数据点。")
        df_clean.loc[mask_late_noise, 'ice_percentage'] = 0.0
        
    return df_clean

def apply_median_filter(df, window=5):
    """中值滤波：去除孤立噪声点"""
    df_copy = df.copy()
    if df_copy['ice_percentage'].isnull().any():
        df_copy['ice_percentage'] = df_copy['ice_percentage'].interpolate(method='linear', limit_direction='both')

    df_copy['ice_percentage'] = df_copy['ice_percentage'].rolling(
        window=window, center=True, min_periods=1
    ).median()
    return df_copy

def calculate_moving_average_sg(df, window=9, polyorder=2):
    """Savitzky-Golay 滤波器平滑处理"""
    df_copy = df.copy()
    if df_copy['ice_percentage'].isnull().any():
        df_copy['ice_percentage'] = df_copy['ice_percentage'].interpolate(method='linear', limit_direction='both')
    
    data_len = len(df_copy)
    if data_len < window:
        window = data_len if data_len % 2 == 1 else data_len - 1
        if window < 3: 
            df_copy['moving_avg'] = df_copy['ice_percentage']
            return df_copy

    try:
        df_copy['moving_avg'] = savgol_filter(
            df_copy['ice_percentage'], 
            window_length=window, 
            polyorder=polyorder,
            mode='interp'
        )
        df_copy['moving_avg'] = df_copy['moving_avg'].clip(0, 100)
    except Exception as e:
        print(f"S-G滤波出错: {e}")
        df_copy['moving_avg'] = df_copy['ice_percentage']
        
    return df_copy
