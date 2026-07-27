"""V4-Local 结果服务模块 — 工业测试裁决引擎

文档依据: 4.docx (V4-Local 工业级系统升级方案-结果输出接口增强版)

模块结构:
  schema.py          ResultRecord 标准数据结构
  result_engine.py   结果计算引擎 (1/0/-1)
  result_store.py    结果持久化存储
  result_api.py      HTTP REST 查询接口
"""
from .schema import ResultRecord
from .result_engine import ResultEngine
from .result_store import ResultStore
from .result_api import ResultAPI
