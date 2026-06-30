"""V4 协议解析器基类 — 统一所有解析器接口"""
import abc

class BaseParser(abc.ABC):
    @property
    @abc.abstractmethod
    def protocol_name(self) -> str: ...

    @abc.abstractmethod
    def can_parse(self, data: str) -> bool: ...

    @abc.abstractmethod
    def parse(self, data: str) -> dict | None: ...

    def validate(self, parsed: dict) -> bool:
        return bool(parsed and "lat" in parsed and "lng" in parsed)


class ParserRegistry:
    _parsers: dict[str, BaseParser] = {}

    @classmethod
    def register(cls, parser: BaseParser):
        cls._parsers[parser.protocol_name] = parser

    @classmethod
    def detect(cls, data: str) -> BaseParser | None:
        for p in cls._parsers.values():
            if p.can_parse(data): return p
        return None

    @classmethod
    def parse(cls, data: str) -> dict | None:
        parser = cls.detect(data)
        return parser.parse(data) if parser else None

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._parsers.keys())
