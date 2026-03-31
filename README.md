# 🧊 基于MODIS去云算法的贝加尔湖湖冰物候提取

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![GDAL](https://img.shields.io/badge/GDAL-3.0%2B-green)
![Rasterio](https://img.shields.io/badge/Rasterio-1.2%2B-green)
![License](https://img.shields.io/badge/License-MIT-orange)

高纬度大型湖泊（以贝加尔湖为例）在冬春季节经常被厚厚的云层遮挡，导致传统光学遥感（如 MODIS）很难获取连续、清晰的冰面观测数据。本项目就是为了解决这个“看天吃饭”的痛点而开发的。

本仓库提供了一套完整的、端到端（End-to-End）的处理流水线：从**原始影像的云量评估**，到**时空双向去云重构**，再到**时序/空间物候参数提取**，最后利用 Sentinel-1 微波雷达数据进行**高精度交叉验证**。整个流程高度模块化，数据与代码严格分离，开箱即用。



## ✨ 核心亮点 

- **☁️ 递进式时空去云算法**：不依赖复杂的深度学习模型，直接结合“双星合成 (Terra+Aqua)”、严格的“$t\pm2$ 双向时序平滑”与“$3\times3$ 空间滤波”，稳健重构连续无云的每日湖冰状态。
- **📈 鲁棒的时序物候提取**：结合季节性物理去噪、中值滤波与 Savitzky-Golay (SG) 平滑，应用不可逆阈值判定逻辑，精确提取全湖四大关键物候节点：FUS (初冻日)、FUE (完全封冻日)、BUS (初融日)、BUE (完全解冻日)。
- **🗺️ 高效的空间格局制图**：抛弃了缓慢的循环遍历，底层全部采用 Numpy 矩阵向量化运算，几十秒内即可输出逐年及多年平均的 FU (Freeze-up) 和 BU (Break-up) 像素级空间分布图。
- **✅ 严谨的 SAR 交叉验证**：内置真值坐标投影转换与混淆矩阵评估模块，利用不受云层影响的 Sentinel-1 雷达数据，硬核验证光学去云算法的准确性。

---

## 📂 项目架构 

代码库采用了“主程序 + `core/` 核心工具箱”的结构，分为四大执行模块。所有数据流转均在 `data/` 目录中自动闭环。

```text
baikal-ice-phenology/
├── Cloud Removal/                 # [Step 1] 时空去云与影像重构模块
├── Phenology Extration/           # [Step 2] 宏观时间序列物候提取模块
├── Phenology Distribution Mapping/# [Step 3] 像素级空间物候制图模块
├── Validation & Assessment/       # [Step 4] 云量统计与 SAR 真值精度验证模块
└── data/                          # 统一的数据存放中心
    ├── 2024/                      # 原始 MOD/MYD 影像存放区 (按年份建文件夹)
    ├── range/                     # 湖泊边界 Shapefile 掩膜
    ├── ground_truth/              # Sentinel-1 SAR 真值数据集及 GEE 脚本
    └── result/                    # (程序自动生成) 去云影像、统计 CSV 与空间分布 TIF
🛠️ 环境配置
处理遥感影像，最头疼的就是 GDAL 和 PROJ 的底层环境冲突。强烈推荐使用 Conda 进行隔离配置：


# 1. 创建并激活虚拟环境
conda create -n ice_phenology python=3.9
conda activate ice_phenology

# 2. 安装核心地理空间库 (务必用 conda-forge 解决底层 C 库依赖)
conda install -c conda-forge gdal rasterio geopandas

# 3. 安装数据处理与可视化常规库
pip install pandas numpy scipy scikit-learn matplotlib seaborn
🚀 处理流程指南 (Processing Pipeline)
请按照以下 1~4 的顺序执行脚本，跑通完整工作流。

Step 0: 准备原始数据
进入 data/2024/ (或其他年份文件夹)，阅读里面的 readme.txt。

使用提供的 GEE 脚本下载对应年份的 MOD10A1 和 MYD10A1 影像，并直接放在该年份文件夹下。

确保 data/range/ 下有贝加尔湖的 Shapefile 掩膜文件。

Step 1: 时空去云处理 (Cloud Removal)
融合双星数据，并用时空平滑算法填补云层空缺。

Bash
cd "Cloud Removal"
python main.py
输出: 连续无云的每日 .tif 重构影像将自动存入 data/result/{Year}/。

Step 2: 时序物候提取 (Temporal Phenology Extraction)
提取全湖宏观的关键物候节点及持续时长 (ICD, CFD, FUD, BUD)，并生成平滑曲线。
(注：运行前请确保你已经统计出了每日覆盖率的 CSV 文件)

Bash
cd "../Phenology Extration"
python main.py
输出: 时序平滑曲线与物候节点散点图保存至 data/plots/。

Step 3: 空间物候制图 (Spatial Phenology Mapping)
生成每个像素的结冰 (FU) 与融冰 (BU) 绝对日期及多年均态分布图。

Bash
cd "../Phenology Distribution Mapping"
# 1. 生成历年 FU/BU 空间分布
python generate_annual_maps.py     
# 2. 生成多年平均空间格局
python calculate_average_maps.py   
输出: .tif 格式的地理空间产品保存至 data/result/spatial_products/。

Step 4: 精度评价与验证 (Validation & Assessment)
评估原始影像到底有多少云，并基于 Sentinel-1 真值生成混淆矩阵。

Bash
cd "../Validation & Assessment"
# 1. 评估原始光学数据的云覆盖率
python eval_cloud_fraction.py      
# 2. 将 GEE 导出的原始真值表合并，并转换至 EPSG:32648 坐标系
python project_ground_truth.py     
# 3. 计算混淆矩阵、总体精度(OA)与 Kappa 系数
python accuracy_assessment.py      
输出: 精度验证明细 CSV 与图表保存至 data/result/validation/ 与 data/plots/。

🌍 关于地面真值 (Ground Truth)
由于缺乏大范围的实地观测，我们在 Google Earth Engine (GEE) 开发了 Sentinel-1 SAR 交互式判读与均衡采样工具，用于人工获取绝对可靠的冰水真值。
关于这套 UI 工具的源码和操作指南，请参阅：
👉 Ground Truth Acquisition Guide

🤝 贡献与反馈
如果你在复现过程中遇到任何路径解析或环境配置的问题，欢迎提交 Issue。如果你觉得这个项目对你的遥感/地学研究有启发，不妨点个 ⭐️ Star！
