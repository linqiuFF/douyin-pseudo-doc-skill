#!/usr/bin/env python3
"""根据分镜 JSON 调用 OpenAI 生图接口，批量生成伪纪录片图文的图片。

先生成定妆照，再按顺序生成每一张；写了 refs 的图会把对应图片作为输入一起发过去，
保证标记物和场景一致。日期水印和配图文案由脚本画上去，不交给模型写字。

用法：
  python generate_images.py storyboard.json                 生成全部（已生成的跳过）
  python generate_images.py storyboard.json --only 6 7      只重做第6、7张
  python generate_images.py storyboard.json --compose-only  只重新加水印和文案，不调接口
  python generate_images.py storyboard.json --dry-run       不调接口，用占位图把流程走一遍

需要：pip install openai pillow，并设置环境变量 OPENAI_API_KEY。
"""

import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = "1024x1536"

CJK_FONTS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

DIGIT_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

NO_TEXT_RULE = "画面里不要出现任何日期水印、文字、字幕或标志，日期水印之后会单独加。"


def fail(msg):
    print(f"错误：{msg}", file=sys.stderr)
    sys.exit(1)


def load_board(path):
    try:
        board = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"读不了分镜文件 {path}：{e}")

    refs = {r["id"]: r for r in board.get("references", [])}
    seen = set()
    for shot in board.get("shots", []):
        sid = shot["id"]
        if sid in seen:
            fail(f"第{sid}张的序号重复了")
        for dep in shot.get("refs", []):
            if isinstance(dep, int):
                if dep not in seen:
                    fail(f"第{sid}张参考了第{dep}张，但第{dep}张必须排在它前面")
            elif dep not in refs:
                fail(f"第{sid}张参考了 {dep!r}，但 references 里没有这个定妆照")
        seen.add(sid)
    if not seen:
        fail("分镜文件里没有 shots")
    return board, refs


def raw_name(item_id):
    return f"ref-{item_id}.png" if isinstance(item_id, str) else f"{item_id:02d}.png"


def ref_label(dep, refs):
    if isinstance(dep, int):
        return f"第{dep}张成品图"
    return f"{refs[dep].get('name', dep)}的定妆照"


def build_prompt(board, body, deps, refs):
    parts = [board.get("style", "").strip(), NO_TEXT_RULE]
    if deps:
        labels = "；".join(f"第{i}张输入图是{ref_label(d, refs)}" for i, d in enumerate(deps, 1))
        parts.append(f"输入图片说明：{labels}。输入图里的物件和场景要保持一致，按下面的描述画出这一张。")
    parts.append(body.strip())
    return "\n\n".join(p for p in parts if p)


def call_api(client, args, prompt, dep_paths):
    extra = {"input_fidelity": args.fidelity} if args.fidelity and dep_paths else None
    if dep_paths:
        files = [open(p, "rb") for p in dep_paths]
        try:
            resp = client.images.edit(
                model=args.model, image=files, prompt=prompt, size=SIZE,
                quality=args.quality, extra_body=extra,
            )
        finally:
            for f in files:
                f.close()
    else:
        resp = client.images.generate(model=args.model, prompt=prompt, size=SIZE, quality=args.quality)
    return base64.b64decode(resp.data[0].b64_json)


