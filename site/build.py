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
from pack_glb import externalize_images, prepare_viewer

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
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · 涂装作品集</title><link rel="icon" href="data:,"><link rel="stylesheet" href="{root}site.css"></head><body><header><a href="{root}index.html">战争雷霆 · 涂装作品集</a><nav aria-label="下载与源码"><a href="https://github.com/IcyRyna/war-thunder-skin-skills/releases/tag/wt-paint-workbench/v1.0.0">下载本地工作台</a><a href="https://github.com/IcyRyna/war-thunder-liveries">GitHub 仓库</a></nav></header><main>{content}</main><footer>原生 UV · 反射与凹凸为 PBR 近似预览，完整材质以游戏内为准</footer><script src="{root}site.js" defer></script></body></html>'''

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
    # Reuse a new work's verified editable-source ZIP without replacing the pinned bundle.
    for extra in data.get('supplementary_archives',[]):
        filename=extra['filename'];prefix=extra['target_prefix'];members=extra['members']
        if Path(filename).name!=filename or not filename.endswith('.zip'):raise ValueError('Invalid supplementary archive filename')
        if not re.fullmatch(r'previews/[a-z0-9-]+/variant-[0-9]+/',prefix):raise ValueError('Invalid supplementary target prefix')
        if not 0<len(members)<=200 or len(set(members.values()))!=len(members):raise ValueError('Invalid supplementary member map')
        source=REPO/filename
        if digest(source)!=extra['sha256']:raise ValueError('Supplementary archive SHA-256 changed')
        with zipfile.ZipFile(source) as z:
            if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate supplementary archive members')
            if sum(z.getinfo(name).file_size for name in members)>256*1024**2:raise ValueError('Supplementary models exceed the size limit')
            for name,basename in members.items():
                path=Path(name)
                if not name.startswith('model/') or path.is_absolute() or '..' in path.parts or '\\' in name:raise ValueError('Unsafe supplementary source member')
                if Path(basename).name!=basename or Path(basename).suffix.lower() not in ('.glb','.png','.json'):raise ValueError('Unsafe supplementary target member')
                target=out/prefix/basename;target.parent.mkdir(parents=True,exist_ok=True)
                if not target.resolve().is_relative_to(out.resolve()):raise ValueError('Supplementary output escaped the build')
                with z.open(name) as original,target.open('xb') as output:shutil.copyfileobj(original,output)
    files=0
    for work in data['works']:
        for variant in work['variants']:
            folder=(out/variant['scene']).parent
            for name,record in variant['files'].items():
                if Path(name).name!=name:raise ValueError('Invalid preview member')
                path=folder/name
                if not path.is_file() or digest(path)!=record['sha256']:raise ValueError('Preview asset changed: '+str(path))
                files+=1
    # Keep full 4K pixels while fitting Pages' 1 GB published-site limit.
    # Source bundle is verified above; only byte-identical native PNGs share a URL.
    shared=out/'previews/shared';shared.mkdir()
    saved=0;seen=set()
    for work in data['works']:
        for variant in work['variants']:
            manifest=out/variant['scene'];folder=manifest.parent
            document=json.loads(manifest.read_text(encoding='utf-8'))
            handled=set()
            for row in document['materials']:
                records=[(row,'native_file','native_sha256')]
                records.extend((row.get('reflection',{}).get(channel,{}),'file','sha256') for channel in ('orm','normal'))
                for record,key,hash_key in records:
                    name=record.get(key)
                    if not name:continue
                    if not re.fullmatch(r'native-(?:color|orm|normal)-[0-9]+\.png',name):raise ValueError('Unexpected native image path')
                    path=folder/name;identity=record[hash_key];target=shared/(identity+'.png')
                    if path.exists() and name not in handled:
                        if digest(path)!=identity:raise ValueError('Native image SHA mismatch')
                        if identity not in seen:shutil.copyfile(path,target);seen.add(identity)
                        else:saved+=path.stat().st_size
                        handled.add(name)
                    record[key]='../../shared/'+identity+'.png'
            # Every native path comes from verified manifest records, inside this fresh output.
            native_names={p.name for p in folder.glob('native-*.png')}
            expected={name for name in variant['files'] if re.fullmatch(r'native-(?:color|orm|normal)-[0-9]+\.png',name)}
            if native_names!=expected:raise ValueError('Unexpected native output files')
            for name in expected:(folder/name).unlink()
            manifest.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
    # Share byte-identical embedded PNGs across every presentation model.
    # The model's geometry, UVs, materials and image pixels remain unchanged.
    packed=[]
    for work in data['works']:
        for variant in work['variants']:
            result=externalize_images((out/variant['scene']).with_name('model.glb'),shared)
            packed.append({'work':work['id'],**result})
    print(json.dumps({'lossless_model_packing':packed}))
    shutil.copytree(viewer,out/'viewer')
    prepare_viewer(out/'viewer/preview.js')
    for name in ['site.css','site.js']:shutil.copyfile(REPO/'site'/name,out/name)
    rendered=dict(zip([w['id'] for w in data['works']],ThreadPoolExecutor(max_workers=4).map(markdown,data['works'])))
    sections={r["id"]:r for r in data["sections"]}
    cards={key:[] for key in sections}
    for work in data['works']:
        section=work['section'];category=html.escape(sections[section]['title'])
        title=html.escape(work['title']);identifier=work['id'];folder=out/'works'/identifier;folder.mkdir(parents=True)
        variants=work['variants'];scenes=[{'label':v['label'],'scene':'../'+v['scene']} for v in variants]
        choices=''
        if len(scenes)>1:choices='<label class="variant">车型版本<select id="variant">'+''.join(f'<option value="{i}">{html.escape(v["label"])}</option>' for i,v in enumerate(scenes))+'</select></label>'
        iframe='../../viewer/?embed=1&scene='+quote(scenes[0]['scene'],safe='')
        content=f'''<nav class="breadcrumb"><a href="../../index.html">全部作品</a><a href="../../index.html?category={section}">{category}</a></nav><nav class="vehicle-kind">{'地面载具' if work['category']=='ground' else '飞机涂装'}</nav><h1>{title}</h1><p class="work-status">状态：{html.escape(work["status"])}</p><section class="interactive"><div class="preview-title"><h2>这套涂装的 3D 预览</h2><span>拖动旋转 · 滚轮拉近</span></div>{choices}<iframe id="preview" title="{title} 三维预览" src="{iframe}" data-scenes="{html.escape(json.dumps(scenes,ensure_ascii=False),quote=True)}" allow="fullscreen" loading="lazy"></iframe><p class="note">已自动载入对应车型和本套涂装 · 可在画面中切换清晰度与视角</p></section><article>{rendered[identifier]}</article>'''
        (folder/'index.html').write_text(page(work['title'],content,2),encoding='utf-8')
        cards[section].append(f'<a class="work" href="works/{identifier}/"><small>{"参考原作" if work["kind"]=="references" else "地面载具" if work["category"]=="ground" else "飞机涂装"} · {html.escape(work["status"])}</small><h2>{title}</h2><span>打开介绍与 3D 预览 →</span></a>')
    buttons='<button type="button" data-category="all" aria-pressed="true">全部作品 <span>'+str(len(data['works']))+'</span></button>'+''.join(f'<button type="button" data-category="{key}" aria-pressed="false">{html.escape(row["title"])} <span>{len(cards[key])}</span></button>' for key,row in sections.items())
    groups=''.join(f'<section class="work-group" data-section="{key}" id="{key}"><div class="group-heading"><h2>{html.escape(row["title"])}</h2><span>{len(cards[key])} 套</span></div><div class="works">'+''.join(cards[key])+'</div></section>' for key,row in sections.items())
    content='<p class="eyebrow">按分类浏览 · 每套作品内嵌 3D 预览</p><h1>涂装作品集</h1><p class="intro">选择分类，再打开作品查看对应模型、介绍与下载。历史方案和参考原作单独归档，作品评价保持原样。</p><nav class="category-filter" aria-label="作品分类">'+buttons+'</nav><p class="filter-result" id="filterResult" role="status" aria-live="polite">全部作品 · '+str(len(data['works']))+' 套</p>'+groups
    (out/'index.html').write_text(page('作品与 3D 预览',content),encoding='utf-8')
    output_bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if output_bytes>=950_000_000:raise ValueError('Published site exceeds the 950 MB resource budget')
    print(json.dumps({'works':sum(map(len,cards.values())),'asset_files_verified':files,'deduplicated_bytes':saved,'published_bytes':output_bytes,'output':str(out)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--viewer',type=Path,required=True);group=p.add_mutually_exclusive_group(required=True);group.add_argument('--previews-dir',type=Path);group.add_argument('--archive',type=Path);a=p.parse_args();build(a.out,a.viewer,a.previews_dir,a.archive)
