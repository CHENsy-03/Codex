ExamSystem 离线考试系统
========================
版本: 1.0 | 协议: JSON v1.0 | Go 引擎

架构总览
--------
  考试系统.exe         Python/Tkinter 桌面 GUI（显示题目、发送答案、显示成绩）
  ExamSystem.exe       Go 后端（抽题、计分、Session 管理、持久化）
  parser.exe           CLI 题库解析器（Word .docx → questions.json）

  数据流:
    Word 题库 → parser.exe → questions.json → ExamSystem.exe → 评分 API
                                                      ↑
   考试系统.exe ──POST /start──→ session_id ──POST /answer──→ 实时保存
              └──POST /submit?session_id=──→ 评分结果

目录结构
--------
  ExamSystem.exe          Go 评分服务（双击启动，自动加载 config/config.yaml）
  parser.exe              命令行解析器
  config/
    config.yaml           配置文件（端口、Token、数据路径）
  data/
    questions.json        题库数据
    sessions/             考试会话（JSON，自动创建）
  logs/                   日志输出
  backup/                 数据备份
  README.txt              本文件

使用步骤
--------
1. 转换 Word 题库为 JSON:
   parser.exe 题库.docx data/questions.json

2. 启动评分服务:
   ExamSystem.exe
   → 服务运行在 http://localhost:8080
   → API: GET /health, GET /questions, POST /start, POST /answer, POST /submit

3. 启动桌面端:
   考试系统.exe
   → 自动启动 ExamSystem.exe（如未运行）
   → 通过 Session API 实时保存答题进度
   → 交卷后显示成绩

配置文件 config/config.yaml
--------------------------
  server.port      服务端口（默认 8080）
  server.token     API 访问令牌（默认 Exam2026）
  data.path        题库文件路径（默认 data/questions.json）
  log.path         日志文件路径（默认 logs/app.log）

构建说明（如需从源码构建）
--------------------------
  # Go 后端
  cd go && go build -o ExamSystem.exe ./cmd/server

  # Python 解析器
  pip install pyinstaller python-docx
  pyinstaller --onefile --hidden-import docx parser.py

  # Python 桌面端
  pyinstaller --onefile --windowed --name 考试系统 main.py
