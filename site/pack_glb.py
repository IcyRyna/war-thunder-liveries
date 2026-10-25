"""Share byte-identical embedded PNGs for explicitly opted-in supplementary models."""
import hashlib
import json
from pathlib import Path
import struct


def externalize_images(path, shared):
    data=path.read_bytes()
    magic,version,total=struct.unpack_from('<III',data)
    if (magic,version,total)!=(0x46546c67,2,len(data)):raise ValueError('Invalid GLB header')
    size,kind=struct.unpack_from('<II',data,12)
    if kind!=0x4e4f534a:raise ValueError('Missing GLB JSON')
    doc=json.loads(data[20:20+size]);offset=20+size
    size,kind=struct.unpack_from('<II',data,offset)
    if kind!=0x004e4942 or offset+8+size!=len(data):raise ValueError('Invalid GLB binary')
    binary=data[offset+8:]
    if len(doc['buffers'])!=1 or doc.get('skins') or doc.get('animations'):raise ValueError('Only static single-buffer models are supported')
    slots=[]
    def scan(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key.endswith('Texture') and isinstance(item,dict) and 'index' in item:slots.append(item)
                else:scan(item)
        elif isinstance(value,list):
            for item in value:scan(item)
    scan(doc['materials'])
    used=sorted({s['index'] for s in slots});mapping={old:new for new,old in enumerate(used)}
    doc['textures']=[doc['textures'][i] for i in used]
    for slot in slots:slot['index']=mapping[slot['index']]
    images=sorted({t['source'] for t in doc['textures']});mapping={old:new for new,old in enumerate(images)}
    selected=[doc['images'][i] for i in images]
    for texture in doc['textures']:texture['source']=mapping[texture['source']]
    shared.mkdir(exist_ok=True)
    for image in selected:
        if image.get('mimeType')!='image/png' or 'bufferView' not in image:raise ValueError('Expected an embedded PNG')
        view=doc['bufferViews'][image.pop('bufferView')];start=view.get('byteOffset',0)
        pixels=binary[start:start+view['byteLength']]
        if len(pixels)!=view['byteLength']:raise ValueError('Truncated embedded PNG')
        identity=hashlib.sha256(pixels).hexdigest();target=shared/(identity+'.png')
        if target.exists():
            if target.read_bytes()!=pixels:raise ValueError('Shared image collision')
        else:target.write_bytes(pixels)
        image['uri']='../../shared/'+target.name
    doc['images']=selected
    used=sorted({a['bufferView'] for a in doc['accessors']});mapping={old:new for new,old in enumerate(used)}
    packed=bytearray();views=[]
    for old in used:
        view=dict(doc['bufferViews'][old]);start=view.get('byteOffset',0)
        while len(packed)%4:packed.append(0)
        view['byteOffset']=len(packed);packed.extend(binary[start:start+view['byteLength']]);views.append(view)
    doc['bufferViews']=views
    for accessor in doc['accessors']:
        if accessor.get('sparse'):raise ValueError('Sparse accessors are unsupported')
        accessor['bufferView']=mapping[accessor['bufferView']]
    while len(packed)%4:packed.append(0)
    doc['buffers'][0]['byteLength']=len(packed)
    encoded=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    output=struct.pack('<III',magic,version,12+8+len(encoded)+8+len(packed))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(packed),0x004e4942)+packed
    path.write_bytes(output)
    manifest=path.with_name('scene.json');scene=json.loads(manifest.read_bytes())
    scene.update(glb_sha256=hashlib.sha256(output).hexdigest(),glb_bytes=len(output))
    scene['glb_external_images']=sorted({image['uri'] for image in selected})
    manifest.write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'model':path.name,'images':len(selected),'GLB_bytes_before':len(data),'GLB_bytes_after':len(output),'pixel_bytes_preserved':True}


def prepare_viewer(script):
    """Allow only this verified scene's explicitly listed, hashed shared PNGs."""
    source=script.read_text(encoding='utf-8')
    old="const manager=new THREE.LoadingManager();manager.setURLModifier(url=>{if(!url.startsWith('blob:')&&!url.startsWith('data:'))throw new Error('展示模型只能使用内嵌资源');return url;});"
    new="""const allowedImages=new Set((manifest.glb_external_images??[]).map(name=>{if(!/^\\.\\.\\/\\.\\.\\/shared\\/[a-f0-9]{64}\\.png$/.test(name))throw new Error('共享图片路径无效');return new URL(name,modelURL).href;}));
  const manager=new THREE.LoadingManager();manager.setURLModifier(url=>{if(url.startsWith('blob:')||url.startsWith('data:'))return url;const resolved=new URL(url,modelURL).href;if(allowedImages.has(resolved))return resolved;throw new Error('图片不在本场景的共享资源清单中');});"""
    if source.count(old)!=1 or source.count("parseAsync(data,'')")!=1:raise ValueError('Pinned renderer resource contract changed')
    source=source.replace(old,new).replace("parseAsync(data,'')","parseAsync(data,new URL('./',modelURL).href)")
    script.write_text(source,encoding='utf-8')
