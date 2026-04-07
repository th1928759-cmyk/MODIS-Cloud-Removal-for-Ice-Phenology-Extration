import pandas as pd
import matplotlib.pyplot as plt
import warnings
from pathlib import Path

from core.validation_utils import build_result_index, build_raw_index, check_cloud_status, extract_prediction, plot_cm

warnings.filterwarnings('ignore')
plt.rcParams['font.family'] = 'Times New Roman'

def main():
    print("========== 🚀 精度验证与混淆矩阵 ==========")
    
    # --- 相对路径配置 (修正为 result) ---
    CURRENT_DIR = Path(__file__).parent.absolute()
    DATA_DIR = CURRENT_DIR.parent / "data"

    RESULT_ROOT_DIR = DATA_DIR / "result"
    RAW_ROOT_DIR = DATA_DIR
    CSV_PATH = DATA_DIR / "ground_truth" / "S1_GroundTruth_Projected.csv"
    
    OUTPUT_DIR = DATA_DIR / "result" / "validation"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not CSV_PATH.exists():
        print(f"❌ 找不到真值 CSV: {CSV_PATH}\n请确保文件位于 data/ground_truth/ 目录下。")
        return

    print("1 & 2. 建立原始与去云结果的影像索引...")
    res_idx = build_result_index(RESULT_ROOT_DIR)
    raw_idx = build_raw_index(RAW_ROOT_DIR)

    print("\n3. 读取并处理 CSV...")
    df = pd.read_csv(CSV_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['manual_label'] != -1].copy()
    
    print("   正在扫描所有波段查找云覆盖...")
    df['is_cloud_originally'] = df.apply(lambda row: check_cloud_status(row, raw_idx), axis=1)
    
    print("   提取模型分类结果...")
    df['MODIS_Pred'] = df.apply(lambda row: extract_prediction(row, res_idx), axis=1)
    
    valid_df = df[(df['MODIS_Pred'].notna()) & (df['MODIS_Pred'] != -999)].copy()
    print(f"\n✅ 有效匹配点数: {len(valid_df)}")
    
    if len(valid_df) > 0:
        df_cloud = valid_df[valid_df['is_cloud_originally'] == True]
        df_clear = valid_df[valid_df['is_cloud_originally'] == False]
        
        print(f"   - 原始被云覆盖 (Cloud): {len(df_cloud)}")
        print(f"   - 原始晴空 (Clear):     {len(df_clear)}")
        
        out_csv = OUTPUT_DIR / "Final_MultiBand_Validation.csv"
        valid_df.to_csv(out_csv, index=False)
        print(f"   📄 详细结果已保存至: {out_csv}")

        # ================= 绘图与精度打印 =================
        fig, axes = plt.subplots(1, 3, figsize=(18, 5.5)) # 高度稍微调大一点以容纳多行标题
        
        # 1. 总体精度
        oa, kp, f1_w, f1_i, f1_m = plot_cm(valid_df['manual_label'], valid_df['MODIS_Pred'], "1. Overall Performance", axes[0])
        print("\n📊 【总体表现 (Overall)】")
        print(f"   OA: {oa:.2%} | Kappa: {kp:.3f}")
        print(f"   F1-Water: {f1_w:.3f} | F1-Ice: {f1_i:.3f} | Macro-F1: {f1_m:.3f}")
        
        # 2. 原始晴空精度
        if len(df_clear) > 0:
            oa_clr, kp_clr, f1_w_clr, f1_i_clr, f1_m_clr = plot_cm(df_clear['manual_label'], df_clear['MODIS_Pred'], "2. Originally Clear Sky", axes[1])
            print("\n☀️ 【原始晴空 (Clear Sky)】")
            print(f"   OA: {oa_clr:.2%} | Kappa: {kp_clr:.3f}")
            print(f"   F1-Water: {f1_w_clr:.3f} | F1-Ice: {f1_i_clr:.3f} | Macro-F1: {f1_m_clr:.3f}")
        else:
            axes[1].text(0.5, 0.5, 'No Clear Sky Data', ha='center')
            axes[1].set_title("Originally Clear Sky")
        
        # 3. 云下恢复精度
        if len(df_cloud) > 0:
            oa_cld, kp_cld, f1_w_cld, f1_i_cld, f1_m_cld = plot_cm(df_cloud['manual_label'], df_cloud['MODIS_Pred'], "3. Cloud Recovered Pixels", axes[2])
            print("\n☁️ 【云下恢复 (Cloud Recovered)】")
            print(f"   OA: {oa_cld:.2%} | Kappa: {kp_cld:.3f}")
            print(f"   F1-Water: {f1_w_cld:.3f} | F1-Ice: {f1_i_cld:.3f} | Macro-F1: {f1_m_cld:.3f}")
        else:
            axes[2].text(0.5, 0.5, 'No Cloud Data Found', ha='center')
            axes[2].set_title("Cloud Recovered Pixels")
            
        plt.tight_layout()
        
        # 保存图表至统一的 plots 文件夹
        plot_path = DATA_DIR / "plots" / "Confusion_Matrix_Validation.png"
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"\n📈 混淆矩阵图表已保存至: {plot_path}")
        
        plt.show()
    else:
        print("❌ 匹配数为0。")

if __name__ == "__main__":
    main()
