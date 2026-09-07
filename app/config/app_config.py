from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config.config_loader import load_config


# 日志配置
@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


@dataclass
class Console:
    enable: bool
    level: str


@dataclass
class LoggingConfig:
    file: File
    console: Console


# 数据库配置
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int


@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str


@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    model_name: str
    api_key: str


@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig


config_file = Path(__file__).parents[2] / 'conf' / 'app_config.yaml'


@lru_cache(maxsize=1)
def load_app_config() -> AppConfig:
    """首次访问时加载 yaml 配置并缓存(lazy),避免 import 模块即有文件读取副作用"""
    return load_config(config_file=config_file, schema_cls=AppConfig)


def __getattr__(name: str):
    """模块属性 app_config 的延迟加载入口,兼容 from app.config.app_config import app_config"""
    if name == "app_config":
        return load_app_config()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == '__main__':
    print(load_app_config().db_meta.port)
