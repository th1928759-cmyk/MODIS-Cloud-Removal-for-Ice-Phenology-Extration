import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 设置绘图风格
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['axes.unicode_minus'] = False 

def plot_phenology_curve(df, phenology_dates, year, durations):
    """绘制 SG滤波后的湖冰曲线及物候点"""
    try:
        plt.figure(figsize=(14, 5))
        plt.plot(df['date'], df['moving_avg'], 
                 color='#1f77b4', linewidth=2.5, label='Smoothed Ice Coverage (Median+SG)')
        
        plt.axhline(y=10, color='gray', linestyle='--', linewidth=1, alpha=0.6)
        plt.axhline(y=90, color='gray', linestyle='--', linewidth=1, alpha=0.6)
        
        plt.text(-0.018, 0.10, '10', transform=plt.gca().transAxes, color='gray', fontsize=10, va='center', ha='left')
        plt.text(-0.018, 0.90, '90', transform=plt.gca().transAxes, color='gray', fontsize=10, va='center', ha='left')

        markers = {'FUS': 'o', 'FUE': 'D', 'BUS': 'D', 'BUE': 'o'}
        colors = {'FUS': '#2ca02c', 'FUE': '#d62728', 'BUS': '#ff7f0e', 'BUE': '#9467bd'} 
        
        for key, date_val in phenology_dates.items():
            if date_val is not None:
                try:
                    y_val = df.loc[df['date'] == date_val, 'moving_avg'].values[0]
                    date_str = date_val.strftime('%b-%d')
                    plt.scatter(date_val, y_val, s=120, zorder=10,
                                c=colors[key], edgecolors='white', linewidth=1.5,
                                marker=markers[key], label=f"{key}: {date_str}")
                    plt.annotate(f"{key}\n{date_str}", 
                                 xy=(date_val, y_val), 
                                 xytext=(0, 15 if y_val < 50 else -25),
                                 textcoords="offset points", 
                                 ha='center', fontsize=9, fontweight='bold',
                                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
                except IndexError:
                    pass

        duration_text = f"ICD: {durations['ICD'] if durations['ICD'] else 'N/A'} days\n"
        duration_text += f"CFD: {durations['CFD'] if durations['CFD'] else 'N/A'} days\n"
        duration_text += f"FUD: {durations['FUD'] if durations['FUD'] else 'N/A'} days\n"
        duration_text += f"BUD: {durations['BUD'] if durations['BUD'] else 'N/A'} days"
            
        plt.text(0.87, 0.82, duration_text, transform=plt.gca().transAxes,
                 fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='#ffffff', alpha=0.8, edgecolor='#cccccc'))

        plt.title(f'Lake Baikal Ice Phenology ({year}-{year+1})', fontsize=16, pad=15)
        plt.ylabel('Ice Coverage (%)', fontsize=12)
        plt.xlabel('Date', fontsize=12)
        plt.ylim(0, 100)
        plt.xlim(df['date'].iloc[0], df['date'].iloc[-1])
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.25), frameon=False)
        plt.tight_layout()
        
        # 保存路径建议指向项目根目录下的统一输出文件夹
        output_dir = os.path.join("..", "data", "plots")
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, f"phenology_sg_{year}.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        print(f"图表已保存至: {save_path}")
        
    except Exception as e:
        print(f"绘图错误: {e}")
