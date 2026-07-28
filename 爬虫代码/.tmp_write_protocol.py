import os
code = r'''from dataclasses import asdict, dataclass
from typing import Any, Literal
PROTOCOL_VERSION = "1.0"
@dataclass(frozen=True, kw_only=True)
class MessageEnvelope:
    task_id: str
    message_id: str
    timestamp: str
    protocol_version: str = PROTOCOL_VERSION
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
@dataclass(frozen=True, kw_only=True)
class SearchMessage(MessageEnvelope):
    type: Literal["search"] = "search"
    site: str; keyword: str; level: int
@dataclass(frozen=True, kw_only=True)
class URLMessage(MessageEnvelope):
    type: Literal["url"] = "url"
    url: str; site: str; keyword: str; level: int
@dataclass(frozen=True, kw_only=True)
class HTMLMessage(MessageEnvelope):
    type: Literal["html"] = "html"
    url: str; site: str; keyword: str; level: int; title: str; html: str
@dataclass(frozen=True, kw_only=True)
class ResultMessage(MessageEnvelope):
    type: Literal["result"] = "result"
    url: str; title: str; publish_date: str; content: str; score: int
@dataclass(frozen=True, kw_only=True)
class ErrorMessage(MessageEnvelope):
    type: Literal["error"] = "error"
    stage: str; url: str; error_code: str; error: str; retryable: bool
'''
target = r'E:\AI_Projects\Codex\workspace\crawler\protocol\messages.py'
with open(target, 'w', encoding='utf-8') as f:
    # Format the code with proper newlines
    formatted = code.replace(';', '\n    ')
    f.write(formatted)
print('Written:', os.path.getsize(target), 'bytes')
