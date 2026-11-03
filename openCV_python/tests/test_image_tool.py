"""自测脚本：覆盖 README 第 10 节列出的主要场景。

在 openCV_python 目录下运行：
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from image_edits import (  # noqa: E402
    convert_image,
    crop_image,
    flip_image,
    resize_image,
    rotate_image,
    to_grayscale,
)
from image_info import get_image_info  # noqa: E402
from image_io import (  # noqa: E402
    ImageToolError,
    default_output_path,
    load_image,
    save_image,
)


def make_bgr() -> np.ndarray:
    """40x60 的 BGR 图，左上角放一个蓝色标记，方便判断翻转是否正确。"""
    img = np.zeros((40, 60, 3), dtype=np.uint8)
    img[:, :] = (10, 20, 30)
    img[0, 0] = (255, 0, 0)
    return img


class TempDirTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class TestInfo(TempDirTestCase):
    def test_color_png(self) -> None:
        path = self.tmp / "a.png"
        save_image(make_bgr(), path)
        info = get_image_info(path)
        self.assertEqual(info["文件名"], "a.png")
        self.assertEqual(info["图片格式"], "PNG")
        self.assertEqual(info["宽度"], "60 像素")
        self.assertEqual(info["高度"], "40 像素")
        self.assertIn("BGR", info["颜色模式"])
        self.assertTrue(info["文件大小"].endswith("KB"))

    def test_alpha_and_gray_modes(self) -> None:
        rgba = np.zeros((10, 12, 4), dtype=np.uint8)
        save_image(rgba, self.tmp / "a.png")
        self.assertIn("BGRA", get_image_info(self.tmp / "a.png")["颜色模式"])

        gray = np.zeros((10, 12), dtype=np.uint8)
        save_image(gray, self.tmp / "g.png")
        self.assertIn("灰度", get_image_info(self.tmp / "g.png")["颜色模式"])


class TestEdits(unittest.TestCase):
    def test_resize_keeps_aspect_ratio(self) -> None:
        self.assertEqual(resize_image(make_bgr(), width=30).shape, (20, 30, 3))
        self.assertEqual(resize_image(make_bgr(), height=20).shape, (20, 30, 3))

    def test_resize_rejects_invalid(self) -> None:
        with self.assertRaises(ImageToolError):
            resize_image(make_bgr(), width=0)
        with self.assertRaises(ImageToolError):
            resize_image(make_bgr())

    def test_crop(self) -> None:
        self.assertEqual(
            crop_image(make_bgr(), 5, 5, 25, 20).shape, (15, 20, 3)
        )
        with self.assertRaises(ImageToolError):
            crop_image(make_bgr(), 0, 0, 999, 999)
        with self.assertRaises(ImageToolError):
            crop_image(make_bgr(), 10, 0, 5, 10)

    def test_rotate(self) -> None:
        self.assertEqual(rotate_image(make_bgr(), 90).shape, (60, 40, 3))
        with self.assertRaises(ImageToolError):
            rotate_image(make_bgr(), 45)

    def test_flip(self) -> None:
        img = make_bgr()
        self.assertTrue(np.array_equal(flip_image(img, "h")[0, -1], img[0, 0]))
        self.assertTrue(np.array_equal(flip_image(img, "v")[-1, 0], img[0, 0]))
        self.assertTrue(np.array_equal(flip_image(img, "hv")[-1, -1], img[0, 0]))

    def test_grayscale_stays_one_channel_when_saved_as_jpg(self) -> None:
        # 回归测试：灰度图存成 JPG 后必须仍然是 1 通道
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "gray.jpg"
            save_image(to_grayscale(make_bgr()), path)
            self.assertEqual(load_image(path).ndim, 2)

    def test_alpha_flattened_to_white_for_jpg(self) -> None:
        rgba = np.zeros((20, 20, 4), dtype=np.uint8)
        rgba[:, :, :3] = (0, 0, 255)          # 红色前景，alpha 全 0（完全透明）
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.jpg"
            save_image(convert_image(rgba, ".jpg"), path)
            bgr = load_image(path)
            self.assertEqual(bgr.shape[2], 3)
            self.assertTrue(np.all(bgr[0, 0] > 240))   # JPEG 有压缩，留点余量


class TestOutput(TempDirTestCase):
    def test_default_output_never_overwrites(self) -> None:
        src = self.tmp / "a.jpg"
        save_image(make_bgr(), src)
        first = default_output_path(src, "resize_10x10", ".jpg")
        first.parent.mkdir(parents=True)
        first.write_bytes(b"x")
        second = default_output_path(src, "resize_10x10", ".jpg")
        self.assertNotEqual(first, second)

    def test_missing_file(self) -> None:
        with self.assertRaises(ImageToolError):
            load_image(self.tmp / "nope.jpg")

    def test_bad_output_extension(self) -> None:
        with self.assertRaises(ImageToolError):
            save_image(make_bgr(), self.tmp / "noext")


class TestCommandLine(unittest.TestCase):
    def test_info_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "a.png"
            save_image(make_bgr(), path)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "image_tool.py"), "info", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("图片基础信息", proc.stdout)
            self.assertIn("60 像素", proc.stdout)


if __name__ == "__main__":
    unittest.main()
