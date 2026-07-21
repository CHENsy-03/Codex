# -*- coding: utf-8 -*-
"""V2.0 Init Config - first-run configuration wizard for temp directory."""
import os, pathlib, yaml
from typing import Optional
def is_first_run(config_path: str = "config/server.yaml") -> bool:
    c = pathlib.Path(config_path)
    if not c.exists():
        return True
    try:
        with open(c, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        db = data.get("database", {})
        tmp = db.get("temp_directory", "")
        if tmp:
            p = pathlib.Path(tmp)
            if p.exists():
                return False
        return True
    except Exception:
        return True
def run_wizard(config_path: str = "config/server.yaml") -> Optional[str]:
    print()
    print("=" * 55)
    print("  首次配置向导 - 临时目录设置")
    print("=" * 55)
    print("  DuckDB 需要 LinShi(临时)目录用于大查询溢写。")
    print("  请选择或输入路径 (留空使用默认 data/temp):")
    print()
    default = os.path.abspath("data/temp")
    suggestions = [
        (default, "默认路径"),
        (os.path.abspath("D:/uav_temp"), "D:/uav_temp"),
        (os.path.abspath("E:/uav_temp"), "E:/uav_temp"),
    ]
    for i, (path, label) in enumerate(suggestions, 1):
        mark = "(建议)" if i == 1 else ""
        print(f"  {i}. {path} {mark}")
    print(f"  0. 手动输入")
    choice = input("\n请选择: ").strip()
    selected = None
    if choice == "0":
        selected = input("请输入 LinShi 目录路径: ").strip()
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                selected = suggestions[idx][0]
        except ValueError:
            pass
    if not selected:
        selected = default
        print(f"  使用默认路径: {selected}")
    sel_path = pathlib.Path(selected)
    try:
        sel_path.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] 目录已创建: {sel_path}")
    except Exception as ex:
        print(f"  [FAIL] 创建目录失败: {ex}")
        return None
    c = pathlib.Path(config_path)
    if c.exists():
        with open(c, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = {"server": {"id": "DEFAULT-001", "name": "default", "level": "county"},
                "database": {"path": "data/gnss_data.duckdb", "memory_limit": "4GB"}}
    data.setdefault("database", {})["temp_directory"] = str(sel_path)
    threshold = input("设置大文件直接扫描阈值(GB, 默认1.0): ").strip()
    try:
        data["database"]["scanner_threshold_gb"] = float(threshold) if threshold else 1.0
    except ValueError:
        data["database"]["scanner_threshold_gb"] = 1.0
    with open(c, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    print(f"  [OK] 配置已保存到 {config_path}")
    return str(sel_path)
