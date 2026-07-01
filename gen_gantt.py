import re, os, sys
sys.path.insert(0, 'C:\\Users\\35594\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python')
from docx import Document
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np

font_path = 'C:\\Windows\\Fonts\\msyh.ttc'
font = FontProperties(fname=font_path, size=8)
font_title = FontProperties(fname=font_path, size=11)
font_small = FontProperties(fname=font_path, size=7)

out_dir = 'E:\\AI_Projects\\Codex\\output_images'
os.makedirs(out_dir, exist_ok=True)
source_dir = 'D:\\企业微信\\文件储存\\WXWork\\1688854658857559\\Cache\\File\\2026-07'

def parse_period(period_str):
    """Parse period string like '第1-10天' or '第1-2周' into (start, end) """
    period_str = period_str.strip()
    # Handle '第1-10天'
    m = re.search(r'第(\d+)[-~](\d+)(天|周)', period_str)
    if m:
        start = int(m.group(1))
        end = int(m.group(2))
        unit = m.group(3)
        if unit == '周':
            start *= 7
            end *= 7
        return (start, end)
    # Handle single value like '第1天' or '第1周'
    m = re.search(r'第(\d+)(天|周)', period_str)
    if m:
        val = int(m.group(1))
        unit = m.group(2)
        if unit == '周':
            val *= 7
        return (val-3, val+3)
    # Handle '第1-10天/2d/周' etc
    m = re.search(r'(\d+)[-~](\d+)', period_str)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # Handle '贯穿全期', '长期'
    if '贯穿' in period_str or '长期' in period_str:
        return None
    return None

def parse_gantt_blocks(cell_texts, time_labels):
    """Parse block character cells to determine task spans"""
    spans = {}
    n_periods = len(time_labels)
    for j, time_label in enumerate(time_labels):
        if j < len(cell_texts):
            text = cell_texts[j]
            blocks = len([c for c in text if c in '█▉▊▋▌▍▎▏'])
            if blocks > 0:
                period_data = parse_period(time_label)
                if period_data:
                    spans[time_label] = period_data
    return spans

def generate_gantt_chart(gantt_data, title, filename):
    """Create a Gantt chart image.
    gantt_data: list of (task_name, [list_of_period_pairs_or_empty])
    Each period is (start, end) or None for no activity
    """
    if not gantt_data:
        print(f'  No data for {filename}')
        return None
    
    fig_height = max(2.5, len(gantt_data) * 0.45 + 1.2)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    fig.patch.set_facecolor('white')
    ax.set_title(title, fontproperties=font_title, pad=10, fontweight='bold', color='#1a1a2e')
    ax.set_facecolor('#FAFBFC')
    
    colors = ['#1976D2', '#388E3C', '#F57C00', '#D32F2F', '#7B1FA2',
              '#0097A7', '#E64A19', '#455A64', '#5D4037', '#303F9F',
              '#00796B', '#C0CA33', '#689F38', '#FFA000', '#C2185B',
              '#512DA8', '#0288D1', '#00BCD4', '#43A047', '#FB8C00']
    
    y_positions = range(len(gantt_data))
    max_time = 0
    
    for i, (task_name, periods) in enumerate(gantt_data):
        bar_color = colors[i % len(colors)]
        for start, end in periods:
            if start is not None and end is not None:
                ax.barh(i, end - start, left=start, height=0.55,
                        color=bar_color, edgecolor='white', linewidth=0.5, alpha=0.85)
                if end > max_time:
                    max_time = end
    
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels([t[0] for t in gantt_data], fontproperties=font)
    ax.invert_yaxis()
    
    if max_time == 0:
        max_time = 100
    ax.set_xlim(0, max_time * 1.05)
    
    # Set x-tick labels from days to more meaningful labels
    if max_time <= 30:
        step = 5
    elif max_time <= 100:
        step = 10
    elif max_time <= 150:
        step = 20
    else:
        step = 30
    
    ticks = list(range(0, int(max_time) + step, step))
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) + '天' for t in ticks], fontproperties=font_small)
    
    ax.grid(axis='x', alpha=0.3, linestyle='--', color='#E0E0E0')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E0E0E0')
    ax.spines['bottom'].set_color('#E0E0E0')
    ax.tick_params(axis='x', labelsize=7)
    ax.tick_params(axis='y', labelsize=7)
    
    plt.tight_layout()
    filepath = os.path.join(out_dir, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'  Generated Gantt: {filename}')
    return filepath

counties = ['威信县', '永善县', '昭阳区']

for county in counties:
    print(f'\n=== {county} Gantt Charts ===')
    src_path = os.path.join(source_dir, f'昭通市{county}_低空经济_架构思维导图版_更新版.docx')
    doc = Document(src_path)
    
    # Find Gantt chart tables and generate images
    gantt_count = 0
    for i, table in enumerate(doc.tables):
        # Check if this table looks like a Gantt chart
        if len(table.rows) < 2 or len(table.columns) < 3:
            continue
        
        first_cell = table.rows[0].cells[0].text.strip()
        second_cell = table.rows[0].cells[1].text.strip() if len(table.rows[0].cells) > 1 else ''
        
        # Identify Gantt tables by looking for time period headers
        is_gantt = False
        time_labels = []
        for cell in table.rows[0].cells:
            text = cell.text.strip()
            if '第' in text and ('天' in text or '周' in text):
                is_gantt = True
                time_labels.append(text)
            elif '长期' in text:
                time_labels.append(text)
        
        if not is_gantt or len(time_labels) < 2:
            continue
        
        # Parse Gantt data
        gantt_data = []
        for j, row in enumerate(table.rows):
            if j == 0:
                continue  # Skip header
            cells = [cell.text.strip() for cell in row.cells]
            task_name = cells[0] if cells else ''
            if not task_name:
                continue
            
            periods = []
            for k, time_label in enumerate(time_labels):
                if k + 1 < len(cells):
                    cell_text = cells[k + 1]
                    # Check for blocks or day text
                    blocks = len([c for c in cell_text if c in '█▉▊▋▌▍▎▏'])
                    if blocks > 0:
                        period = parse_period(time_label)
                        if period:
                            periods.append(period)
                    elif '—' not in cell_text and cell_text.strip():
                        # Direct day text
                        period = parse_period(time_label)
                        if period:
                            periods.append(period)
            
            if periods:
                gantt_data.append((task_name, periods))
        
        if gantt_data:
            gantt_count += 1
            title = f'{county} - 第{gantt_count}阶段实施甘特图'
            filename = f'{county}_gantt_{gantt_count}.png'
            generate_gantt_chart(gantt_data, title, filename)
    
    if gantt_count == 0:
        print('  No Gantt tables found')

print('\n=== Gantt Chart Generation Complete ===')
