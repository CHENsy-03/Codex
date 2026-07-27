import pathlib, sys
DIR = pathlib.Path("E:/AI_Projects/Codex/离线小程序")
files = [
    # Python client requirements
    "ExamSystem/client/requirements.txt",
    # Python entry points
    "ExamSystem/client/main.py",
    "ExamSystem/client/parser.py",
    # Deprecated Python engine (kept for reference)
    "ExamSystem/tools/legacy_exam_engine.py",
    # Config files
    "ExamSystem/config/config.yaml",
    "README.md",
    # exam_core app modules
    "ExamSystem/client/app/exam_app.py",
    "ExamSystem/client/core/client.py",
    "ExamSystem/client/core/backend_manager.py",
    "ExamSystem/client/model/question.py",
    # exam_core parser modules
    "ExamSystem/client/parser/docx_parser.py",
    "ExamSystem/client/parser/answer_parser.py",
    # exam_core utility modules
    "ExamSystem/client/utils/config.py",
    "ExamSystem/client/utils/logger.py",
    "ExamSystem/client/utils/ui.py",
    # exam_core export module
    "ExamSystem/client/export/json_export.py",
    # go/ project - Go backend
    "ExamSystem/server/go.mod",
    "ExamSystem/server/go.sum",
    "ExamSystem/server/cmd/server/main.go",
    "ExamSystem/server/cmd/scoretest/main.go",
    "ExamSystem/server/internal/config/config.go",
    "ExamSystem/server/internal/logger/logger.go",
    "ExamSystem/server/model/question.go",
    "ExamSystem/server/internal/engine/engine.go",
    "ExamSystem/server/internal/storage/storage.go",
    "ExamSystem/server/internal/storage/question_loader.go",
    "ExamSystem/server/internal/engine/exam.go",
    "ExamSystem/server/internal/engine/session.go",
    "ExamSystem/server/internal/engine/session_manager.go",
    "ExamSystem/server/internal/api/handler.go",
    "ExamSystem/server/internal/api/server.go",
]
output = DIR / "全部代码.txt"
with open(output, "w", encoding="utf-8") as out:
    for fname in files:
        path = DIR / fname
        if not path.exists():
            print(f"WARNING: {fname} not found, skipping", file=sys.stderr)
            continue
        content = path.read_text(encoding="utf-8")
        out.write(f"{'='*60}\n")
        out.write(f"File: {fname}\n")
        out.write(f"{'='*60}\n\n")
        out.write(content)
        if not content.endswith("\n"):
            out.write("\n")
        out.write("\n")
print(f"Written: {output}")
print(f"Size: {output.stat().st_size} bytes")
included = [f for f in files if (DIR/f).exists()]
print(f"Files included ({len(included)}): {included}")
