"""Build each work's introduction with its matched, inline WebGL preview."""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
import re
import shutil
import subprocess
from urllib.parse import quote,urljoin
import zipfile

REPO=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1048576),b''):h.update(block)
    return h.hexdigest()

def markdown(work):
    source=(REPO/work['readme']).read_text(encoding='utf-8')
    source=re.sub(r'<!-- interactive-preview:start -->[\s\S]*?<!-- interactive-preview:end -->','',source)
    source='\n'.join(source.splitlines()[1:])
    base='https://github.com/IcyRyna/war-thunder-liveries/blob/main/'+work['readme']
    raw='https://raw.githubusercontent.com/IcyRyna/war-thunder-liveries/main/'+work['readme']
    def rewrite(match):
        bang,label,target=match.groups()
        if not re.match(r'https?://|#',target):target=urljoin(raw if bang else base,target)
        return f'{bang}[{label}]({target})'
    source=re.sub(r'(!?)\[([^\]]*)\]\(([^)]+)\)',rewrite,source)
    payload=json.dumps({'text':source,'mode':'gfm','context':'IcyRyna/war-thunder-liveries'}).encode()
    return subprocess.check_output(['gh','api','markdown','--input','-'],input=payload).decode('utf-8').replace('<img ','<img loading="lazy" decoding="async" ')

def page(title,content,depth=0):
    root='../'*depth
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · 涂装作品集</title><link rel="icon" href="data:,"><link rel="stylesheet" href="{root}site.css"></head><body><header><a href="{root}index.html">战争雷霆 · 涂装作品集</a><a href="https://github.com/IcyRyna/war-thunder-liveries">GitHub 仓库</a></header><main>{content}</main><footer>原生 UV 颜色预览 · 反射、法线与完整材质以游戏内为准</footer><script src="{root}site.js" defer></script></body></html>'''

def build(out,viewer,previews_dir=None,archive=None):
    data=json.loads((REPO/'site/previews.json').read_text(encoding='utf-8'))
    out=Path(out)
    if out.exists():raise FileExistsError('Build output must be a new directory')
    out.mkdir(parents=True)
    if archive:
        archive=Path(archive)
        if digest(archive)!=data['bundle_sha256']:raise ValueError('Preview archive SHA-256 changed')
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or sum(i.file_size for i in z.infolist())>2*1024**3:raise ValueError('Invalid preview archive')
            for name in names:
                path=Path(name)
                if path.is_absolute() or '..' in path.parts or '\\' in name or not name.startswith('previews/'):raise ValueError('Unsafe preview archive member')
            z.extractall(out)
    else:shutil.copytree(Path(previews_dir)/'previews',out/'previews')
    files=0
    for work in data['works']:
        for variant in work['variants']:
            folder=(out/variant['scene']).parent
            for name,record in variant['files'].items():
                if Path(name).name!=name:raise ValueError('Invalid preview member')
                path=folder/name
                if not path.is_file() or digest(path)!=record['sha256']:raise ValueError('Preview asset changed: '+str(path))
                files+=1
    shutil.copytree(viewer,out/'viewer')
    for name in ['site.css','site.js']:shutil.copyfile(REPO/'site'/name,out/name)
    rendered=dict(zip([w['id'] for w in data['works']],ThreadPoolExecutor(max_workers=4).map(markdown,data['works'])))
    cards=[]
    for work in data['works']:
        title=html.escape(work['title']);identifier=work['id'];folder=out/'works'/identifier;folder.mkdir(parents=True)
        variants=work['variants'];scenes=[{'label':v['label'],'scene':'../'+v['scene']} for v in variants]
        choices=''
        if len(scenes)>1:choices='<label class="variant">车型版本<select id="variant">'+''.join(f'<option value="{i}">{html.escape(v["label"])}</option>' for i,v in enumerate(scenes))+'</select></label>'
        iframe='../../viewer/?embed=1&scene='+quote(scenes[0]['scene'],safe='')
        content=f'''<nav class="breadcrumb"><a href="../../index.html">全部作品</a><span>{'参考原作' if work['kind']=='references' else '地面载具' if work['category']=='ground' else '飞机涂装'}</span></nav><h1>{title}</h1><p class="work-status">状态：{html.escape(work["status"])}</p><section class="interactive"><div class="preview-title"><h2>这套涂装的 3D 预览</h2><span>拖动旋转 · 滚轮拉近</span></div>{choices}<iframe id="preview" title="{title} 三维预览" src="{iframe}" data-scenes="{html.escape(json.dumps(scenes,ensure_ascii=False),quote=True)}" allow="fullscreen" loading="lazy"></iframe><p class="note">已自动载入对应车型和本套涂装 · 可在画面中切换清晰度与视角</p></section><article>{rendered[identifier]}</article>'''
        (folder/'index.html').write_text(page(work['title'],content,2),encoding='utf-8')
        cards.append(f'<a class="work" href="works/{identifier}/"><small>{"参考原作" if work["kind"]=="references" else "地面载具" if work["category"]=="ground" else "飞机涂装"} · {html.escape(work["status"])}</small><h2>{title}</h2><span>打开介绍与 3D 预览 →</span></a>')
    (out/'index.html').write_text(page('作品与 3D 预览','<p class="eyebrow">可旋转的整车与机体预览</p><h1>每套涂装，放回对应的模型。</h1><p class="intro">选择作品，直接查看已装好涂装的三维模型、介绍和下载。保留各作品原有评价与来源。</p><div class="works">'+''.join(cards)+'</div>'),encoding='utf-8')
    print(json.dumps({'works':len(cards),'asset_files_verified':files,'output':str(out)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--viewer',type=Path,required=True);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--previews-dir',type=Path);group.add_argument('--archive',type=Path);a=p.parse_args();build(a.out,a.viewer,a.previews_dir,a.archive)
