from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config.config_loader import load_config


@dataclass
class ColumnConfig:
    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool


@dataclass
class TableConfig:
    name: str
    role: str
    description: str
    columns: list[ColumnConfig]


@dataclass
class MetricConfig:
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


@dataclass
class MetaConfig:
    tables: list[TableConfig]
    metrics: list[MetricConfig]


config_file = Path(__file__).parents[2] / 'conf' / 'meta_config.yaml'


@lru_cache(maxsize=1)
def load_meta_config() -> MetaConfig:
    """首次访问时加载 yaml 配置并缓存(lazy),避免 import 模块即有文件读取副作用"""
    return load_config(config_file=config_file, schema_cls=MetaConfig)


def __getattr__(name: str):
    """模块属性 meta_config 的延迟加载入口,兼容 from app.config.meta_config import meta_config"""
    if name == "meta_config":
        return load_meta_config()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == '__main__':
    print(load_meta_config().metrics[0].name)
