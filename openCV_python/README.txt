========================================================================
图片信息与简单编辑工具 —— 使用说明
========================================================================

一、这个程序是做什么的
------------------------------------------------------------------------
这是一个用 Python + OpenCV 写的命令行程序：没有图形界面，在终端里
敲命令运行。

它能做两件事：

  1. 读取一张图片的基础信息
       文件名、图片格式（JPEG / PNG 等）、宽度和高度（像素）、
       颜色模式（BGR / BGRA / 灰度）、文件大小（KB 或 MB，保留 2 位小数）

  2. 对图片做 6 种简单编辑
       缩放、裁剪、旋转、翻转、灰度化、格式转换

支持 JPEG / PNG / BMP / WEBP / TIFF 等常见格式。

几条重要约定：
  * 所有编辑结果都保存成"新文件"，默认放在原图旁边的 output 目录里，
    原图永远不会被改动；程序会把实际保存位置打印出来。
  * 如果输出文件已经存在，程序不会覆盖它，会自动加 _1、_2 这样的序号。
  * 文件不存在、不是有效图片、参数不合法（例如宽高小于等于 0）时，
    程序给出明确提示并退出，不会直接崩溃或甩出一堆报错。
  * 带透明通道的 PNG 存成 JPG 时，会先和白色背景合成再去掉 alpha
    （JPEG 格式本身不支持透明），所以透明区域是白色而不是黑色。

代码由 4 个模块组成，每个文件的职责：
  image_io.py      读写图片、判断格式和颜色模式、生成输出路径
  image_info.py    整理并格式化 5 项基础信息
  image_edits.py   6 个编辑函数（只处理数组，不碰文件）
  image_tool.py    命令行入口，解析参数、打印结果和错误
  make_samples.py  生成示例图片（可选，用来照着下面的命令练习）
  tests/           自测脚本


二、运行环境怎么配
------------------------------------------------------------------------
需要：Python 3.10 或更高版本（开发环境是 Python 3.13）。
依赖：opencv-python、numpy（装 opencv-python 会自动带上 numpy）。

【方式 A：用 uv，推荐】
  1. 安装 uv（已经装过就跳过这步）
       Linux / macOS:
         curl -LsSf https://astral.sh/uv/install.sh | sh
       Windows PowerShell:
         powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

  2. 在项目根目录（image_tool.py 所在的目录）执行：
         uv lock
         uv sync
     第一步生成 uv.lock 锁文件，第二步创建 .venv 虚拟环境并装好依赖。
     把 pyproject.toml 和 uv.lock 一起提交，别人装到的版本就完全一致。

  3. 之后所有命令都用 uv run 开头，不用手动激活环境，例如：
         uv run python image_tool.py --help

【方式 B：用 pip + venv】
  1. 在项目根目录依次执行：
         python3 -m venv .venv
         source .venv/bin/activate
         python -m pip install -r requirements.txt
     Windows 下第二行换成：  .venv\Scripts\activate

  2. 验证是否装好：
         python -c "import cv2; print(cv2.__version__)"
     能打印出版本号（例如 4.12.0）就说明环境 OK。

  3. 如果默认源提示"找不到可用的包版本"，可以临时换源，
     只影响这一条命令，不会改全局配置：
         python -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt


三、怎么运行
------------------------------------------------------------------------
所有命令都在项目根目录执行，基本格式是：
    python image_tool.py <命令> <图片路径> [参数]

用下面两条命令可以查看帮助：
    python image_tool.py --help
    python image_tool.py resize --help

【第 0 步：先生成示例图片】
    python make_samples.py

会生成 3 张很小的图片（一共几十 KB）：
    samples/demo.jpg        彩色图，320 x 240
    samples/demo.png        带透明通道的 PNG
    samples/demo_gray.png   灰度图

下面的例子都用这 3 张图，你可以换成自己的图片路径。


------------------------------------------------------------------------
1. 读取图片信息：info
------------------------------------------------------------------------
命令：
    python image_tool.py info samples/demo.jpg

预期输出（文件大小按实际为准）：
    ========== 图片基础信息 ==========
    文件名   : demo.jpg
    图片格式 : JPEG
    宽度     : 320 像素
    高度     : 240 像素
    颜色模式 : BGR 彩色（3 通道，OpenCV 顺序为 B-G-R）
    文件大小 : 8.42 KB
    =================================

把路径换成 samples/demo.png，颜色模式会显示"BGRA 彩色 + 透明（4 通道）"；
换成 samples/demo_gray.png，会显示"灰度（1 通道）"。


------------------------------------------------------------------------
2. 缩放：resize
------------------------------------------------------------------------
参数：
    --width  / -W    目标宽度（像素）
    --height / -H    目标高度（像素）
    -o / --output    指定结果保存路径（可选）

只给宽或只给高时，另一个尺寸按原图比例自动算；两个都给就按给定值拉伸。

示例：
    python image_tool.py resize samples/demo.jpg --width 160
    python image_tool.py resize samples/demo.jpg --height 120
    python image_tool.py resize samples/demo.jpg --width 400 --height 300

