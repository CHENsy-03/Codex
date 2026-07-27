import os
target = r'E:\AI_Projects\Codex\workspace\crawler\protocol\messages.py'
lines = []
lines.append('from dataclasses import asdict, dataclass')
lines.append('from typing import Any, Literal')
lines.append('')
lines.append('PROTOCOL_VERSION = "1.0"')
lines.append('')
lines.append('')
lines.append('@dataclass(frozen=True, kw_only=True)')
lines.append('class MessageEnvelope:')
lines.append('    task_id: str')
lines.append('    message_id: str')
lines.append('    timestamp: str')
lines.append('    protocol_version: str = PROTOCOL_VERSION')
lines.append('')
lines.append('    def to_dict(self) -> dict[str, Any]:')
lines.append('        return asdict(self)')
lines.append('')
lines.append('')
CLASSES = [
    ('SearchMessage', 'search', [('site','str'),('keyword','str'),('level','int')]),
    ('URLMessage', 'url', [('url','str'),('site','str'),('keyword','str'),('level','int')]),
    ('HTMLMessage', 'html', [('url','str'),('site','str'),('keyword','str'),('level','int'),('title','str'),('html','str')]),
    ('ResultMessage', 'result', [('url','str'),('title','str'),('publish_date','str'),('content','str'),('score','int')]),
    ('ErrorMessage', 'error', [('stage','str'),('url','str'),('error_code','str'),('error','str'),('retryable','bool')]),
]
for name, mtype, fields in CLASSES:
    lines.append('')
    lines.append('')
    lines.append('@dataclass(frozen=True, kw_only=True)')
    lines.append(f'class {name}(MessageEnvelope):')
    lines.append(f'    type: Literal["{mtype}"] = "{mtype}"')
    for fname, ftype in fields:
        lines.append(f'    {fname}: {ftype}')
open(target, 'w', encoding='utf-8').write('\n'.join(lines))
sz = os.path.getsize(target)
print(f'Wrote {sz} bytes')
