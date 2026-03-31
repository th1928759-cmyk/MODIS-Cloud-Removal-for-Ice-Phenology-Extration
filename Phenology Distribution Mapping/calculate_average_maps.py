import os
import glob
from core.algorithms import calculate_average_map
from core.io_utils import save_geotiff
from core.constants import OUTPUT_NODATA

def process_average(work_dir, prefix, out_filename):
    # 递归查找历年该前缀的 TIF
    pattern = os.path.join(work_dir, "20*", f"{prefix}_20*.tif")
    tif_files = sorted(glob.glob(pattern))
    
    if not tif_files:
        print(f"❌ 未找到 {prefix} 系列文件，跳过。")
        return
        
    print(f"\n正在计算 {prefix} 系列均值，共 {len(tif_files)} 个可用年份...")
    avg_array, meta = calculate_average_map(tif_files)
    
    out_path = os.path.join(work_dir, out_filename)
    save_geotiff(avg_array, out_path, meta, dtype='float32', nodata=float(OUTPUT_NODATA))
    print(f"✅ 平均值计算完毕: {out_path}")

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    work_dir = os.path.abspath(os.path.join(current_dir, "..", "data", "results", "spatial_products"))
    
    if not os.path.exists(work_dir):
        print("❌ 未找到空间产品目录，请先运行 generate_annual_maps.py。")
        return
        
    process_average(work_dir, "BU", "BU_Average.tif")
    print("-" * 30)
    process_average(work_dir, "FU", "FU_Average.tif")
    
    print("\n🎉 所有平均空间格局计算完毕。")

if __name__ == "__main__":
    main()
