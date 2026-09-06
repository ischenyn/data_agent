from pathlib import Path
from typing import Type, TypeVar

from omegaconf import OmegaConf

T = TypeVar("T")


def load_config(config_file: Path, schema_cls: Type[T]) -> T:
    context = OmegaConf.load(config_file)
    schema = OmegaConf.structured(schema_cls)
    # Merge order matters: schema first (defines the structure/defaults),
    # then context (YAML values) so nested elements keep their dataclass types.
    config: T = OmegaConf.to_object(OmegaConf.merge(schema, context))
    return config
