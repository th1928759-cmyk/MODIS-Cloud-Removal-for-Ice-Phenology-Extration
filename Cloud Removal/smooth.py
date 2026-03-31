# core/smooth.py
import numpy as np
from .constants import WATER, ICE, CLOUD, NODATA
from .utils import get_priority_value

def temporal_smooth_strict(cube, dates_list):
    """严格限定在 t±2 范围内的双向时序平滑"""
    T = len(cube)
    out_cube = np.copy(cube)

    def run_pass(data_cube, date_array):
        for t in range(T):
            priority = get_priority_value(date_array[t].month, ICE, WATER)
            mask_cloud = (data_cube[t] == CLOUD)
            
            if not np.any(mask_cloud): 
                continue
            
            for dt in [1, 2]:
                p_idx = t - dt
                n_idx = t + dt
                
                prev_v = data_cube[p_idx] if p_idx >= 0 else None
                next_v = data_cube[n_idx] if n_idx < T else None
                current_clouds = (data_cube[t] == CLOUD)
                
                if prev_v is not None and next_v is not None:
                    mask_same = (prev_v == next_v) & (prev_v != CLOUD) & (prev_v != NODATA)
                    fill_mask = current_clouds & mask_same
                    data_cube[t][fill_mask] = prev_v[fill_mask]
                    
                    current_clouds = (data_cube[t] == CLOUD)
                    mask_diff = (prev_v != CLOUD) & (prev_v != NODATA) & \
                                (next_v != CLOUD) & (next_v != NODATA) & (prev_v != next_v)
                    fill_mask_diff = current_clouds & mask_diff
                    data_cube[t][fill_mask_diff] = priority
                    
                current_clouds = (data_cube[t] == CLOUD)
                if prev_v is not None:
                    mask_p_only = (prev_v != CLOUD) & (prev_v != NODATA)
                    fill_mask_p = current_clouds & mask_p_only
                    data_cube[t][fill_mask_p] = prev_v[fill_mask_p]
                    
                current_clouds = (data_cube[t] == CLOUD)
                if next_v is not None:
                    mask_n_only = (next_v != CLOUD) & (next_v != NODATA)
                    fill_mask_n = current_clouds & mask_n_only
                    data_cube[t][fill_mask_n] = next_v[fill_mask_n]

                if not np.any(data_cube[t] == CLOUD):
                    break
        return data_cube

    print("  -> 执行正向时序平滑...")
    out_cube = run_pass(out_cube, dates_list)
    
    print("  -> 执行反向时序平滑...")
    rev_cube = out_cube[::-1].copy()
    rev_dates = dates_list[::-1]
    rev_cube = run_pass(rev_cube, rev_dates)
    
    return rev_cube[::-1]

def spatial_smooth(data):
    """基于 3x3 窗口的 8 邻域空间平滑"""
    rows, cols = data.shape
    out = np.copy(data)
    cloud_indices = np.argwhere(data == CLOUD)
    
    for r, c in cloud_indices:
        if 0 < r < rows-1 and 0 < c < cols-1:
            window = data[r-1:r+2, c-1:c+2].flatten()
            neighbors = np.delete(window, 4)
            for target in [ICE, WATER]:
                if np.sum(neighbors == target) >= 5:
                    out[r, c] = target
                    break
    return out