第一条的预期输出：
    已保存：/你的路径/image-tool/samples/output/demo_resize_160x120.jpg
    原图保持不变：/你的路径/image-tool/samples/demo.jpg

    （原图 320 x 240，只给宽 160，高度按比例变成 120）

错误示例：
    python image_tool.py resize samples/demo.jpg --width 0
    错误：宽度必须是正整数，收到 0

    python image_tool.py resize samples/demo.jpg
    错误：缩放至少要指定 --width 或 --height 之一


------------------------------------------------------------------------
3. 裁剪：crop
------------------------------------------------------------------------
参数（坐标顺序是 左、上、右、下，右和下不包含在结果里）：
    --left   / -l    左边界
    --top    / -t    上边界
    --right  / -r    右边界
    --bottom / -b    下边界

示例：
    python image_tool.py crop samples/demo.jpg --left 20 --top 20 --right 200 --bottom 150

结果文件名类似 demo_crop_20_20_200_150.jpg，尺寸是 180 x 130。

越界时不会崩溃，会给出明确提示：
    python image_tool.py crop samples/demo.jpg -l 0 -t 0 -r 5000 -b 5000
    错误：裁剪区域越界：图片只有 320x240（宽x高），你给的右下角是 (5000, 5000)


------------------------------------------------------------------------
4. 旋转：rotate
------------------------------------------------------------------------
参数：
    --angle / -a    角度，只支持 90（顺时针）、180、270（逆时针 90）

示例：
    python image_tool.py rotate samples/demo.jpg --angle 90
    python image_tool.py rotate samples/demo.jpg --angle 180
    python image_tool.py rotate samples/demo.jpg --angle 270

直角旋转用的是 OpenCV 的 cv2.rotate，不会裁掉内容、不会产生黑边。
传 45 会提示：错误：旋转角度只支持 90 / 180 / 270 度，收到 45


------------------------------------------------------------------------
5. 翻转：flip
------------------------------------------------------------------------
参数：
    --direction / -d    h = 水平（左右镜像）
                        v = 垂直（上下镜像）
                        hv = 两者都做

示例：
    python image_tool.py flip samples/demo.jpg --direction h
    python image_tool.py flip samples/demo.jpg --direction v
    python image_tool.py flip samples/demo.jpg --direction hv


------------------------------------------------------------------------
6. 灰度化：grayscale
------------------------------------------------------------------------
命令：
    python image_tool.py grayscale samples/demo.jpg

输出 demo_grayscale.jpg。再用 info 查看这个文件，颜色模式会显示"灰度（1 通道）"。


------------------------------------------------------------------------
7. 格式转换：convert
------------------------------------------------------------------------
参数：
    --to         目标格式：jpg / jpeg / png / bmp / webp / tif / tiff
    --quality    JPEG 质量 0~100，默认 95（只对 JPG 生效）

示例：
    python image_tool.py convert samples/demo.png --to jpg
    python image_tool.py convert samples/demo.jpg --to png --quality 90

第一条是重点：demo.png 带透明通道，而 JPEG 不支持 alpha，程序会按
"前景 x a + 白底 x (1-a)" 合成后再编码，所以透明区域是白色而不是黑色。


------------------------------------------------------------------------
8. 自己指定输出位置
------------------------------------------------------------------------
任何编辑命令都可以加 -o / --output：
    python image_tool.py resize samples/demo.jpg --width 160 -o /tmp/small.png

注意：
  * 输出路径不能和原图相同（程序会拒绝，不会覆盖原图）。
  * 用 convert 时，-o 的扩展名要和 --to 一致，否则会提示。
  * 如果目标文件已存在，会自动加序号，不会覆盖已有结果。


------------------------------------------------------------------------
9. 常见错误提示
------------------------------------------------------------------------
    python image_tool.py info 不存在.jpg
      错误：文件不存在：不存在.jpg

    python image_tool.py info README.md
      错误：不是有效的图片，或格式不受 OpenCV 支持：README.md

    python image_tool.py rotate samples/demo.jpg --angle 45
      错误：旋转角度只支持 90 / 180 / 270 度，收到 45

出问题时程序返回退出码 1，终端里不会出现 Python 的 traceback。


------------------------------------------------------------------------
10. 自测（提交前建议跑一遍）
------------------------------------------------------------------------
    python -m unittest discover -s tests -v

覆盖：信息读取、按比例缩放、裁剪越界、直角旋转、翻转、灰度化、
带透明 PNG 转 JPG、输出不覆盖原图、错误输入不崩溃、命令行端到端。


========================================================================
补充：给没参与过开发的人的最短路径
========================================================================
  1. 装好 Python 3.10+
  2. 把项目文件夹整个拷到虚拟机里，用 VSCode 打开这个文件夹
  3. 在 VSCode 终端里依次执行：
         python3 -m venv .venv
         source .venv/bin/activate
         python -m pip install -r requirements.txt
         python make_samples.py
         python image_tool.py info samples/demo.jpg
  4. 看到"图片基础信息"那几行，说明已经跑起来了；
     想试编辑功能，照着上面第 2~7 节敲命令即可，结果都在 samples/output/ 里。
========================================================================
