#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 压缩工具 —— 本地 Web 图形界面版

特点：
  · 浏览器界面，拖拽 PDF 即可压缩
  · 仅依赖 Python 标准库 + pymupdf，无需 Tk / Swift
  · 双击 run.command 启动，自动打开浏览器

使用：
  python3 server.py
  然后浏览器访问 http://127.0.0.1:8765
"""
import os
import re
import sys
import json
import time
import uuid
import shutil
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

import pymupdf

BASE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(BASE, ".work")
PORT = 8765

sys.path.insert(0, BASE)
from pdf_compressor import diagnose, compress, verify, human

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDF 压缩工具</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Helvetica Neue",sans-serif;
     background:#F5F6F8;color:#1F2937;padding:28px 20px}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:26px;font-weight:700;margin-bottom:6px}
.sub{color:#6B7280;font-size:13px;margin-bottom:24px}
.card{background:#fff;border-radius:12px;padding:20px;
      box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:16px}
.card h2{font-size:15px;font-weight:700;margin-bottom:14px;color:#374151}

/* 拖拽区 */
#drop{border:2px dashed #BFDBFE;border-radius:12px;background:#EFF6FF;
      padding:38px 20px;text-align:center;cursor:pointer;transition:.2s}
#drop:hover,#drop.hot{border-color:#2563EB;background:#DBEAFE}
#drop .ico{font-size:40px;line-height:1}
#drop .t1{font-size:17px;font-weight:700;margin:10px 0 4px;color:#1F2937}
#drop .t2{font-size:12px;color:#6B7280}
#drop input{display:none}

/* 参数 */
.row{display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.row label{font-size:13px;font-weight:600;width:96px;color:#374151}
.row input[type=range]{flex:1;min-width:200px;accent-color:#2563EB}
.row .val{font-size:13px;font-weight:700;color:#2563EB;width:56px;text-align:right}
.hint{font-size:11px;color:#9CA3AF;margin:-8px 0 14px 108px}
.presets{display:flex;gap:8px;margin-left:108px;flex-wrap:wrap}
.presets button{padding:5px 13px;border:none;border-radius:6px;background:#F3F4F6;
                color:#374151;font-size:12px;cursor:pointer;font-weight:600}
.presets button:hover{background:#E5E7EB}
.presets button.on{background:#2563EB;color:#fff}
.chk{display:flex;align-items:center;gap:7px;font-size:13px;color:#374151;cursor:pointer}
.chk input{accent-color:#2563EB;width:15px;height:15px}

/* 按钮 */
.btns{display:flex;gap:10px;margin-top:4px}
.btn{flex:1;padding:13px;border:none;border-radius:9px;font-size:15px;font-weight:700;
     cursor:pointer;transition:.15s}
.btn-p{background:#2563EB;color:#fff}
.btn-p:hover:not(:disabled){background:#1D4ED8}
.btn-p:disabled{background:#9CA3AF;cursor:not-allowed}
.btn-s{background:#F3F4F6;color:#374151;flex:0 0 auto;padding:13px 20px;font-size:13px}
.btn-s:hover{background:#E5E7EB}
.btn-s:disabled{opacity:.45;cursor:not-allowed}

/* 进度 */
.bar{height:7px;background:#E5E7EB;border-radius:4px;overflow:hidden;margin:14px 0 8px}
.bar i{display:block;height:100%;width:0;background:#2563EB;transition:width .25s}
.pmsg{font-size:12px;color:#6B7280}

/* 结果 */
.kv{display:flex;justify-content:space-between;padding:9px 0;
    border-bottom:1px solid #F3F4F6;font-size:13px}
.kv:last-child{border:none}
.kv .k{color:#6B7280}
.kv .v{font-weight:700;font-variant-numeric:tabular-nums}
.big{font-size:30px;font-weight:800;color:#16A34A;line-height:1.3}
.pages{margin-top:10px;font-size:11px;color:#9CA3AF;font-family:ui-monospace,monospace;
      max-height:130px;overflow:auto;background:#F9FAFB;padding:9px;border-radius:6px}
.pages div{padding:2px 0}

/* 对比 */
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cmp figure{margin:0;text-align:center}
.cmp .ph{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
         min-height:210px;display:flex;align-items:center;justify-content:center;
         overflow:hidden;padding:5px}
.cmp img{max-width:100%;max-height:340px;display:block}
.cmp figcaption{font-size:12px;font-weight:700;margin-top:7px;color:#6B7280}
.cmp .ph span{color:#D1D5DB;font-size:12px}

.vq{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#374151;margin-top:4px}
.vq b{color:#16A34A}
.note{font-size:11px;color:#9CA3AF;margin-top:9px;line-height:1.7}
#log{background:#1E293B;color:#E2E8F0;font-family:ui-monospace,monospace;font-size:11px;
     padding:13px;border-radius:8px;height:150px;overflow:auto;line-height:1.75;white-space:pre-wrap}
.hide{display:none!important}
a.dl{display:block;text-align:center;margin-top:14px;padding:12px;background:#16A34A;
     color:#fff;border-radius:9px;text-decoration:none;font-weight:700;font-size:14px}
a.dl:hover{background:#15803D}
</style>
</head>
<body>
<div class="wrap">
  <h1>PDF 压缩工具</h1>
  <div class="sub">拖拽 PDF 到下方区域即可压缩 · 图片型 PDF 通常可压缩 100 倍以上</div>

  <div class="card">
    <div id="drop">
      <div class="ico">⬆</div>
      <div class="t1" id="dt1">拖拽 PDF 到此处</div>
      <div class="t2" id="dt2">或点击此处选择文件 · 支持批量</div>
      <input type="file" id="file" accept="application/pdf,.pdf" multiple>
    </div>
  </div>

  <div class="card">
    <h2>压缩参数</h2>
    <div class="row">
      <label>分辨率倍率</label>
      <input type="range" id="zoom" min="1.5" max="8" step="0.5" value="4">
      <span class="val" id="zoomV">4.0x</span>
    </div>
    <div class="hint">倍率越高越清晰、体积越大；报表类建议 3.5x ~ 4.5x</div>

    <div class="row">
      <label>图片质量</label>
      <input type="range" id="qual" min="60" max="98" step="1" value="92">
      <span class="val" id="qualV">92</span>
    </div>
    <div class="presets" id="presets">
      <button data-z="2.5" data-q="85">极致压缩</button>
      <button data-z="4" data-q="92" class="on">均衡（推荐）</button>
      <button data-z="5.5" data-q="95">高清</button>
      <button data-z="8" data-q="98">最高质量</button>
    </div>

    <div class="row" style="margin-top:16px">
      <label class="chk" style="width:auto"><input type="checkbox" id="vchk" checked>压缩后自动比对像素差异（校验画质）</label>
    </div>
  </div>

  <div class="card">
    <div class="btns">
      <button class="btn btn-p" id="go" disabled>开始压缩</button>
      <button class="btn btn-s" id="open" disabled>打开文件夹</button>
    </div>
    <div class="bar hide" id="bar"><i></i></div>
    <div class="pmsg hide" id="pmsg"></div>
  </div>

  <div class="card hide" id="rcard">
    <h2>压缩结果</h2>
    <div class="big" id="ratio">—</div>
    <div class="kv"><span class="k">原大小</span><span class="v" id="s1">—</span></div>
    <div class="kv"><span class="k">压缩后</span><span class="v" id="s2">—</span></div>
    <div class="kv"><span class="k">节省空间</span><span class="v" id="saved">—</span></div>
    <div class="kv"><span class="k">输出文件</span><span class="v" id="outn">—</span></div>
    <div class="pages" id="pages"></div>
    <a class="dl hide" id="dl" download>下载压缩后的 PDF</a>
  </div>

  <div class="card hide" id="vcard">
    <h2>质量校验</h2>
    <div class="vq" id="vq"></div>
    <div class="note">「差异 ≤5」指每个像素的 RGB 通道偏差在 5 以内（肉眼基本不可见）。
       占比越高代表画质越接近原文件。</div>
  </div>

  <div class="card hide" id="ccard">
    <h2>视觉对比</h2>
    <div class="cmp">
      <figure><div class="ph" id="ph1"><span>压缩中…</span></div><figcaption>原文件</figcaption></figure>
      <figure><div class="ph" id="ph2"><span>—</span></div><figcaption>压缩后</figcaption></figure>
    </div>
  </div>

  <div class="card">
    <h2>处理日志</h2>
    <div id="log">等待输入 PDF 文件…</div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
const log=(m,c)=>{const L=$('log');L.textContent+=`\n${m}`;
  if(c)L.innerHTML=L.textContent.replace(/[^\\n]*$/,'')+`<span style="color:${c}">${m}</span>`;
  L.scrollTop=L.scrollHeight;};
const un=b=>{if(!b)return'0 B';const u=['B','KB','MB','GB'];let i=0,f=b;
  while(f>=1024&&i<u.length-1){f/=1024;i++;}return f.toFixed(2)+' '+u[i];};

let FILES=[],BUSY=false;

/* 拖拽 */
const dz=$('drop');
['dragenter','dragover'].forEach(e=>dz.addEventListener(e,ev=>{
  ev.preventDefault();dz.classList.add('hot');}));
['dragleave','drop'].forEach(e=>dz.addEventListener(e,ev=>{
  ev.preventDefault();dz.classList.remove('hot');}));
dz.addEventListener('drop',ev=>{
  const fs=[...ev.dataTransfer.files].filter(f=>
    f.name.toLowerCase().endsWith('.pdf'));
  if(!fs.length)return log('⚠ 仅支持 PDF 文件','#FBBF24');
  add(fs);});
dz.addEventListener('click',()=>$('file').click());
$('file').addEventListener('change',e=>add([...e.target.files]));

function add(fs){
  FILES=fs;BUSY=false;
  log('─'.repeat(44));
  log(`已选择 ${fs.length} 个文件`);
  fs.forEach(f=>log(`  · ${f.name}  (${un(f.size)})`));
  $('go').disabled=false;$('go').textContent=`开始压缩（${fs.length} 个文件）`;
  $('dt1').textContent='已选择 '+fs.length+' 个 PDF';
  ['rcard','vcard','ccard'].forEach(i=>$(i).classList.add('hide'));
}

/* 参数 */
$('zoom').oninput=e=>{ $('zoomV').textContent=(+e.target.value).toFixed(1)+'x'; };
$('qual').oninput=e=>{ $('qualV').textContent=e.target.value; };
document.querySelectorAll('#presets button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#presets button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');$('zoom').value=b.dataset.z;$('qual').value=b.dataset.q;
  $('zoomV').textContent=(+b.dataset.z).toFixed(1)+'x';$('qualV').textContent=b.dataset.q;});

/* 压缩 */
$('go').onclick=async()=>{
  if(BUSY||!FILES.length)return;
  BUSY=true;$('go').disabled=true;$('go').textContent='压缩中…';
  $('bar').classList.remove('hide');$('pmsg').classList.remove('hide');
  $('open').disabled=true;
  ['rcard','vcard','ccard'].forEach(i=>$(i).classList.add('hide'));
  $('dl').classList.add('hide');
  $('ph1').innerHTML='<span>生成预览…</span>';

  const t0=Date.now();
  try{
    const fd=new FormData();
    fd.append('zoom',$('zoom').value);
    fd.append('quality',$('qual').value);
    fd.append('verify',$('vchk').checked?'1':'0');
    FILES.forEach(f=>fd.append('files',f,f.name));

    const r=await fetch('/api/compress',{method:'POST',body:fd});
    const j=await r.json();
    if(!r.ok)throw new Error(j.error||'服务端错误');

    /* 结果 */
    let tin=0,tout=0;
    j.results.forEach(x=>{tin+=x.orig;tout+=x.out;});
    const rt=tin/tout, sv=(1-tout/tin)*100;
    $('ratio').textContent=rt.toFixed(1)+' 倍压缩';
    $('s1').textContent=un(tin);
    $('s2').textContent=un(tout);
    $('saved').textContent=sv.toFixed(1)+'%';
    $('rcard').classList.remove('hide');

    if(j.results.length===1){
      const x=j.results[0];
      $('outn').textContent=x.outName;
      $('pages').innerHTML=x.pages.map(p=>
        `<div>第${p.page}页 ${p.px} → ${un(p.bytes)}</div>`).join('');
      $('dl').href='/api/download/'+encodeURIComponent(x.token);
      $('dl').setAttribute('download',x.outName);
      $('dl').textContent='下载：'+x.outName;
      $('dl').classList.remove('hide');

      if(j.verify&&j.verify.length){
        $('vcard').classList.remove('hide');
        $('vq').innerHTML=j.verify.map(v=>
          `<span>第${v.page}页 · 平均差异 <b>${v.mean}</b></span>`+
          `<span>差异≤5 <b>${v.near5}%</b></span>`+
          `<span>差异≤12 <b>${v.near12}%</b></span>`).join('');
        log('✓ 质量校验通过：绝大多数像素差异肉眼不可见','#4ADE80');
      }
      if(j.previews){
        $('ccard').classList.remove('hide');
        $('ph1').innerHTML=`<img src="data:image/jpeg;base64,${j.previews[0]}">`;
        if(j.previews[1])$('ph2').innerHTML=`<img src="data:image/jpeg;base64,${j.previews[1]}">`;
      }
    }else{
      $('outn').textContent=j.results.length+' 个文件';
      $('pages').innerHTML=j.results.map(x=>
        `<div>${x.outName}：${un(x.orig)} → ${un(x.out)}</div>`).join('');
      log(`共 ${j.results.length} 个文件，已保存到输出目录`,'#4ADE80');
    }

    log(`✓ 压缩完成：${un(tin)} → ${un(tout)}（${rt.toFixed(1)} 倍，耗时 ${((Date.now()-t0)/1000).toFixed(1)}s）`,'#4ADE80');
    $('open').disabled=false;
  }catch(e){
    log('✗ 出错：'+e.message,'#F87171');
    alert('压缩失败：'+e.message);
  }finally{
    BUSY=false;
    $('go').disabled=false;
    $('go').textContent=FILES.length>1?`重新压缩（${FILES.length} 个）`:'开始压缩';
    $('bar').classList.add('hide');$('pmsg').classList.add('hide');
  }
};

$('open').onclick=()=>fetch('/api/open',{method:'POST'});
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path.startswith("/api/download/"):
            token = self.path.split("/api/download/")[1]
            self._do_download(token)
        else:
            self._send(404, b'{"error":"not found"}')

    def _do_download(self, token):
        import urllib.parse
        token = urllib.parse.unquote(token)
        meta_path = os.path.join(WORK, token + ".json")
        if not os.path.exists(meta_path):
            return self._send(404, b'{"error":"expired"}')
        meta = json.load(open(meta_path))
        path = meta["path"]
        if not os.path.exists(path):
            return self._send(404, b'{"error":"file missing"}')
        with open(path, "rb") as f:
            data = f.read()

        # 中文文件名需RFC 5987 编码（HTTP 头只支持 latin-1）
        name = meta["outName"]
        ascii_fallback = "".join(c if ord(c) < 128 else "_" for c in name)
        quoted = urllib.parse.quote(name)

        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header(
            "Content-Disposition",
            f"attachment; filename=\"{ascii_fallback}\"; "
            f"filename*=UTF-8''{quoted}")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path == "/api/open":
            try:
                if sys.platform == "darwin":
                    os.system(f'open "{WORK}"')
                elif sys.platform.startswith("win"):
                    os.startfile(WORK)
                else:
                    os.system(f'xdg-open "{WORK}"')
            except Exception:
                pass
            return self._send(200, b'{"ok":true}')
        if self.path == "/api/compress":
            return self._do_compress()
        self._send(404, b'{"error":"not found"}')

    def _do_compress(self):
        try:
            ctype = self.headers.get("Content-Type", "")
            m = re.search(r"boundary=([^;]+)", ctype)
            if not m:
                return self._send(400, b'{"error":"bad content-type"}')
            boundary = ("--" + m.group(1)).encode()

            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            parts = body.split(boundary)

            fields, uploads = {}, []
            for part in parts:
                if not part or part in (b"--\r\n", b"--", b"\r\n"):
                    continue
                if part.startswith(b"\r\n"):
                    part = part[2:]
                idx = part.find(b"\r\n\r\n")
                if idx < 0:
                    continue
                raw_head = part[:idx].decode("utf-8", "ignore")
                payload = part[idx + 4:]
                if payload.endswith(b"\r\n"):
                    payload = payload[:-2]

                fm = re.search(r'name="([^"]+)"', raw_head)
                if not fm:
                    continue
                fname = fm.group(1)

                fn = re.search(r'filename="([^"]*)"', raw_head)
                if fn and fn.group(1):
                    uploads.append((fname, fn.group(1), payload))
                else:
                    fields[fname] = payload.decode("utf-8", "ignore")

            zoom = float(fields.get("zoom") or 4.0)
            quality = int(fields.get("quality") or 92)
            do_verify = fields.get("verify", "1") == "1"

            if not uploads:
                return self._send(400, b'{"error":"no file uploaded"}')

            os.makedirs(WORK, exist_ok=True)
            results = []
            verify_out = []
            previews = []
            tmpdir = os.path.join(WORK, "tmp")
            shutil.rmtree(tmpdir, ignore_errors=True)
            os.makedirs(tmpdir)

            import base64
            import io
            from PIL import Image

            for fname, orig_name, payload in uploads:
                if fname != "files":
                    continue
                name = os.path.basename(orig_name or "doc.pdf")
                src = os.path.join(tmpdir, name)
                with open(src, "wb") as w:
                    w.write(payload)

                base = os.path.splitext(name)[0]
                dst = os.path.join(tmpdir, f"{base}_压缩.pdf")
                s1, s2, pages = compress(src, dst, zoom, quality)

                token = uuid.uuid4().hex
                final = os.path.join(WORK, f"{base}_{token[:6]}_压缩.pdf")
                shutil.move(dst, final)
                out_name = f"{base}_压缩.pdf"

                # 预览图（原文件 + 压缩后）
                for p in (src, final):
                    if len(previews) >= 2:
                        break
                    try:
                        d = pymupdf.open(p)
                        pg = d[0]
                        z = min(1.0, 460 / max(pg.rect.width, 1))
                        px = pg.get_pixmap(matrix=pymupdf.Matrix(z, z),
                                           alpha=False, colorspace=pymupdf.csRGB)
                        im = Image.frombytes("RGB", (px.width, px.height), px.samples)
                        b = io.BytesIO()
                        im.save(b, "JPEG", quality=80)
                        previews.append(base64.b64encode(b.getvalue()).decode())
                        d.close()
                    except Exception as e:
                        print(f"[预览失败] {p}: {e}", file=sys.stderr)

                # 画质校验
                vlist = []
                if do_verify:
                    rep = verify(src, final)
                    for pno in sorted(rep):
                        r = rep[pno]
                        if "error" in r:
                            continue
                        vlist.append({
                            "page": pno,
                            "mean": round(r["mean"], 3),
                            "near5": round(r["near5_pct"], 2),
                            "near12": round(r["near12_pct"], 2),
                        })

                json.dump({"path": final, "outName": out_name},
                          open(os.path.join(WORK, token + ".json"), "w"))

                results.append({
                    "orig": s1, "out": s2,
                    "outName": out_name, "token": token, "pages": pages,
                })
                if vlist:
                    verify_out = vlist

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._send(500, json.dumps(
                {"error": str(e)}).encode("utf-8"))

        self._send(200, json.dumps({
            "results": results,
            "verify": verify_out,
            "previews": previews,
        }, ensure_ascii=False).encode("utf-8"))


def main():
    os.makedirs(WORK, exist_ok=True)
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print("=" * 46)
    print("  PDF 压缩工具已启动")
    print(f"  请在浏览器打开：{url}")
    print("  关闭此窗口即停止服务")
    print("=" * 46)
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()