def placeholder(item_id, deps):
    img = Image.new("RGB", (1024, 1536), (90, 90, 90))
    draw = ImageDraw.Draw(img)
    font = load_font(CJK_FONTS, 60) or ImageFont.load_default()
    label = f"定妆照 {item_id}" if isinstance(item_id, str) else f"第{item_id}张"
    draw.text((60, 80), label, fill="white", font=font)
    if deps:
        draw.text((60, 180), "参考：" + ", ".join(map(str, deps)), fill="white", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def load_font(candidates, size):
    for path in candidates:
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return None


def draw_watermark(img, timestamp):
    w, h = img.size
    size = int(h * 0.032)
    font = load_font(DIGIT_FONTS + CJK_FONTS, size) or ImageFont.load_default(size=size)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    box = draw.textbbox((0, 0), timestamp, font=font)
    x = w - (box[2] - box[0]) - int(w * 0.05)
    y = h - (box[3] - box[1]) - int(h * 0.035)
    # 老相机日期戳：橙色字带一点光晕
    draw.text((x, y), timestamp, fill=(255, 120, 20, 255), font=font)
    glow = layer.filter(ImageFilter.GaussianBlur(size * 0.12))
    img.alpha_composite(glow)
    img.alpha_composite(layer)


def wrap_text(draw, text, font, max_width):
    lines, line = [], ""
    for ch in text:
        if draw.textlength(line + ch, font=font) > max_width and line:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def draw_caption(img, caption, font_path):
    w, h = img.size
    size = int(h * 0.026)
    font = load_font([font_path] + CJK_FONTS, size)
    if font is None:
        return False
    draw = ImageDraw.Draw(img)
    lines = wrap_text(draw, caption, font, w * 0.86)
    line_h = int(size * 1.45)
    y = h - int(h * 0.1) - line_h * len(lines)
    for line in lines:
        draw.text((int(w * 0.05), y), line, font=font, fill="white",
                  stroke_width=max(2, size // 14), stroke_fill=(0, 0, 0))
        y += line_h
    return True


def compose(raw_path, out_dir, shot, font_path, captions):
    img = Image.open(raw_path).convert("RGBA")
    if shot.get("timestamp"):
        draw_watermark(img, shot["timestamp"])
    name = f"{shot['id']:02d}.jpg"
    (out_dir / "final").mkdir(exist_ok=True)
    img.convert("RGB").save(out_dir / "final" / name, quality=85)
    if captions and shot.get("caption"):
        if not draw_caption(img, shot["caption"], font_path):
            return False
        (out_dir / "captioned").mkdir(exist_ok=True)
        img.convert("RGB").save(out_dir / "captioned" / name, quality=85)
    return True


def main():
    p = argparse.ArgumentParser(description="按分镜 JSON 批量生成伪纪录片图文图片")
    p.add_argument("storyboard", help="分镜 JSON 文件")
    p.add_argument("--out", help="输出目录，默认是分镜文件旁边的 output/")
    p.add_argument("--only", nargs="+", help="只重做这些（第几张的数字，或定妆照的 id）")
    p.add_argument("--compose-only", action="store_true", help="只重新加水印和文案")
    p.add_argument("--dry-run", action="store_true", help="不调接口，用占位图")
    p.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1"))
    p.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    p.add_argument("--fidelity", choices=["low", "high"], help="改图时保留输入图细节的程度，走样多时用 high")
    p.add_argument("--font", help="配图文案用的中文字体文件")
    p.add_argument("--no-captions", action="store_true", help="不在图上加配图文案")
    args = p.parse_args()

    board, refs = load_board(args.storyboard)
    out_dir = Path(args.out) if args.out else Path(args.storyboard).resolve().parent / "output"
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    only = None
    if args.only:
        only = {int(x) if x.isdigit() else x for x in args.only}

    client = None
    if not (args.compose_only or args.dry_run):
        if not os.environ.get("OPENAI_API_KEY"):
            fail("没有设置 OPENAI_API_KEY 环境变量")
        try:
            from openai import OpenAI
        except ImportError:
            fail("缺少 openai 库，先运行：pip install openai pillow")
        client = OpenAI()

    jobs = [(r["id"], r["prompt"], []) for r in board.get("references", [])]
    jobs += [(s["id"], s["prompt"], s.get("refs", [])) for s in board["shots"]]

    redone = set()
    if not args.compose_only:
        for item_id, body, deps in jobs:
            path = raw_dir / raw_name(item_id)
            if path.exists() and (only is None or item_id not in only):
                continue
            if only is not None and item_id not in only:
                continue
            dep_paths = [raw_dir / raw_name(d) for d in deps]
            missing = [str(d) for d, dp in zip(deps, dep_paths) if not dp.exists()]
            if missing:
                fail(f"{item_id} 要参考的图还没生成：{', '.join(missing)}")
            label = f"定妆照 {item_id}" if isinstance(item_id, str) else f"第{item_id}张"
            print(f"生成 {label} ...", flush=True)
            if args.dry_run:
                data = placeholder(item_id, deps)
            else:
                try:
                    data = call_api(client, args, build_prompt(board, body, deps, refs), dep_paths)
                except Exception as e:  # 接口报错（含内容审核拒绝）时停下，避免后面的图参考不到
                    fail(f"{label} 生成失败：{e}")
            path.write_bytes(data)
            redone.add(item_id)

    stale = [s["id"] for s in board["shots"]
             if s["id"] not in redone and any(d in redone for d in s.get("refs", []))]
    if only is not None and stale:
        print(f"提示：第{'、'.join(map(str, stale))}张参考了刚重做的图，需要的话也一起重做：--only {' '.join(map(str, stale))}")

    captions = not args.no_captions
    caption_ok = True
    for shot in board["shots"]:
        raw = raw_dir / raw_name(shot["id"])
        if raw.exists():
            caption_ok &= compose(raw, out_dir, shot, args.font, captions)
    if captions and not caption_ok:
        print("提示：没找到中文字体，没加配图文案。可以用 --font 指定字体文件，或者用醒图手动加。")

    print(f"完成。成品在 {out_dir / 'final'}" + ("，带文案的在 " + str(out_dir / "captioned") if captions and caption_ok else ""))


if __name__ == "__main__":
    main()
