import sys, os
sys.path.insert(0, 'C:\\Users\\35594\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np

font_path = 'C:\\Windows\\Fonts\\msyh.ttc'
font_title = FontProperties(fname=font_path, size=14)
font_node = FontProperties(fname=font_path, size=9)
font_sub = FontProperties(fname=font_path, size=7)

out_dir = 'E:\\AI_Projects\\Codex\\output_images'
os.makedirs(out_dir, exist_ok=True)

def create_mindmap(title, nodes, filename, width=10, height=7):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor('#FAFBFC')
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis('off')
    
    # Title
    ax.text(width/2, height-0.3, title, ha='center', va='center',
            fontproperties=font_title, fontweight='bold', color='#1a1a2e',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#2F5496', edgecolor='#1a3a6e', linewidth=2))
    
    # Use a tree layout
    colors = ['#1976D2', '#388E3C', '#F57C00', '#D32F2F', '#7B1FA2', '#0097A7', '#E64A19']
    
    # Root at center, arrange nodes in levels
    level_height = height / (max([len(v) for v in nodes.values()]) + 1)
    
    # Draw center to each main branch
    center_x = width / 2
    center_y = height - 1.0
    
    num_branches = len(nodes)
    for i, (branch_name, sub_nodes) in enumerate(nodes.items()):
        angle = np.pi * 0.8 + (np.pi * 0.4 * i / max(1, num_branches - 1))
        r = 2.0
        bx = center_x + r * np.cos(angle)
        by = center_y + r * np.sin(angle) * 0.5
        
        color = colors[i % len(colors)]
        
        # Draw line from center to branch
        ax.annotate('', xy=(bx, by), xytext=(center_x, center_y),
                    arrowprops=dict(arrowstyle='->', color=color, lw=2))
        
        # Branch node
        ax.text(bx, by, branch_name, ha='center', va='center',
                fontproperties=font_node, fontweight='bold', color='white',
                bbox=dict(boxstyle='round,pad=0.4', facecolor=color, edgecolor=color, linewidth=1))
        
        # Sub nodes
        for j, sub in enumerate(sub_nodes):
            sub_x = bx + 1.5 * np.cos(angle) * (0.5 + j * 0.3)
            sub_y = by + 1.2 * np.sin(angle) * (0.3 + j * 0.2)
            
            # Draw line to sub node
            ax.plot([bx, sub_x], [by, sub_y], '-', color=color, lw=1, alpha=0.5)
            
            ax.text(sub_x, sub_y, sub, ha='center', va='center',
                    fontproperties=font_sub, color='#333333',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=color, linewidth=0.5, alpha=0.9))
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, filename), dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'  Saved mindmap: {filename}')

