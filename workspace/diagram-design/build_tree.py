import os
svg = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 620" style="background:#f8f9fc;font-family:sans-serif;">
<defs><filter id="sd"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.12"/></filter>
<linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a3a6b"/><stop offset="100%" stop-color="#2b5797"/></linearGradient>
<linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2b5797"/><stop offset="100%" stop-color="#3d7bd9"/></linearGradient>
</defs>
<rect width="900" height="560" fill="#f8f9fc" rx="12"/>
<rect x="0" y="0" width="900" height="46" fill="url(#g1)" rx="12"/><rect x="0" y="30" width="900" height="16" fill="url(#g1)"/>
<text x="450" y="30" text-anchor="middle" fill="#fff" font-size="17" font-weight="700">项目指挥体系组织架构树</text>
</svg>'''
path = r'E:\AI_Projects\Codex\思维导图、树形图、流程图设计\项目指挥体系组织架构树.svg'
with open(path, 'w', encoding='utf-8') as f: f.write(svg)
print('OK:', os.path.getsize(path))
import os

svg = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 620" style="background:#f8f9fc;font-family:sans-serif;">
  <defs>
    <filter id="sd"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.12"/></filter>
    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a3a6b"/><stop offset="100%" stop-color="#2b5797"/></linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2b5797"/><stop offset="100%" stop-color="#3d7bd9"/></linearGradient>
  </defs>

  <!-- Background -->
  <rect width="900" height="620" fill="#f8f9fc" rx="12"/>

  <!-- Title bar -->
  <rect x="0" y="0" width="900" height="46" fill="url(#g1)" rx="12"/>
  <rect x="0" y="30" width="900" height="16" fill="url(#g1)"/>
  <text x="450" y="30" text-anchor="middle" fill="#fff" font-size="17" font-weight="700">项目指挥体系 · 组织架构树</text>

  <!-- Level 0: 项目总指挥 -->
  <rect x="365" y="65" width="170" height="40" rx="20" fill="url(#g1)" filter="url(#sd)"/>
  <text x="450" y="90" text-anchor="middle" fill="#fff" font-size="14" font-weight="700">项目总指挥</text>

  <!-- Lines L0 to L1 -->
  <line x1="450" y1="105" x2="450" y2="120" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="130" y1="120" x2="770" y2="120" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="130" y1="120" x2="130" y2="135" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="770" y1="120" x2="770" y2="135" stroke="#7c8db5" stroke-width="1.5"/>

  <!-- Level 1: two nodes -->
  <rect x="60" y="135" width="140" height="36" rx="18" fill="url(#g2)" filter="url(#sd)"/>
  <text x="130" y="158" text-anchor="middle" fill="#fff" font-size="12" font-weight="600">技术总顾问</text>

  <rect x="380" y="135" width="140" height="36" rx="18" fill="url(#g2)" filter="url(#sd)"/>
  <text x="450" y="158" text-anchor="middle" fill="#fff" font-size="12" font-weight="600">技术负责人（项目总工）</text>

  <!-- Lines from 技术负责人 to L2 -->
  <line x1="450" y1="171" x2="450" y2="185" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="180" y1="185" x2="720" y2="185" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="180" y1="185" x2="180" y2="200" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="315" y1="185" x2="315" y2="200" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="450" y1="185" x2="450" y2="200" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="585" y1="185" x2="585" y2="200" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="720" y1="185" x2="720" y2="200" stroke="#7c8db5" stroke-width="1.5"/>

  <!-- Level 2: five professional leads -->
  <rect x="100" y="200" width="160" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="180" y="223" text-anchor="middle" fill="#1a3a6b" font-size="12" font-weight="600">建筑专业负责人</text>

  <rect x="235" y="200" width="160" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="315" y="223" text-anchor="middle" fill="#1a3a6b" font-size="12" font-weight="600">结构专业负责人</text>

  <rect x="370" y="200" width="160" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="450" y="217" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">电气与助航</text>
  <text x="450" y="231" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">灯光负责人</text>

  <rect x="505" y="200" width="160" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="585" y="223" text-anchor="middle" fill="#1a3a6b" font-size="12" font-weight="600">给排水/消防负责人</text>

  <rect x="640" y="200" width="160" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="720" y="217" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">空管/通信</text>
  <text x="720" y="231" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">导航负责人</text>

  <!-- "协同" label & dashed line -->
  <line x1="720" y1="236" x2="720" y2="270" stroke="#7c8db5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <rect x="700" y="275" width="40" height="22" rx="11" fill="#7c8db5" opacity="0.6"/>
  <text x="720" y="290" text-anchor="middle" fill="#fff" font-size="10" font-weight="600">协同</text>

  <!-- Lines from 协同 to L3 -->
  <line x1="720" y1="297" x2="720" y2="315" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="245" y1="315" x2="720" y2="315" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="245" y1="315" x2="245" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="400" y1="315" x2="400" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="560" y1="315" x2="560" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="720" y1="315" x2="720" y2="330" stroke="#7c8db5" stroke-width="1.5"/>

  <!-- Level 3: four collaborative teams -->
  <rect x="165" y="330" width="160" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="245" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">BIM与数字化中心</text>
  <text x="245" y="362" text-anchor="middle" fill="#6b7fa5" font-size="10">(协同)</text>

  <rect x="320" y="330" width="160" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="400" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">场道与土建</text>
  <text x="400" y="362" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">施工团队</text>

  <rect x="480" y="330" width="160" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="560" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">质量安全与</text>
  <text x="560" y="362" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">合规审查组</text>

  <rect x="640" y="330" width="160" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="720" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">资料副总工</text>
  <text x="720" y="362" text-anchor="middle" fill="#6b7fa5" font-size="10">(协同)</text>

  <!-- Legend -->
  <rect x="30" y="420" width="12" height="12" rx="2" fill="url(#g1)"/>
  <text x="48" y="431" fill="#4a5a7a" font-size="11">核心领导</text>
  <rect x="160" y="420" width="12" height="12" rx="2" fill="url(#g2)"/>
  <text x="178" y="431" fill="#4a5a7a" font-size="11">中层管理</text>
  <rect x="290" y="420" width="12" height="12" rx="2" fill="#eef3fc" stroke="#b0c4de" stroke-width="1"/>
  <text x="308" y="431" fill="#4a5a7a" font-size="11">专业负责人</text>
  <rect x="430" y="420" width="12" height="12" rx="2" fill="#dce5f2" stroke="#b0c4de" stroke-width="1"/>
  <text x="448" y="431" fill="#4a5a7a" font-size="11">执行团队</text>
  <line x1="560" y1="426" x2="590" y2="426" stroke="#7c8db5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <text x="598" y="431" fill="#4a5a7a" font-size="11">协同关系</text>

  <text x="450" y="610" text-anchor="middle" fill="#a0b0c8" font-size="10">项目指挥体系架构图</text>
</svg>'''

