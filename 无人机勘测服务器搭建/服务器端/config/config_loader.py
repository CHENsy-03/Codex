"""配置加载器：从 YAML 读取并验证服务器配置"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DatabaseConfig:
    path: str = "data/gnss_data.duckdb"
    memory_limit: str = "4GB"
    temp_directory: str = "data/temp"


@dataclass
class NetworkConfig:
    priority: List[str] = field(default_factory=lambda: ["5g", "4g", "wifi"])
    heartbeat_interval: int = 30
    session_timeout: int = 120


@dataclass
class ProtocolConfig:
    supported: List[str] = field(default_factory=lambda: ["GPGGA", "BESTPOS"])
    version: str = "2.0"
    crc_enabled: bool = True
    encrypt: bool = False


@dataclass
class SyncConfig:
    upstream_id: str = ""
    sync_interval: int = 60
    batch_size: int = 1000
    retry_max: int = 3


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "data/server.log"
    max_size_mb: int = 100
    backup_count: int = 5


@dataclass
class ServerConfig:
    id: str = "DEFAULT-001"
    name: str = "未命名服务器"
    level: str = "county"       # county / city / province / center
    host: str = "0.0.0.0"
    port: int = 9000
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


class ConfigLoader:
    """YAML 配置加载与验证"""

    @staticmethod
    def load(config_path: str = "config/server.yaml") -> ServerConfig:
        if not os.path.exists(config_path):
            print(f"[WARN] 配置文件不存在: {config_path}, 使用默认配置")
            return ServerConfig()

        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        return ConfigLoader._parse(raw)

    @staticmethod
    def _parse(raw: dict) -> ServerConfig:
        srv = raw.get("server", {})
        db_raw = raw.get("database", {})
        net = raw.get("network", {})
        prot = raw.get("protocol", {})
        sync_raw = raw.get("sync", {})
        log_raw = raw.get("logging", {})

        return ServerConfig(
            id=srv.get("id", "DEFAULT-001"),
            name=srv.get("name", "未命名服务器"),
            level=srv.get("level", "county"),
            host=srv.get("host", "0.0.0.0"),
            port=srv.get("port", 9000),
            database=DatabaseConfig(
                path=db_raw.get("path", "data/gnss_data.duckdb"),
                memory_limit=str(db_raw.get("memory_limit", "4GB")),
                temp_directory=db_raw.get("temp_directory", "data/temp"),
            ),
            network=NetworkConfig(
                priority=net.get("priority", ["5g", "4g", "wifi"]),
                heartbeat_interval=net.get("heartbeat_interval", 30),
                session_timeout=net.get("session_timeout", 120),
            ),
            protocol=ProtocolConfig(
                supported=prot.get("supported", ["GPGGA", "BESTPOS"]),
                version=str(prot.get("version", "2.0")),
                crc_enabled=prot.get("crc_enabled", True),
                encrypt=prot.get("encrypt", False),
            ),
            sync=SyncConfig(
                upstream_id=sync_raw.get("upstream_id", ""),
                sync_interval=sync_raw.get("sync_interval", 60),
                batch_size=sync_raw.get("batch_size", 1000),
                retry_max=sync_raw.get("retry_max", 3),
            ),
            logging=LoggingConfig(
                level=log_raw.get("level", "INFO"),
                file=log_raw.get("file", "data/server.log"),
                max_size_mb=log_raw.get("max_size_mb", 100),
                backup_count=log_raw.get("backup_count", 5),
            ),
        )
