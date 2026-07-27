import os
svg_path = r'E:\AI_Projects\Codex\思维导图、树形图、流程图设计\项目指挥体系组织架构树.svg'
t = open(svg_path, encoding='utf-8').read()

t = t.replace(
    '场道与土建施工团队</text>',
    '场道与土建施工团队</text>', 1)
t = t.replace(
    '<text x="340" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">场道与土建施工团队</text>',
    '<text x="340" y="353" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">场道与土建施工团队</text>')
t = t.replace(
    '<text x="510" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">质量安全与合规审查组</text>',
    '<text x="510" y="353" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">质量安全与合规审查组</text>')
t = t.replace(
    '<text x="170" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">BIM与数字化中心</text>\n  <text x="170" y="362" text-anchor="middle" fill="#1a3a6b" font-size="10">（含3D建模渲染工程师）</text>',
    '<text x="170" y="342" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">BIM与数字化中心</text>\n  <text x="170" y="358" text-anchor="middle" fill="#1a3a6b" font-size="10">（含3D建模渲染工程师）</text>')
t = t.replace(
    '<text x="680" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">资料副总工</text>\n  <text x="680" y="362" text-anchor="middle" fill="#6b7fa5" font-size="10">(协同)</text>',
    '<text x="680" y="342" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">资料副总工</text>\n  <text x="680" y="358" text-anchor="middle" fill="#6b7fa5" font-size="10">(协同)</text>')

open(svg_path, 'w', encoding='utf-8').write(t)
print('Done:', len(t.encode('utf-8')), 'bytes')
import os
svg_path = r'E:\AI_Projects\Codex\思维导图、树形图、流程图设计\项目指挥体系组织架构树.svg'
t = open(svg_path, encoding='utf-8').read()

# Shift Level 3 items +15px to center everything
t = t.replace('x="80" y="330" width="180"', 'x="95" y="330" width="180"')
t = t.replace('x="250" y="330" width="180"', 'x="265" y="330" width="180"')
t = t.replace('x="420" y="330" width="180"', 'x="435" y="330" width="180"')
t = t.replace('x="590" y="330" width="180"', 'x="605" y="330" width="180"')

# Update center positions for text (+15)
t = t.replace('x="170" y="342" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">BIM', 
              'x="185" y="342" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">BIM')
t = t.replace('x="170" y="358" text-anchor="middle" fill="#1a3a6b" font-size="10">', 
              'x="185" y="358" text-anchor="middle" fill="#1a3a6b" font-size="10">')
t = t.replace('x="340" y="353" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">场道', 
              'x="355" y="353" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">场道')
t = t.replace('x="510" y="353" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">质量', 
              'x="525" y="353" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">质量')
t = t.replace('x="680" y="342" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">资料', 
              'x="695" y="342" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">资料')
t = t.replace('x="680" y="358" text-anchor="middle" fill="#6b7fa5"', 
              'x="695" y="358" text-anchor="middle" fill="#6b7fa5"')

# Update the horizontal connecting line for Level 3
t = t.replace('x1="170" y1="315" x2="740" y2="315"', 'x1="185" y1="315" x2="740" y2="315"')

# Update vertical drop lines
t = t.replace('x1="170" y1="315" x2="170" y2="330"', 'x1="185" y1="315" x2="185" y2="330"')
t = t.replace('x1="340" y1="315" x2="340" y2="330"', 'x1="355" y1="315" x2="355" y2="330"')
t = t.replace('x1="510" y1="315" x2="510" y2="330"', 'x1="525" y1="315" x2="525" y2="330"')
t = t.replace('x1="680" y1="315" x2="680" y2="330"', 'x1="695" y1="315" x2="695" y2="330"')

open(svg_path, 'w', encoding='utf-8').write(t)
print('Updated SVG')
