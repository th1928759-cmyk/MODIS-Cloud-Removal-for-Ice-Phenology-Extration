import numpy as np
from .constants import WATER, ICE, CLOUD, NODATA, CLOUD_VALUES
from .utils import get_priority_value

def classify_pixel(data_band1, data_band2):
    """根据双波段阈值划分水、冰、云"""
    result = np.full(data_band1.shape, NODATA, dtype=np.uint8)
    result[data_band1 == 0] = WATER
    result[(data_band1 >= 1) & (data_band1 <= 100)] = ICE
    
    cloud_mask = np.isin(data_band2, CLOUD_VALUES)
    result[cloud_mask] = CLOUD
    
    return result

def solve_dual_satellite(mod, myd, month):
    """双星合成逻辑"""
    if mod is None: return myd
    if myd is None: return mod
    
    combined = np.copy(mod)
    priority = get_priority_value(month, ICE, WATER)
    
    # 只要一个是明确地物(非云非无数据)，就覆盖云
    valid_myd = (myd != CLOUD) & (myd != NODATA)
    combined[(mod == CLOUD) & valid_myd] = myd[(mod == CLOUD) & valid_myd]
    
    # 双星冲突且都不是云，按月份优先级赋予
    conflict = (mod != CLOUD) & (myd != CLOUD) & (mod != myd) & (mod != NODATA)
    combined[conflict] = priority
    
    return combined
