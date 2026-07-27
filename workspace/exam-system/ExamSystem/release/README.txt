考试系统 v1.0.0
===============

使用方法：
  双击 考试系统.exe 启动

目录结构：
  backend/ExamSystem.exe  后端引擎（自动启动）
  config/config.yaml      配置文件
  data/questions/         题库文件目录
  data/sessions/          考试会话（运行时生成）
  logs/                   日志（运行时生成）

配置选项（config/config.yaml）:
  server.port             端口号（默认 8080）
  server.token            API 鉴权令牌
  exam.show_answer_after_submit  交卷后是否显示正确答案

技术支持：
  如需重新打包，请运行 tools/build_all.bat
