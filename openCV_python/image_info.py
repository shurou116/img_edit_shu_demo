"""读取图片基础信息：文件名、格式、宽高、颜色模式、文件大小。"""
from __future__ import annotations

from pathlib import Path

from image_io import (
    describe_mode,
    detect_format,
    human_size,
    load_image,
)


def get_image_info(path: str | Path) -> dict[str, str]:
    """返回整理好的信息字典。

    先调 load_image：它顺带完成了「文件不存在 / 不是有效图片」的校验，
    所以这里不用重复判断，也不会因为读不出图片而崩溃。
    """
    img = load_image(path)
    p = Path(path)

    # numpy 数组的形状是 (高, 宽[, 通道])，别把 width / height 写反
    height, width = img.shape[:2]

    return {
        "文件名": p.name,
        "图片格式": detect_format(p),
        "宽度": f"{width} 像素",
        "高度": f"{height} 像素",
        "颜色模式": describe_mode(img),
        "文件大小": human_size(p.stat().st_size),
    }


def format_info(info: dict[str, str]) -> str:
    """把字典排成好看的几行，供命令行直接打印。"""
    return "\n".join(
        [
            "========== 图片基础信息 ==========",
            f"文件名   : {info['文件名']}",
            f"图片格式 : {info['图片格式']}",
            f"宽度     : {info['宽度']}",
            f"高度     : {info['高度']}",
            f"颜色模式 : {info['颜色模式']}",
            f"文件大小 : {info['文件大小']}",
            "=================================",
        ]
    )
