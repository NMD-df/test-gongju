# -*- coding: utf-8 -*-
"""
PDF 压缩核心模块（与 GUI 解耦，可单独使用）

原理：
  很多工具（如 jsPDF）生成的 PDF 会把 PNG 图片用 FlateDecode(zlib) 直接塞进 PDF。
  对大面积单色内容（表格截图、报表）zlib 压缩率极低，导致 PDF 体积接近原始像素总量。
  本模块将每页渲染为位图后重新编码为高质量 JPEG，可将此类 PDF 压缩 100倍以上。

处理流程：
  1. 诊断：解析 PDF 内部结构，定位体积大户（图片 / SMask / 冗余流）
  2. 压缩：按指定缩放倍率与质量逐页渲染 -> JPEG -> 重建 PDF
  3. 校验：同分辨率逐像素比对，输出客观质量指标
"""
import os
import pymupdf


# ============================================================
# 1. 诊断
# ============================================================
def diagnose(path):
    """分析 PDF 构成，返回体积分布诊断信息。"""
    doc = pymupdf.open(path)
    total = os.path.getsize(path)
    result = {
        "size": total,
        "pages": doc.page_count,
        "producer": (doc.metadata or {}).get("producer", ""),
        "text_chars": 0,
        "images": [],
        "stream_total": 0,
        "image_raw_total": 0,
        "has_text_layer": False,
    }

    for pno in range(doc.page_count):
        page = doc[pno]
        chars = len(page.get_text())
        result["text_chars"] += chars
        for im in page.get_images(full=True):
            xref = im[0]
            try:
                stream = doc.xref_stream(xref)
            except Exception:
                continue
            if stream is None:
                continue
            info = doc.extract_image(xref)
            result["images"].append({
                "page": pno + 1,
                "xref": xref,
                "w": im[2],
                "h": im[3],
                "is_smask": doc.xref_get_key(xref, "ColorSpace")[1] == "/DeviceGray",
                "raw": len(stream),
                "encoded": len(info["image"]),
                "ext": info["ext"],
            })
            result["image_raw_total"] += len(stream)

    xrefs = doc.xref_length()
    for x in range(1, xrefs):
        try:
            d = doc.xref_stream(x)
        except Exception:
            continue
        if d:
            result["stream_total"] += len(d)

    result["has_text_layer"] = result["text_chars"] > 0
    doc.close()
    return result


# ============================================================
# 2. 压缩
# ============================================================
def compress(src, dst, zoom=4.0, quality=92, progress=None):
    """
    压缩 PDF。

    参数:
        src:源文件路径
        dst     : 输出文件路径
        zoom    : 渲染缩放倍率（页面 595x842pt 时，4x ≈ 2382x3368 px）
        quality : JPEG 质量 1-100
        progress: 进度回调 (当前页, 总页数, 该页输出字节数)

    返回: (原字节数, 输出字节数, 逐页信息列表)
    """
    doc = pymupdf.open(src)
    out = pymupdf.open()
    mat = pymupdf.Matrix(zoom, zoom)
    page_infos = []

    try:
        for pno in range(doc.page_count):
            page = doc[pno]
            pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=pymupdf.csRGB)
            jpg = pix.tobytes("jpeg", jpg_quality=quality)

            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=jpg)

            page_infos.append({
                "page": pno + 1,
                "px": f"{pix.width}x{pix.height}",
                "bytes": len(jpg),
            })
            if progress:
                progress(pno + 1, doc.page_count, len(jpg))
    finally:
        out.save(dst, garbage=4, deflate=True, clean=True)
        out.close()
        doc.close()

    return os.path.getsize(src), os.path.getsize(dst), page_infos


# ============================================================
# 3. 质量校验
# ============================================================
def verify(src, dst, zoom=2.0):
    """
    同分辨率逐像素比对，输出客观质量指标。

    返回: {页码: {mean, near5_pct, near12_pct, max}}
    """
    from PIL import Image, ImageChops

    d1 = pymupdf.open(src)
    d2 = pymupdf.open(dst)
    m = pymupdf.Matrix(zoom, zoom)
    report = {}

    try:
        for pno in range(min(d1.page_count, d2.page_count)):
            p1 = d1[pno].get_pixmap(matrix=m, alpha=False, colorspace=pymupdf.csRGB)
            p2 = d2[pno].get_pixmap(matrix=m, alpha=False, colorspace=pymupdf.csRGB)
            if (p1.width, p1.height) != (p2.width, p2.height):
                report[pno + 1] = {"error": "尺寸不一致"}
                continue

            im1 = Image.frombytes("RGB", (p1.width, p1.height), p1.samples)
            im2 = Image.frombytes("RGB", (p2.width, p2.height), p2.samples)
            diff = ImageChops.difference(im1, im2).convert("L")
            hist = diff.histogram()
            total = sum(hist)
            mean = sum(i * c for i, c in enumerate(hist)) / total
            near5 = sum(hist[:6]) / total * 100
            near12 = sum(hist[:13]) / total * 100
            mx = max(i for i, c in enumerate(hist) if c > 0)

            report[pno + 1] = {
                "mean": mean,
                "near5_pct": near5,
                "near12_pct": near12,
                "max": mx,
                "size": f"{p1.width}x{p1.height}",
            }
    finally:
        d1.close()
        d2.close()
    return report


def human(n):
    """字节数转可读字符串。"""
    if n is None:
        return "-"
    u = ["B", "KB", "MB", "GB"]
    i = 0
    f = float(n)
    while f >= 1024 and i < len(u) - 1:
        f /= 1024.0
        i += 1
    return f"{f:.2f} {u[i]}"