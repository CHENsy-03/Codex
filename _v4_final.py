
import py_compile, sys, os
sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.join(os.path.dirname(__file__), '无人机勘测服务器搭建', '服务器端')
files = [
  ("upgrade/base_parser.py","parser"),
  ("upgrade/eventbus.py","eventbus"),
  ("upgrade/plugin_sdk.py","plugin"),
  ("storage/sqlite_storage.py","sqlite"),
  ("v4_server.py","v4"),
]
for fp, n in files:
  try:
    src = os.path.join(BASE, fp)
    if not os.path.isfile(src):
      print(f"{n}: SKIP (file not found: {src})")
      continue
    py_compile.compile(src, doraise=True)
    print(f"{n}: OK")
  except py_compile.PyCompileError as e:
    print(f"{n}: COMPILE_ERROR - {str(e)[:100]}")
  except UnicodeEncodeError as e:
    print(f"{n}: ENCODING_ERROR - {str(e)[:80]}")
  except Exception as e:
    print(f"{n}: ERROR - {str(e)[:100]}")
