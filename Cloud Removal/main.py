import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from pathlib import Path

# 从核心库导入算法模块
from core.constants import CLOUD, NODATA
from core.utils import get_ice_season_dates
from core.classify import classify_pixel, solve_dual_satellite
from core.smooth import temporal_smooth_strict, spatial_smooth

def run():
    year_str = input("请输入起始年份 (如 2003): ").strip()
    try:
        year = int(year_str)
    except ValueError:
        print("❌ 输入年份无效。")
        return
        
    base_dir = Path(f"./data/{year}") # 建议归拢到 data 目录下
    roi_path = Path("./data/range/Baikal_Lake_Boundary.shp")
    output_dir = Path(f"./result/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not roi_path.exists():
        print(f"❌ 找不到 SHP 文件: {roi_path}")
        return
        
    roi = gpd.read_file(roi_path)
    dates = get_ice_season_dates(year)
    
    cube = []
    meta = None
    valid_dates = []
    
    print(f"\n🚀 启动 {year} 冰物候年去云处理程序")
    print("Step 1: 读取原始数据、根据 SHP 裁剪并进行双星合成...")
    
    for d in dates:
        d_str = d.strftime("%Y%m%d")
        mod_p = base_dir / f"MOD10A1_{d_str}.tif"
        myd_p = base_dir / f"MYD10A1_{d_str}.tif"
        
        day_imgs = []
        for p in [mod_p, myd_p]:
            if p.exists():
                with rasterio.open(p) as src:
                    roi_proj = roi.to_crs(src.crs)
                    out_img, out_trans = mask(src, roi_proj.geometry, crop=True, nodata=NODATA)
                    
                    if meta is None:
                        meta = src.meta.copy()
                        meta.update({
                            "driver": "GTiff", 
                            "height": out_img.shape[1], 
                            "width": out_img.shape[2],
                            "count": 1, 
                            "dtype": "uint8", 
                            "nodata": NODATA, 
                            "transform": out_trans
                        })
                    
                    day_imgs.append(classify_pixel(out_img[0], out_img[1]))
            else:
                day_imgs.append(None)
        
        if day_imgs[0] is None and day_imgs[1] is None:
            if meta:
                day_res = np.full((meta['height'], meta['width']), CLOUD, dtype=np.uint8)
            else:
                day_res = None
        else:
            day_res = solve_dual_satellite(day_imgs[0], day_imgs[1], d.month)
            
        if day_res is not None:
            cube.append(day_res)
            valid_dates.append(d)

    if not cube:
        print("❌ 未发现任何可用数据，程序终止。")
        return

    cube = np.array(cube)

    print("\nStep 2: 正在进行严格 t±2 范围的双向时序平滑...")
    cube = temporal_smooth_strict(cube, valid_dates)

    print("\nStep 3: 正在进行空间平滑并按 YYYYMMDD 格式导出...")
    for i, d in enumerate(valid_dates):
        final_map = spatial_smooth(cube[i])
        
        out_file = output_dir / f"{d.strftime('%Y%m%d')}.tif"
        with rasterio.open(out_file, "w", **meta) as dst:
            dst.write(final_map, 1)

    print(f"\n🎉 处理完成！无云结果已保存至: {output_dir.absolute()}")

if __name__ == "__main__":
    run()
