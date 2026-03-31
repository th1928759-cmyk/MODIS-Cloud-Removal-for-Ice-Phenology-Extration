import datetime
import numpy as np
import pandas as pd
from pathlib import Path
from osgeo import gdal, ogr
import os

gdal.UseExceptions()
gdal.PushErrorHandler('CPLQuietErrorHandler')

def get_ice_phenology_days(start_year):
    start_date = datetime.date(start_year, 11, 1)
    return [start_date + datetime.timedelta(days=i) for i in range(242)]

def create_shp_mask(ref_tif_path, shp_path):
    ref_ds = gdal.Open(str(ref_tif_path))
    if ref_ds is None: return None
    
    x_size = ref_ds.RasterXSize
    y_size = ref_ds.RasterYSize
    geo_transform = ref_ds.GetGeoTransform()
    projection = ref_ds.GetProjection()
    
    mem_driver = gdal.GetDriverByName('MEM')
    mask_ds = mem_driver.Create('', x_size, y_size, 1, gdal.GDT_Byte)
    mask_ds.SetGeoTransform(geo_transform)
    mask_ds.SetProjection(projection)
    
    shp_ds = ogr.Open(str(shp_path))
    if shp_ds is None: raise FileNotFoundError(f"无法打开 SHP: {shp_path}")
    layer = shp_ds.GetLayer()
    
    gdal.RasterizeLayer(mask_ds, [1], layer, burn_values=[1])
    mask_array = mask_ds.GetRasterBand(1).ReadAsArray()
    
    ref_ds, mask_ds, shp_ds = None, None, None
    return mask_array == 1 

def calculate_masked_cloud_fraction(file_path, lake_mask):
    if not file_path.exists(): return None
    try:
        ds = gdal.Open(str(file_path))
        if ds is None: return None
        b2 = ds.GetRasterBand(2).ReadAsArray()
        
        valid_pixels_mask = lake_mask & (b2 != 255)
        valid_count = np.sum(valid_pixels_mask)
        if valid_count == 0: return 0.0
            
        cloud_values = [200, 201, 211, 250, 254]
        cloud_pixels_mask = np.isin(b2, cloud_values) & valid_pixels_mask
        cloud_count = np.sum(cloud_pixels_mask)
        
        return round((cloud_count / valid_count) * 100, 2)
    except Exception as e:
        print(f"读取异常 {file_path.name}: {e}")
        return None

def main():
    year_in = input("请输入统计年份 (例如 2013): ")
    try:
        start_year = int(year_in)
    except ValueError:
        print("年份输入无效。")
        return

    # --- 动态相对路径配置 ---
    current_dir = Path(__file__).parent.absolute()
    base_dir = current_dir.parent / "data" / "raw" / str(start_year)
    roi_path = current_dir.parent / "data" / "range" / "Baikal_Lake_Boundary.shp"
    output_dir = current_dir.parent / "data" / "results" / "statistics"
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

    valid_mod = pd.to_numeric(df["MOD10A1_Cloud_%"], errors='coerce')
    valid_myd = pd.to_numeric(df["MYD10A1_Cloud_%"], errors='coerce')
    all_valid = pd.concat([valid_mod, valid_myd]).dropna()
    
    if not all_valid.empty:
        print(f"\n📊 研究时段平均云覆盖率: {all_valid.mean():.2f}%")
    else:
        print("\n📊 无有效数据进行平均计算。")

if __name__ == "__main__":
    main()
