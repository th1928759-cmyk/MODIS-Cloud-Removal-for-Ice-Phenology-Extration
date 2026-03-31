import pandas as pd
from pathlib import Path
from osgeo import gdal
import datetime

from core.cloud_utils import get_ice_phenology_days, create_shp_mask, calculate_masked_cloud_fraction

# 屏蔽 GDAL 警告
gdal.UseExceptions()
gdal.PushErrorHandler('CPLQuietErrorHandler')

def main():
    year_in = input("请输入统计年份 (例如 2013): ")
    try:
        start_year = int(year_in)
    except ValueError:
        print("年份输入无效。")
        return

    # --- 相对路径配置 ---
    current_dir = Path(__file__).parent.absolute()
    base_dir = current_dir.parent / "data" / "raw" / str(start_year)
    roi_path = current_dir.parent / "data" / "range" / "Baikal_Lake_Boundary.shp"
    
    # 修正：写入到 result 文件夹
    output_dir = current_dir.parent / "data" / "result" / "statistics"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not roi_path.exists():
        print(f"❌ 找不到Shapefile: {roi_path}")
        return
    if not base_dir.exists():
        print(f"❌ 找不到原始数据目录: {base_dir}")
        return

    date_series = get_ice_phenology_days(start_year)
    results = []

    print(f"\n--- 正在基于 {roi_path.name} 提取 {start_year} 物候年云占比 ---")
    
    lake_mask = None
    for date in date_series:
        d_str = date.strftime("%Y%m%d")
        mod_path = base_dir / f"MOD10A1_{d_str}.tif"
        if mod_path.exists():
            lake_mask = create_shp_mask(mod_path, roi_path)
            if lake_mask is not None:
                print(f"✅ 成功生成精确湖泊掩膜！")
                break
    
    if lake_mask is None:
        print("❌ 无法生成掩膜，未找到影像参考。")
        return

    for date in date_series:
        d_str = date.strftime("%Y%m%d")
        mod_path = base_dir / f"MOD10A1_{d_str}.tif"
        myd_path = base_dir / f"MYD10A1_{d_str}.tif"
        
        results.append({
            "Date": d_str,
            "MOD10A1_Cloud_%": calculate_masked_cloud_fraction(mod_path, lake_mask),
            "MYD10A1_Cloud_%": calculate_masked_cloud_fraction(myd_path, lake_mask)
        })

    df = pd.DataFrame(results)
    csv_path = output_dir / f"Cloud_Fraction_SHP_Masked_{start_year}.csv"
    
    try:
        df.to_csv(csv_path, index=False)
        print(f"\n✅ 统计结果已保存至:\n{csv_path}")
    except PermissionError:
        new_csv_path = output_dir / f"Cloud_Fraction_SHP_Masked_{start_year}_{datetime.datetime.now().strftime('%H%M%S')}.csv"
        df.to_csv(new_csv_path, index=False)
        print(f"\n⚠️ 原CSV占用，已另存为:\n{new_csv_path}")

    # 计算均值
    valid_mod = pd.to_numeric(df["MOD10A1_Cloud_%"], errors='coerce')
    valid_myd = pd.to_numeric(df["MYD10A1_Cloud_%"], errors='coerce')
    all_valid = pd.concat([valid_mod, valid_myd]).dropna()
    
    if not all_valid.empty:
        print(f"\n📊 研究时段平均云覆盖率: {all_valid.mean():.2f}%")
    else:
        print("\n📊 无有效数据进行平均计算。")

if __name__ == "__main__":
    main()
