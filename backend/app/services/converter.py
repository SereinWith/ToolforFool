"""繁简转换服务。

基于 opencc-python-reimplemented，支持繁体转简体（t2s）与简体转繁体（s2t）。
"""
from __future__ import annotations

from functools import lru_cache

from opencc import OpenCC


@lru_cache(maxsize=4)
def _get_converter(config: str) -> OpenCC:
    """缓存 OpenCC 实例，避免重复加载词典。"""
    return OpenCC(config)


def to_simplified(text: str) -> str:
    """繁体转简体。"""
    if not text:
        return text
    return _get_converter("t2s").convert(text)


def to_traditional(text: str) -> str:
    """简体转繁体。"""
    if not text:
        return text
    return _get_converter("s2t").convert(text)
