"""命令行入口：只负责解析参数、调用各模块、打印结果或友好错误。

运行示例：
    python image_tool.py info samples/demo.jpg
    python image_tool.py resize samples/demo.jpg --width 160
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from image_edits import (
    convert_image,
    crop_image,
    flip_image,
    resize_image,
    rotate_image,
    to_grayscale,
)
from image_io import (
    ImageToolError,
    default_output_path,
    load_image,
    save_image,
)
from image_info import format_info, get_image_info

# --to 允许的格式，统一映射到带点的扩展名
TARGET_EXTS = {
    "jpg": ".jpg", "jpeg": ".jpeg", "png": ".png", "bmp": ".bmp",
    "webp": ".webp", "tif": ".tif", "tiff": ".tiff",
}


def normalize_target(value: str) -> str:
    """把 --to 的值规整成 '.jpg' 这样的扩展名，非法值给出明确提示。"""
    key = value.lower().lstrip(".")
    if key not in TARGET_EXTS:
        raise ImageToolError(
            f"--to 只支持 {', '.join(TARGET_EXTS)}，收到 {value!r}"
        )
    return TARGET_EXTS[key]


def add_common(parser: argparse.ArgumentParser) -> None:
    """编辑类子命令共用的两个参数。"""
    parser.add_argument("image", help="原图路径")
    parser.add_argument(
        "-o", "--output", default=None,
        help="结果保存路径；不填则自动放到原图旁边的 output/ 目录",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image_tool.py",
        description="读取图片基础信息并完成简单编辑（基于 OpenCV）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="显示图片基础信息")
    p.add_argument("image", help="图片路径")

    p = sub.add_parser("resize", help="缩放（可只给宽或高）")
    add_common(p)
    p.add_argument("-W", "--width", type=int, help="目标宽度（像素）")
    p.add_argument("-H", "--height", type=int, help="目标高度（像素）")

    p = sub.add_parser("crop", help="裁剪 (左, 上, 右, 下)")
    add_common(p)
    p.add_argument("-l", "--left", type=int, required=True)
    p.add_argument("-t", "--top", type=int, required=True)
    p.add_argument("-r", "--right", type=int, required=True)
    p.add_argument("-b", "--bottom", type=int, required=True)

    p = sub.add_parser("rotate", help="旋转 90 / 180 / 270 度")
    add_common(p)
    p.add_argument("-a", "--angle", type=int, required=True)

    p = sub.add_parser("flip", help="翻转 h / v / hv")
    add_common(p)
    p.add_argument("-d", "--direction", required=True)

    p = sub.add_parser("grayscale", help="彩色转灰度")
    add_common(p)

    p = sub.add_parser("convert", help="格式转换，如 PNG 转 JPG")
    add_common(p)
    p.add_argument("--to", required=True, help="目标格式，如 jpg / png")
    p.add_argument(
        "--quality", type=int, default=95,
        help="JPEG 质量 0~100（默认 95）",
    )
    return parser


def resolve_output(src: Path, args: argparse.Namespace, tag: str, ext: str) -> Path:
    """决定输出路径，并保证绝不覆盖原图、也绝不覆盖已有结果文件。"""
    if not args.output:
        return default_output_path(src, tag, ext)

    out = Path(args.output)
    if out.resolve() == src.resolve():
        raise ImageToolError("输出路径不能与原图相同，程序不会覆盖原图")
    if out.exists():
        stem, suffix = out.stem, out.suffix
        n = 1
        while out.exists():               # 同名自动加序号
            out = out.with_name(f"{stem}_{n}{suffix}")
            n += 1
    return out


def run(args: argparse.Namespace) -> int:
    """执行一条命令，成功返回 0。"""
    src = Path(args.image)

    if args.command == "info":
        print(format_info(get_image_info(src)))
        return 0

    img = load_image(src)                 # 文件不存在/不是图片都在这里变成友好提示
    out_ext = src.suffix
    quality = getattr(args, "quality", 95)

    if args.command == "resize":
        result = resize_image(img, args.width, args.height)
        tag = f"resize_{result.shape[1]}x{result.shape[0]}"
    elif args.command == "crop":
        result = crop_image(img, args.left, args.top, args.right, args.bottom)
        tag = f"crop_{args.left}_{args.top}_{args.right}_{args.bottom}"
    elif args.command == "rotate":
        result = rotate_image(img, args.angle)
        tag = f"rotate_{args.angle}"
    elif args.command == "flip":
        result = flip_image(img, args.direction)
        tag = f"flip_{args.direction.lower()}"
    elif args.command == "grayscale":
        result = to_grayscale(img)
        tag = "grayscale"
    elif args.command == "convert":
        out_ext = normalize_target(args.to)
        if args.output and Path(args.output).suffix.lower() != out_ext:
            raise ImageToolError(
                f"--output 的扩展名与 --to {out_ext.lstrip('.')} 不一致，"
                "请改成相同格式"
            )
        result = convert_image(img, out_ext)
        tag = f"convert_{out_ext.lstrip('.')}"
    else:                                 # argparse 已经挡住了，留个兜底
        raise ImageToolError(f"未知命令：{args.command}")

    out = resolve_output(src, args, tag, out_ext)
    saved = save_image(result, out, jpeg_quality=quality)

    print(f"已保存：{saved.resolve()}")
    print(f"原图保持不变：{src.resolve()}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args)
    except ImageToolError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"错误：文件操作失败（{exc}）", file=sys.stderr)
        return 1
    except cv2.error as exc:
        print(f"错误：OpenCV 处理失败（{exc}）", file=sys.stderr)
        return 1
    except Exception as exc:              # 兜底：不把 traceback 甩给使用者
        print(f"错误：发生未预期的问题（{type(exc).__name__}: {exc}）", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
