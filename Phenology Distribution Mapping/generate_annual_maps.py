import os
import glob
import traceback
import numpy as np

from core.constants import ICE_VALUE, NODATA_VALUE, OUTPUT_NODATA, CHECK_WINDOW, THRESHOLD_LOW, THRESHOLD_HIGH
from core.io_utils import get_sorted_tif_files, load_data_cube, save_geotiff
from core.algorithms import calculate_phenology_vectorized

def process_year(year_str, input_dir, output_dir):
    print(f"\n====== 开始处理 {year_str} 冰物候年 ======")
    year_dir = os.path.join(input_dir, year_str)
    files = get_sorted_tif_files(year_dir)
    if not files: return
    
    # 1. 加载数据立方体
    print(f"  -> 加载 {len(files)} 幅影像...")
    stack, profile, valid_mask = load_data_cube(files, NODATA_VALUE)
    if stack is None: return

    ice_bool = (stack == ICE_VALUE).astype(np.int8)
    
    # 2. 计算 FU (正序)
    print("  -> 正在计算 FU (正序)...")
    fu_map = calculate_phenology_vectorized(ice_bool, CHECK_WINDOW, THRESHOLD_LOW, THRESHOLD_HIGH)
    
    # 3. 计算 BU (倒序)
    print("  -> 正在计算 BU (倒序)...")
    stack_rev = ice_bool[::-1]
    bu_raw_idx_map = calculate_phenology_vectorized(stack_rev, CHECK_WINDOW, THRESHOLD_LOW, THRESHOLD_HIGH)
    
    total_days = len(files)
    bu_map = np.full(fu_map.shape, OUTPUT_NODATA, dtype=np.int16)
    valid_bu = (bu_raw_idx_map != OUTPUT_NODATA)
    bu_map[valid_bu] = total_days - bu_raw_idx_map[valid_bu] + 1

    # 4. 应用掩膜
    fu_map[~valid_mask] = OUTPUT_NODATA
    bu_map[~valid_mask] = OUTPUT_NODATA

    # 5. 保存结果
    fu_path = os.path.join(output_dir, year_str, f"FU_{year_str}.tif")
    bu_path = os.path.join(output_dir, year_str, f"BU_{year_str}.tif")
    
    save_geotiff(fu_map, fu_path, profile, dtype='int16', nodata=OUTPUT_NODATA)
    save_geotiff(bu_map, bu_path, profile, dtype='int16', nodata=OUTPUT_NODATA)
    print(f"✅ 结果已保存至 {os.path.dirname(fu_path)}")

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.abspath(os.path.join(current_dir, "..", "data", "results"))
    output_dir = os.path.abspath(os.path.join(current_dir, "..", "data", "results", "spatial_products"))
    
    year_dirs = sorted(glob.glob(os.path.join(input_dir, "20*")))
    print(f"检测到 {len(year_dirs)} 个年份文件夹，开始批量制图...")
    
    for yd in year_dirs:
        year_str = os.path.basename(yd)
        if year_str.isdigit():
            try:
                process_year(year_str, input_dir, output_dir)
            except Exception as e:
                print(f"❌ 处理 {year_str} 时出错: {e}")
                traceback.print_exc()
                
    print("\n🎉 所有年份空间物候制图处理完毕。")

if __name__ == "__main__":
    main()
