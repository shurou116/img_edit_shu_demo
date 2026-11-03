"""生成几张很小的示例图片，方便照着 README 里的命令自己动手试。

运行：python make_samples.py
会在 samples/ 下生成 3 张图，总共几十 KB，不会污染仓库。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from image_io import save_image

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
H, W = 240, 320


def build_color() -> np.ndarray:
    """彩色渐变 + 几个形状 + 文字，方便肉眼判断旋转/翻转是否生效。"""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        img[y, :, 0] = int(255 * y / H)          # B 通道纵向渐变
    for x in range(W):
        img[:, x, 1] = int(255 * x / W)          # G 通道横向渐变
    cv2.rectangle(img, (20, 20), (120, 100), (0, 0, 255), -1)   # 红块
    cv2.circle(img, (250, 150), 45, (0, 255, 255), -1)          # 黄圆
    cv2.putText(img, "TOP", (135, 32), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def build_rgba() -> np.ndarray:
    """带透明通道的 PNG：中心圆不透明，圆外完全透明。"""
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[:, :, :3] = (200, 60, 30)               # BGR 蓝色
    cv2.circle(rgba[:, :, 3], (160, 120), 80, 255, -1)  # 只画 alpha 通道
    return rgba


def main() -> None:
    SAMPLES.mkdir(exist_ok=True)
    color = build_color()

    targets = {
        "demo.jpg": color,
        "demo.png": build_rgba(),
        "demo_gray.png": cv2.cvtColor(color, cv2.COLOR_BGR2GRAY),
    }
    for name, img in targets.items():
        path = SAMPLES / name
        path.unlink(missing_ok=True)     # 生成脚本允许重建示例图
        save_image(img, path)
        print(f"已生成：{path}")
    print(f"\n共 {len(targets)} 张，颜色模式分别是 BGR / BGRA / 灰度。")


if __name__ == "__main__":
    main()