path = r'E:\AI_Projects\Codex\思维导图、树形图、流程图设计\项目指挥体系组织架构树.svg'
with open(path, 'w', encoding='utf-8') as f:
    f.write(svg)
print('Done:', os.path.getsize(path), 'bytes')
import os

svg = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 640" style="background:#f8f9fc;font-family:sans-serif;">
  <defs>
    <filter id="sd"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.12"/></filter>
    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a3a6b"/><stop offset="100%" stop-color="#2b5797"/></linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2b5797"/><stop offset="100%" stop-color="#3d7bd9"/></linearGradient>
  </defs>

  <!-- Background -->
  <rect width="880" height="640" fill="#f8f9fc" rx="12"/>

  <!-- Title bar -->
  <rect x="0" y="0" width="880" height="46" fill="url(#g1)" rx="12"/>
  <rect x="0" y="30" width="880" height="16" fill="url(#g1)"/>
  <text x="440" y="30" text-anchor="middle" fill="#fff" font-size="17" font-weight="700">项目指挥体系 · 组织架构树</text>

  <!-- Level 0: 项目总指挥 -->
  <rect x="355" y="65" width="170" height="40" rx="20" fill="url(#g1)" filter="url(#sd)"/>
  <text x="440" y="90" text-anchor="middle" fill="#fff" font-size="14" font-weight="700">项目总指挥</text>

  <!-- Lines L0 to L1 -->
  <line x1="440" y1="105" x2="440" y2="118" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="140" y1="118" x2="740" y2="118" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="140" y1="118" x2="140" y2="133" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="740" y1="118" x2="740" y2="133" stroke="#7c8db5" stroke-width="1.5"/>

  <!-- Level 1 -->
  <rect x="70" y="133" width="140" height="36" rx="18" fill="url(#g2)" filter="url(#sd)"/>
  <text x="140" y="156" text-anchor="middle" fill="#fff" font-size="12" font-weight="600">技术总顾问</text>
  <rect x="670" y="133" width="140" height="36" rx="18" fill="url(#g2)" filter="url(#sd)"/>
  <text x="740" y="156" text-anchor="middle" fill="#fff" font-size="12" font-weight="600">技术负责人（项目总工）</text>

  <!-- Lines L1 to L2 -->
  <line x1="740" y1="169" x2="740" y2="183" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="183" x2="740" y2="183" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="183" x2="170" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="286" y1="183" x2="286" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="402" y1="183" x2="402" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="518" y1="183" x2="518" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="634" y1="183" x2="634" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="740" y1="183" x2="740" y2="198" stroke="#7c8db5" stroke-width="1.5"/>

  <!-- Level 2: six professional leads -->
  <!-- 建筑 -->
  <rect x="105" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="170" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">建筑专业负责人</text>
  <!-- 结构 -->
  <rect x="221" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="286" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">结构专业负责人</text>
  <!-- 电气 -->
  <rect x="337" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="402" y="215" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">电气与助航灯光</text>
  <text x="402" y="229" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">负责人</text>
  <!-- 给排水 -->
  <rect x="453" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="518" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">给排水/消防负责人</text>
  <!-- 空管 -->
  <rect x="569" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="634" y="215" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">空管/通信导航</text>
  <text x="634" y="229" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">负责人</text>
  <!-- 机场工艺 -->
  <rect x="675" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="740" y="215" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">机场工艺与机位</text>
  <text x="740" y="229" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">设计负责人</text>

  <!-- "协同" label & dashed line -->
  <line x1="740" y1="234" x2="740" y2="270" stroke="#7c8db5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <rect x="718" y="276" width="44" height="22" rx="11" fill="#7c8db5" opacity="0.6"/>
  <text x="740" y="291" text-anchor="middle" fill="#fff" font-size="10" font-weight="600">协同</text>

  <!-- Lines L2 to L3 -->
  <line x1="740" y1="298" x2="740" y2="315" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="315" x2="740" y2="315" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="315" x2="170" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="340" y1="315" x2="340" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="510" y1="315" x2="510" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="680" y1="315" x2="680" y2="330" stroke="#7c8db5" stroke-width="1.5"/>

  <!-- Level 3: four collaborative teams -->
  <!-- BIM （含3D建模） -->
  <rect x="80" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="170" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">BIM与数字化中心</text>
  <text x="170" y="362" text-anchor="middle" fill="#1a3a6b" font-size="10">（含3D建模渲染工程师）</text>

  <!-- 场道 -->
  <rect x="250" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="340" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">场道与土建</text>
  <text x="340" y="362" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">施工团队</text>

  <!-- 质量安全 -->
  <rect x="420" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="510" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">质量安全与</text>
  <text x="510" y="362" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">合规审查组</text>

  <!-- 资料副总工 -->
  <rect x="590" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="680" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">资料副总工</text>
  <text x="680" y="362" text-anchor="middle" fill="#6b7fa5" font-size="10">(协同)</text>

  <!-- Legend -->
  <rect x="30" y="420" width="12" height="12" rx="2" fill="url(#g1)"/>
  <text x="48" y="431" fill="#4a5a7a" font-size="11">核心领导</text>
  <rect x="155" y="420" width="12" height="12" rx="2" fill="url(#g2)"/>
  <text x="173" y="431" fill="#4a5a7a" font-size="11">中层管理</text>
  <rect x="280" y="420" width="12" height="12" rx="2" fill="#eef3fc" stroke="#b0c4de" stroke-width="1"/>
  <text x="298" y="431" fill="#4a5a7a" font-size="11">专业负责人</text>
  <rect x="415" y="420" width="12" height="12" rx="2" fill="#dce5f2" stroke="#b0c4de" stroke-width="1"/>
  <text x="433" y="431" fill="#4a5a7a" font-size="11">执行团队</text>
  <line x1="535" y1="426" x2="565" y2="426" stroke="#7c8db5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <text x="573" y="431" fill="#4a5a7a" font-size="11">协同关系</text>
  <text x="698" y="431" fill="#4a5a7a" font-size="11">协同关系</text>

  <rect x="415" y="420" width="12" height="12" rx="2" fill="#dce5f2" stroke="#b0c4de" stroke-width="1"/>
  <text x="433" y="431" fill="#4a5a7a" font-size="11">执行团队</text>
  <line x1="535" y1="426" x2="565" y2="426" stroke="#7c8db5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <text x="573" y="431" fill="#4a5a7a" font-size="11">协同关系</text>

  <text x="440" y="630" text-anchor="middle" fill="#a0b0c8" font-size="10">项目指挥体系架构图（更新版）</text>
