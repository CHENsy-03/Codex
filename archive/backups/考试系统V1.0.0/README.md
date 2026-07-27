# 离线考试系统

一个基于 Python + Tkinter (GUI) + Go (后端引擎) 的桌面离线考试小程序，支持：
- 上传 Word（.docx）题库并自动解析选择题
- 可选单独的答案文件覆盖答案
- 自定义每题分值（默认 1 分）
- 在线作答，交卷后即时出分
- 查看逐题解析与正确答案

## 项目结构

```
ExamSystem/
│
├── python/                        # Python 前端
├── ExamSystem/client/                     # Python 前端源码
│   ├── main.py                    # 入口文件（自动启动 Go 后端）
│   ├── parser.py                  # CLI 解析器（docx → json）
│   ├── requirements.txt           # pip 依赖
│   ├── app/
│   │   └── exam_app.py            # Tkinter 桌面 GUI
│   ├── core/
│   │   ├── client.py              # HTTP 客户端
│   │   └── backend_manager.py     # 后端进程管理器
│   ├── model/
│   │   └── question.py            # 题目数据模型
│   ├── parser/
│   │   ├── docx_parser.py         # Word 解析器
│   │   └── answer_parser.py       # 答案文件解析器
│   ├── utils/
│   │   ├── config.py              # 全局常量
│   │   ├── logger.py              # 日志模块
│   │   └── ui.py                  # 鼠标滚轮绑定
│   └── export/
│       └── json_export.py         # JSON 导出
│
├── ExamSystem/server/                            # Go 后端引擎
│   ├── cmd/server/main.go         # HTTP 服务入口
│   ├── cmd/scoretest/main.go      # 评分测试
│   ├── internal/
│   │   ├── api/handler.go         # HTTP 路由
│   │   ├── api/server.go          # 服务器启动
│   │   ├── config/config.go       # 配置加载
│   │   ├── logger/logger.go       # 日志
│   │   ├── engine/                    # 引擎模块
│   │   │   ├── engine.go          # 题库管理
│   │   │   ├── exam.go            # 结果类型
│   │   │   ├── session.go         # 会话评分
│   │   │   └── session_manager.go # 会话持久化
│   │   └── storage/               # 存储模块
│   │       ├── storage.go
│   │       └── question_loader.go # 题库加载
│   ├── model/question.go          # 数据模型
│   ├── go.mod / go.sum
│
├── data/                          # 数据
│   ├── questions/                 # 题库文件（每科一个 .json）
│   │   ├── default.json           # 默认题库
│   │   ├── 综合.json               # 后续可添加多个题库
│   │   └── ...                    # 每文件一科，文件即科目
│   ├── sessions/                  # 考试会话持久化
│   └── backup/                    # 题库备份
│
├── logs/                          # 日志
│   ├── server.log                 # Go 服务端日志
│   ├── client.log                 # Python 客户端日志
│   └── error.log                  # 错误日志
│
├── config/                        # 配置
│   └── config.yaml                # 主配置文件
│   ├── combine_code.py            # 源码合并工具
├── 全部代码.txt
└── README.md
```

## 使用说明

### 1. 安装依赖

```bash
pip install -r ExamSystem/client/requirements.txt
```

### 2. 启动程序

```bash
python ExamSystem/client/main.py
```

程序自动启动 Go 后端（ExamSystem.exe），无需手动运行。

### 3. 考试流程

1. **导入页面**：选择 Word（.docx）题库文件，设置分值，点击"解析题库"
2. **预览**：表格显示所有题目，可双击修改每题分值
3. **开始考试**：逐题作答，支持上一题/下一题/提交
4. **交卷**：显示总分、得分率和逐题解析（分页浏览）

### 4. 题库格式要求

Word 文档每道题按以下格式：

```
1. 题目文字
A. 选项一
B. 选项二
C. 选项三
D. 选项四
答案：A
```

- 题号支持 `.` `、` `)` `）` 分隔
- 选项支持 `A.` `A)` `A）` `A、`
- 答案行支持 `答案：` `正确答案：` `【答案】` 
- 连续两个空行结束当前题目

### 5. 架构说明

```
main.py → backend_manager → 启动 Go 后端
       → ExamApp (Tkinter)
            ├─ ImportView  (导入/预览)
            ├─ ExamView    (逐题作答，分页缓存)
            └─ ResultView  (成绩解析)

通信: ExamView → client.py (HTTP) → Go API → Engine
```

### 6. 源代码整合

```bash
python ExamSystem/tools/combine_code.py
# 生成 全部代码.txt
```

## 模块架构

```
Python 架构：
main.py → BackendManager → ExamApp → ImportView / ExamView / ResultView
          ↕ HTTP (client.py)
Go 架构：
API (/health, /start, /answer, /submit, /questions) → Engine → SessionManager

数据流：
.docx → docx_parser → Question → JSON → questions.json → Go → API → Python
```

### 遗留模块

`legacy_exam_engine.py` 为旧版 Python 引擎，已被 Go 替代，保留作参考。

### 注意事项

- 首次运行需要 python-docx 依赖：`pip install -r ExamSystem/client/requirements.txt`
- Go 后端需要提前编译：`cd ExamSystem\server
go build -o ..\release\backend\ExamSystem.exe .\cmd\server\
go build -o ..\release\backend\ExamSystem.exe .\cmd\server\`
- 如需重新打包 exe：`pyinstaller --onefile --add-data "python;python" main.py`


## 发布包结构

为终端用户交付时使用 `ExamSystem/release/` 目录，用户只需双击 `考试系统.exe`。

```
ExamSystem/release/
│
├── 考试系统.exe            # 主界面入口（双击启动）
│
├── backend/
│   └── ExamSystem.exe      # Go 后端引擎（自动启动）
│
├── tools/
│   └── parser.exe          # 命令行题库解析器
│
├── config/
│   └── config.yaml         # 配置文件
│
├── data/
│   ├── questions/          # 题库文件（每科一个 .json）
│   │   └── default.json
│   ├── sessions/           # 考试会话持久化
│   └── backup/             # 题库备份
│
└── logs/                   # 运行日志
    ├── server.log
    ├── client.log
    └── error.log
```

`考试系统.exe` 会自动在 `backend/` 目录下寻找 `ExamSystem.exe` 并启动。\n