# Generate 3 mind maps for each county
counties_mindmaps = {
    '威信县': [
        {
            'title': '威信县低空经济三层架构思维导图',
            'nodes': {
                '第一层：城市低空新基建底座': ['空域规划与划设', '数字底座绘制', '感知网络铺建', '通信网络建设', '气象设施部署'],
                '第二层：枢纽运营中心': ['五大功能中心', '指挥调度中心', '运维中心', '培训中心', '展示中心'],
                '第三层：县乡村三级服务网络': ['红色旅游观光', '特色农业服务', '矿区物资运输', '城市治理应急', '飞行器维保']
            },
            'fname': '威信县_mindmap_1_layer.png'
        },
        {
            'title': '威信县勘测组织架构思维导图',
            'nodes': {
                '总指挥中心': ['项目经理1名', '统筹协调调度'],
                '10个勘测片区': ['每区8人勘测队', '覆盖全县乡镇', '动态调度机制'],
                '技术支持组': ['GIS工程师', '数据分析师', '设备维护'],
                '后勤保障组': ['车辆调度', '物资供应', '住宿餐饮'],
                '质量控制组': ['数据质检', '进度监控', '安全监督']
            },
            'fname': '威信县_mindmap_2_org.png'
        },
        {
            'title': '威信县低空运行管理云平台架构',
            'nodes': {
                '数据底座层': ['三维地图数据', '设备点位数据', '气象数据融合', '统一数据接口'],
                '业务应用层': ['低空智能网联', '航线审批管理', '实时飞行监控', '数字孪生系统'],
                '空管保障层': ['空域管理', '流量监控', '冲突解算', '安全审计'],
                '配套服务层': ['用户管理', '计费系统', '数据分析', '报告生成']
            },
            'fname': '威信县_mindmap_3_platform.png'
        }
    ],
    '永善县': [
        {
            'title': '永善县低空经济三层架构思维导图',
            'nodes': {
                '第一层：城市低空新基建底座': ['空域规划与划设', '三维数字底座', '感知网络铺建', '通信网络建设'],
                '第二层：枢纽运营中心': ['运营服务中心', '物流集散中心', '维修保障中心', '培训展示中心'],
                '第三层：县乡村三级服务网络': ['农业植保服务', '物流运输', '旅游观光', '城市治理']
            },
            'fname': '永善县_mindmap_1_layer.png'
        },
        {
            'title': '永善县勘测组织架构思维导图',
            'nodes': {
                '总指挥部': ['项目经理', '技术总监', '安全监督'],
                '16个勘测片区': ['每区6-7人', '动态增援机制', '三阶段突击策略'],
                '后勤技术组': ['设备保障', '数据管理', '技术支撑'],
                '质量控制组': ['质检专员', '进度跟踪', '安全巡查']
            },
            'fname': '永善县_mindmap_2_org.png'
        },
        {
            'title': '永善县低空运行管理云平台架构',
            'nodes': {
                '数据底座层': ['三维地图导入', '设备数据接入', '气象数据融合', '标准化处理'],
                '核心业务层': ['身份识别', '航线审批', '冲突解算', '实时监控', '数字孪生'],
                '空管保障层': ['气象接入', '雷达接入', '5G-A感知', '告警联动'],
                '业务支撑层': ['物流调度', '植保管理', '旅游服务', '应急指挥']
            },
            'fname': '永善县_mindmap_3_platform.png'
        }
    ],
    '昭阳区': [
        {
            'title': '昭阳区低空经济三层架构思维导图',
            'nodes': {
                '第一层：城市低空新基建底座': ['空域规划与划设', '数字底座绘制', '5G-A通信网络', '雷达感知网络'],
                '第二层：枢纽运营中心': ['运营服务中心', '物流集散中心', '维保中心', '数据中心'],
                '第三层：县乡村三级服务网络': ['即时物流', '城市治理', '载人观光', '飞行器维保']
            },
            'fname': '昭阳区_mindmap_1_layer.png'
        },
        {
            'title': '昭阳区勘测组织架构思维导图',
            'nodes': {
                '指挥中心': ['项目总监', '技术主管', '安全监督'],
                '20个勘测片区': ['每区10人', '覆盖全区乡镇', '动态调度'],
                '技术支撑组': ['GIS分析', '数据处理', '设备维护'],
                '后勤保障组': ['车辆调度', '物资供应', '应急保障'],
                '质量监督组': ['数据验收', '进度管控', '安全巡查']
            },
            'fname': '昭阳区_mindmap_2_org.png'
        },
        {
            'title': '昭阳区低空运行管理云平台架构',
            'nodes': {
                '数据底座层': ['三维地图数据', '设备数据接入', '气象数据融合', '标准化接口'],
                '核心业务层': ['身份识别', '航线审批', '冲突解算', '实时监控', '数字孪生'],
                '空管保障层': ['态势感知', '告警联动', '应急响应', '安全审计'],
                '场景应用层': ['物流调度', '城市治理', '载人观光', '维保管理']
            },
            'fname': '昭阳区_mindmap_3_platform.png'
        }
    ]
}

for county, maps in counties_mindmaps.items():
    print(f'\n=== Generating mind maps for {county} ===')
    for mm in maps:
        create_mindmap(mm['title'], mm['nodes'], mm['fname'])

print('\n=== Mindmap generation complete! ===')
