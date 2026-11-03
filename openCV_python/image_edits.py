"""6 种简单图片编辑。

统一约定：每个函数都是「接收 numpy 数组 -> 返回新数组」，
不读文件、不写文件、也不修改传进来的原数组。存文件交给 image_io，
命令行交给 image_tool，这样每层都好单独测试和复用。
"""
from __future__ import annotations

import cv2
import numpy as np

from image_io import ImageToolError, flatten_alpha


def resize_image(
    img: np.ndarray, width: int | None = None, height: int | None = None
) -> np.ndarray:
    """缩放：可只给宽或高（另一个按比例算），也可两个都给。

    OpenCV 的 cv2.resize 第二个参数是 (宽, 高)，和数组 shape 的
    (高, 宽) 顺序相反，这里是最容易写反的地方。
    """
    if width is None and height is None:
        raise ImageToolError("缩放至少要指定 --width 或 --height 之一")
    for name, value in (("宽度", width), ("高度", height)):
        if value is not None and value <= 0:
            raise ImageToolError(f"{name}必须是正整数，收到 {value}")

    h, w = img.shape[:2]
    if width is not None and height is not None:
        new_w, new_h = int(width), int(height)
    elif width is not None:
        new_w = int(width)
        new_h = max(1, round(h * new_w / w))     # 按原始宽高比折算
    else:
        new_h = int(height)
        new_w = max(1, round(w * new_h / h))

    # 缩小用 INTER_AREA（不容易出现摩尔纹），放大用 INTER_LINEAR
    interpolation = (
        cv2.INTER_AREA if (new_w < w or new_h < h) else cv2.INTER_LINEAR
    )
    return cv2.resize(img, (new_w, new_h), interpolation=interpolation)


def crop_image(
    img: np.ndarray, left: int, top: int, right: int, bottom: int
) -> np.ndarray:
    """裁剪：按 (左, 上, 右, 下) 坐标切一块，右/下为开区间。

    数组切片是 img[行, 列]，也就是 img[top:bottom, left:right]，
    千万别写成 img[left:right, top:bottom]。
    """
    h, w = img.shape[:2]
    for name, value in (
        ("left", left), ("top", top), ("right", right), ("bottom", bottom)
    ):
        if value < 0:
            raise ImageToolError(f"裁剪坐标 {name} 不能为负数（收到 {value}）")
    if right <= left or bottom <= top:
        raise ImageToolError(
            "裁剪区域无效：right 必须大于 left，bottom 必须大于 top"
        )
    if left >= w or top >= h:
        raise ImageToolError(
            f"裁剪起点 ({left}, {top}) 已落在图片 {w}x{h}（宽x高）之外"
        )
    if right > w or bottom > h:
        raise ImageToolError(
            f"裁剪区域越界：图片只有 {w}x{h}（宽x高），"
            f"你给的右下角是 ({right}, {bottom})"
        )
    return img[top:bottom, left:right].copy()   # copy 断开与原数组的共享内存


def rotate_image(img: np.ndarray, angle: int) -> np.ndarray:
    """旋转 90 / 180 / 270 度。

    用 cv2.rotate 而不是 cv2.warpAffine：前者是整数倍直角旋转，
    不产生黑边、不裁掉内容、也不涉及插值，像素无损。
    """
    mapping = {
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE,
    }
    if angle not in mapping:
        raise ImageToolError(f"旋转角度只支持 90 / 180 / 270 度，收到 {angle}")
    return cv2.rotate(img, mapping[angle])


def flip_image(img: np.ndarray, direction: str) -> np.ndarray:
    """翻转：h 水平 / v 垂直 / hv 两者。

    cv2.flip 的 flipCode：1=水平(左右镜像)，0=垂直(上下镜像)，-1=两者。
    """
    mapping = {
        "h": 1, "horizontal": 1,
        "v": 0, "vertical": 0,
        "hv": -1, "both": -1,
    }
    key = direction.lower()
    if key not in mapping:
        raise ImageToolError(
            f"翻转方向只支持 h(水平) / v(垂直) / hv(两者)，收到 {direction!r}"
        )
    return cv2.flip(img, mapping[key])


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """彩色转灰度。注意 BGRA 要走 COLOR_BGRA2GRAY，不能用 BGR2GRAY。"""
    if img.ndim == 2:
        return img.copy()                       # 本来就是灰度
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def convert_image(img: np.ndarray, target_ext: str) -> np.ndarray:
    """格式转换前的像素准备。

    JPEG 没有 alpha 通道，所以目标是 jpg/jpeg 时先用白底合成去掉透明；
    目标支持 alpha（png / webp / tiff 等）时原样保留。
    真正的编码在 save_image 里按输出文件后缀完成。
    """
    ext = target_ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    if ext in (".jpg", ".jpeg"):
        return flatten_alpha(img)
    return img.copy()
