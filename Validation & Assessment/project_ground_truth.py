import os
import glob
import pandas as pd
import geopandas as gpd
from pathlib import Path

def main():
    print("========== 🌍 Ground Truth 坐标投影与合并 ==========")
    
    # --- 1. 配置相对路径 ---
    current_dir = Path(__file__).parent.absolute()
    ground_truth_dir = current_dir.parent / "data" / "ground_truth"
    raw_exports_dir = ground_truth_dir / "raw_exports"
    
    # 输出文件，正是 accuracy_assessment.py 需要读取的名字
    output_file = ground_truth_dir / "S1_GroundTruth_Projected.csv"

    if not raw_exports_dir.exists():
        print(f"❌ 找不到原始导出目录: {raw_exports_dir}")
        print("请在 data/ground_truth/ 下创建 raw_exports 文件夹，并将 GEE 下载的 CSV 放入其中。")
        return

    # --- 2. 扫描并合并所有 GEE 导出的 CSV ---
    csv_files = glob.glob(str(raw_exports_dir / "*.csv"))
    
    if len(csv_files) == 0:
        print(f"❌ 在 {raw_exports_dir} 中未找到任何 CSV 文件。")
        return
        
    print(f"✅ 找到 {len(csv_files)} 个原始导出文件，正在合并...")
    
    df_list = []
    for file in csv_files:
        try:
            temp_df = pd.read_csv(file)
            # 检查必须的列是否存在 (GEE 导出时包含的列)
            required_cols = ['date', 'lat', 'lon', 'manual_label']
            if not all(col in temp_df.columns for col in required_cols):
                print(f"⚠️ 跳过文件 {os.path.basename(file)}: 缺少必需的列 (lat, lon 等)")
                continue
            df_list.append(temp_df)
        except Exception as e:
            print(f"⚠️ 读取文件 {os.path.basename(file)} 时出错: {e}")

    if not df_list:
        print("❌ 没有有效的数据被合并。")
        return

    # 合并为一个大的 DataFrame
    master_df = pd.concat(df_list, ignore_index=True)
    print(f"✅ 合并完成，总计 {len(master_df)} 个验证点。")

    # --- 3. 坐标投影转换 (WGS84 -> EPSG:32648) ---
    print("🔄 正在进行坐标转换 (EPSG:4326 -> EPSG:32648)...")
    
    # 将 Pandas DataFrame 转换为 GeoDataFrame，指定原始坐标系为 WGS84 (EPSG:4326)
    gdf = gpd.GeoDataFrame(
        master_df, 
        geometry=gpd.points_from_xy(master_df.lon, master_df.lat),
        crs="EPSG:4326"
    )

    # 转换投影到贝加尔湖常用的 UTM 区域 (EPSG:32648)
    gdf_projected = gdf.to_crs("EPSG:32648")

    # 提取转换后的 X 和 Y 坐标到新列 'proj_x' 和 'proj_y'
    master_df['proj_x'] = gdf_projected.geometry.x
    master_df['proj_y'] = gdf_projected.geometry.y

    # --- 4. 数据清理与保存 ---
    # 去除由于在 GEE 中可能点击了 "❓ 跳过" 产生的 -1 标签
    initial_count = len(master_df)
    master_df = master_df[master_df['manual_label'] != -1]
    filtered_count = initial_count - len(master_df)
    if filtered_count > 0:
        print(f"🧹 已清理 {filtered_count} 个标记为未知 (-1) 的点。")

    # 保存最终结果
    master_df.to_csv(output_file, index=False)
    print(f"🎉 处理成功！带有 proj_x 和 proj_y 的投影文件已保存至:\n   {output_file}")
    print("下一步：您可以直接运行 accuracy_assessment.py 进行精度验证了！")

if __name__ == "__main__":
    main()
