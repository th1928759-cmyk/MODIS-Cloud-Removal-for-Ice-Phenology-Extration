import os
import pandas as pd
from processing import clean_seasonal_noise, apply_median_filter, calculate_moving_average_sg
from phenology import extract_phenology_dates, calculate_durations
from plotting import plot_phenology_curve

def get_valid_year():
    while True:
        try:
            year = input("请输入要处理的年份 (例如: 2024): ")
            year = int(year.strip())
            if 2000 <= year <= 2100: return year
            print("年份必须在2000-2100之间。")
        except ValueError:
            print("请输入有效的年份数字。")

def process_year(year):
    # 路径指向上级目录中的 data 文件夹
    csv_path = os.path.join("..", "data", "results", "statistics", f"coverage_{year}.csv")
    if not os.path.exists(csv_path):
        print(f"❌ 错误: 找不到文件 {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    
    # 预处理
    df.columns = [c.lower() for c in df.columns]
    col_map = {'ice': 'ice_percentage', 'ice %': 'ice_percentage'}
    df = df.rename(columns=col_map)
    
    try:
        df['date'] = df['date'].astype(str).str.replace(r'[\s\-\/]', '', regex=True)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    except:
        print("日期格式解析失败，请确保CSV中包含YYYYMMDD格式日期")
        return

    # 1. 物理清洗
    print("正在执行季节性物理清洗 (去除初冬/末春假冰)...")
    df = clean_seasonal_noise(df)

    # 2. 中值滤波
    print("正在进行中值滤波 (去除突变噪声)...")
    df = apply_median_filter(df, window=5)

    # 3. SG滤波
    print("正在进行 SG 滤波平滑...")
    df_sg = calculate_moving_average_sg(df, window=9, polyorder=2)
    
    # 4. 提取物候
    print("正在提取物候日期 (稳定性判定)...")
    phenology = extract_phenology_dates(df_sg, stability_days=30)
    
    # 5. 计算时长
    durations = calculate_durations(phenology)
    
    # 6. 输出结果
    print("\n" + "="*40)
    print(f"{year}-{year+1} 贝加尔湖冰情物候结果:")
    print("="*40)
    for k, v in phenology.items():
        d_str = v.strftime('%Y-%m-%d') if v is not None else "未识别"
        print(f"  {k}: {d_str}")
    
    print("-" * 20)
    print(f"  ICD: {durations['ICD'] if durations['ICD'] else 'N/A'} 天")
    print(f"  CFD: {durations['CFD'] if durations['CFD'] else 'N/A'} 天")
    print(f"  FUD: {durations['FUD'] if durations['FUD'] else 'N/A'} 天")
    print(f"  BUD: {durations['BUD'] if durations['BUD'] else 'N/A'} 天")
    print("="*40 + "\n")
    
    # 7. 绘图
    plot_phenology_curve(df_sg, phenology, year, durations)

if __name__ == "__main__":
    print("=== 湖冰物候提取程序 (物理清洗+中值+SG) ===")
    y = get_valid_year()
    process_year(y)
