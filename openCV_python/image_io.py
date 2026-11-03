"""图片读写层：项目里只有这个文件直接和「文件 + OpenCV 编解码」打交道。

为什么单独拆一层？
  1. 其他模块只拿 numpy 数组，不必关心路径、编码格式这些细节；
  2. Windows 上 cv2.imread / cv2.imwrite 遇到中文路径会静默失败，
     这里用 imdecode / imencode 绕开，问题只解决一次就够了。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ImageToolError(Exception):
    """可预期的、要展示给使用者的错误（文件不存在、参数不合法等）。

    单独定义一种异常，命令行入口就能统一捕获、打印一句人话，
    而不是把一长串 traceback 甩给使用者。
    """


# imencode 能写出的扩展名，超出范围就明确报错
WRITABLE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def load_image(path: str | Path) -> np.ndarray:
    """读取图片，返回 OpenCV 的 numpy 数组（BGR / BGRA / 灰度）。

    IMREAD_UNCHANGED 是关键：默认的 cv2.imread 会丢掉 PNG 的透明通道、
    还会把灰度图强行读成 3 通道，那样「颜色模式」就判断不准了。
    """
    p = Path(path)
    if not p.exists():
        raise ImageToolError(f"文件不存在：{p}")
    if not p.is_file():
        raise ImageToolError(f"这不是一个文件：{p}")

    # np.fromfile 支持 Windows 中文路径，cv2.imread 不支持
    try:
        data = np.fromfile(str(p), dtype=np.uint8)
    except OSError as exc:
        raise ImageToolError(f"读取文件失败：{p}（{exc}）") from exc
    if data.size == 0:
        raise ImageToolError(f"文件是空的：{p}")

    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ImageToolError(f"不是有效的图片，或格式不受 OpenCV 支持：{p}")
    return img


def detect_format(path: str | Path) -> str:
    """用文件头「魔数」判断真实格式，比看扩展名可靠（扩展名可能是假的）。"""
    p = Path(path)
    try:
        with p.open("rb") as f:
            head = f.read(16)          # 只看前 16 字节，不整文件读进内存
    except OSError:
        return "未知格式"

    if head.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if head.startswith(b"BM"):
        return "BMP"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "TIFF"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "GIF"
    if len(head) >= 12 and head[8:12] == b"WEBP":
        return "WEBP"
    return "未知格式"


def describe_mode(img: np.ndarray) -> str:
    """从数组维度判断颜色模式 —— OpenCV 入门最容易踩的坑就在这里。

    OpenCV 读进来的形状是 (高, 宽, 通道)，且彩色顺序是 B-G-R，不是 R-G-B。
    """
    if img.ndim == 2:
        return "灰度（1 通道）"
    if img.ndim == 3:
        channels = img.shape[2]
        if channels == 3:
            return "BGR 彩色（3 通道，OpenCV 顺序为 B-G-R）"
        if channels == 4:
            return "BGRA 彩色 + 透明（4 通道）"
    return f"非常规数组（shape={img.shape}）"


def human_size(num_bytes: int) -> str:
    """文件大小：>= 1 MB 用 MB，否则用 KB，都保留 2 位小数。"""
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / 1024 / 1024:.2f} MB"
    return f"{num_bytes / 1024:.2f} KB"


def flatten_alpha(
    img: np.ndarray, background: tuple[int, int, int] = (255, 255, 255)
) -> np.ndarray:
    """把带 alpha 的图与纯色背景合成，输出 3 通道 BGR。

    JPEG 不支持透明通道，必须处理。直接 cvtColor(BGRA2BGR) 虽然能去掉
    第 4 通道，但透明像素原本的 BGR 往往是 0，会变成黑底。正确做法是按
    alpha 加权混合：结果 = 前景 * a + 背景 * (1 - a)，默认白底。
    """
    if img.ndim == 2:
        # 本来就是灰度图，保持 1 通道即可。不要转成 3 通道，
        # 否则灰度图存成 JPG 后会被识别成 BGR 彩色。
        return img.copy()
    if img.shape[2] == 3:
        return img.copy()
    if img.shape[2] != 4:
        raise ImageToolError(f"无法处理的通道数：{img.shape[2]}")

    fg = img[:, :, :3].astype(np.float32)
    a = img[:, :, 3:4].astype(np.float32) / 255.0
    bg = np.array(background, dtype=np.float32).reshape(1, 1, 3)
    blended = fg * a + bg * (1.0 - a)
    return np.clip(blended, 0, 255).astype(np.uint8)


def default_output_path(
    src: str | Path, tag: str, ext: str | None = None
) -> Path:
    """编辑结果统一放到原图同级的 output/ 目录，且绝不覆盖已有文件。"""
    src = Path(src)
    suffix = ext if ext is not None else src.suffix
    if suffix and not suffix.startswith("."):
        suffix = "." + suffix
    out_dir = src.parent / "output"
    candidate = out_dir / f"{src.stem}_{tag}{suffix}"
    n = 1
    while candidate.exists():          # 同名就加序号，原图和旧结果都不动
        candidate = out_dir / f"{src.stem}_{tag}_{n}{suffix}"
        n += 1
    return candidate


def save_image(
    img: np.ndarray, out_path: str | Path, jpeg_quality: int = 95
) -> Path:
    """把数组编码成图片文件；返回实际保存的绝对路径。"""
    out = Path(out_path)
    ext = out.suffix.lower()
    if not ext:
        raise ImageToolError(
            f"输出路径缺少扩展名，无法确定保存格式：{out}（例如写成 {out}.jpg）"
        )
    if ext not in WRITABLE_EXTS:
        raise ImageToolError(
            f"不支持的输出格式 {ext!r}，可用：{', '.join(sorted(WRITABLE_EXTS))}"
        )
    if not 0 <= jpeg_quality <= 100:
        raise ImageToolError("JPEG 质量必须是 0~100 之间的整数")

    if ext in (".jpg", ".jpeg"):
        img = flatten_alpha(img)      # 兜底：存 JPG 一律先去透明通道
        params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
    elif ext == ".png":
        params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
    else:
        params = []

    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        raise ImageToolError(f"编码失败，无法保存为 {ext}：{out}")

    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        buf.tofile(str(out))          # 同样是为了支持中文路径
    except OSError as exc:
        raise ImageToolError(f"写入文件失败：{out}（{exc}）") from exc
    return out