</svg>'''

path = r'E:\AI_Projects\Codex\思维导图、树形图、流程图设计\项目指挥体系组织架构树.svg'
with open(path, 'w', encoding='utf-8') as f:
    f.write(svg)
print('Done:', os.path.getsize(path), 'bytes')
import os

svg = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 600" style="background:#f8f9fc;font-family:sans-serif;">
  <defs>
    <filter id="sd"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.12"/></filter>
    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a3a6b"/><stop offset="100%" stop-color="#2b5797"/></linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2b5797"/><stop offset="100%" stop-color="#3d7bd9"/></linearGradient>
  </defs>
  <rect width="880" height="600" fill="#f8f9fc" rx="12"/>
  <rect x="0" y="0" width="880" height="46" fill="url(#g1)" rx="12"/><rect x="0" y="30" width="880" height="16" fill="url(#g1)"/>
  <text x="440" y="30" text-anchor="middle" fill="#fff" font-size="17" font-weight="700">项目指挥体系 · 组织架构树</text>
  <rect x="355" y="65" width="170" height="40" rx="20" fill="url(#g1)" filter="url(#sd)"/>
  <text x="440" y="90" text-anchor="middle" fill="#fff" font-size="14" font-weight="700">项目总指挥</text>
  <line x1="440" y1="105" x2="440" y2="118" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="140" y1="118" x2="740" y2="118" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="140" y1="118" x2="140" y2="133" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="740" y1="118" x2="740" y2="133" stroke="#7c8db5" stroke-width="1.5"/>
  <rect x="70" y="133" width="140" height="36" rx="18" fill="url(#g2)" filter="url(#sd)"/>
  <text x="140" y="156" text-anchor="middle" fill="#fff" font-size="12" font-weight="600">技术总顾问</text>
  <rect x="670" y="133" width="140" height="36" rx="18" fill="url(#g2)" filter="url(#sd)"/>
  <text x="740" y="156" text-anchor="middle" fill="#fff" font-size="12" font-weight="600">技术负责人（项目总工）</text>
  <line x1="740" y1="169" x2="740" y2="183" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="183" x2="740" y2="183" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="183" x2="170" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="286" y1="183" x2="286" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="402" y1="183" x2="402" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="518" y1="183" x2="518" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="634" y1="183" x2="634" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="740" y1="183" x2="740" y2="198" stroke="#7c8db5" stroke-width="1.5"/>
  <rect x="105" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="170" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">建筑专业负责人</text>
  <rect x="221" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="286" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">结构专业负责人</text>
  <rect x="337" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="402" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">电气与助航灯光负责人</text>
  <rect x="453" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="518" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">给排水/消防负责人</text>
  <rect x="569" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="634" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">空管/通信导航负责人</text>
  <rect x="675" y="198" width="130" height="36" rx="18" fill="#eef3fc" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="740" y="221" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">机场工艺与机位设计负责人</text>
  <line x1="740" y1="234" x2="740" y2="270" stroke="#7c8db5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <rect x="718" y="276" width="44" height="22" rx="11" fill="#7c8db5" opacity="0.6"/>
  <text x="740" y="291" text-anchor="middle" fill="#fff" font-size="10" font-weight="600">协同</text>
  <line x1="740" y1="298" x2="740" y2="315" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="315" x2="740" y2="315" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="170" y1="315" x2="170" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="340" y1="315" x2="340" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="510" y1="315" x2="510" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <line x1="680" y1="315" x2="680" y2="330" stroke="#7c8db5" stroke-width="1.5"/>
  <rect x="80" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="170" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">BIM与数字化中心</text>
  <text x="170" y="362" text-anchor="middle" fill="#1a3a6b" font-size="10">（含3D建模渲染工程师）</text>
  <rect x="250" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="340" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">场道与土建施工团队</text>
  <rect x="420" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="510" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">质量安全与合规审查组</text>
  <rect x="590" y="330" width="180" height="36" rx="18" fill="#dce5f2" stroke="#b0c4de" stroke-width="1.2"/>
  <text x="680" y="347" text-anchor="middle" fill="#1a3a6b" font-size="11" font-weight="600">资料副总工</text>
  <text x="680" y="362" text-anchor="middle" fill="#6b7fa5" font-size="10">(协同)</text>
  <rect x="30" y="420" width="12" height="12" rx="2" fill="url(#g1)"/>
  <text x="48" y="431" fill="#4a5a7a" font-size="11">核心领导</text>
  <rect x="155" y="420" width="12" height="12" rx="2" fill="url(#g2)"/>
  <text x="173" y="431" fill="#4a5a7a" font-size="11">中层管理</text>
  <rect x="280" y="420" width="12" height="12" rx="2" fill="#eef3fc" stroke="#b0c4de" stroke-width="1"/>
  <text x="298" y="431" fill="#4a5a7a" font-size="11">专业负责人</text>
  <rect x="415" y="420" width="12" height="12" rx="2" fill="#dce5f2" stroke="#b0c4de" stroke-width="1"/>
  <text x="433" y="431" fill="#4a5a7a" font-size="11">执行团队</text>
  <line x1="535" y1="426" x2="565" y2="426" stroke="#7c8db5" stroke-width="1.5" stroke-dasharray="4,3"/>
  <text x="573" y="431" fill="#4a5a7a" font-size="11">协同关系</text>
  <text x="440" y="590" text-anchor="middle" fill="#a0b0c8" font-size="10">项目指挥体系架构图</text>
</svg>'''

path = r'E:\AI_Projects\Codex\思维导图、树形图、流程图设计\项目指挥体系组织架构树.svg'
with open(path, 'w', encoding='utf-8') as f:
    f.write(svg)
print('Done:', os.path.getsize(path), 'bytes')
