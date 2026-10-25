from pathlib import Path
import hashlib
import json
import subprocess

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'site/previews.json').read_text(encoding='utf-8'))
def download(asset,expected,filename):
    if type(asset) is not int or asset<=0:raise ValueError('A pinned Release asset is required')
    if Path(filename).name!=filename or not filename.endswith('.zip'):raise ValueError('Unsafe download filename')
    target=root/filename
    with target.open('xb') as output:
        subprocess.run(['gh','api','-H','Accept: application/octet-stream',f'repos/IcyRyna/war-thunder-liveries/releases/assets/{asset}'],stdout=output,check=True)
    h=hashlib.sha256()
    with target.open('rb') as source:
        for block in iter(lambda:source.read(1048576),b''):h.update(block)
    if h.hexdigest()!=expected:raise ValueError('Downloaded archive does not match its pinned SHA-256')
    return target.stat().st_size

size=download(manifest['asset_id'],manifest['bundle_sha256'],'previews.zip')
for archive in manifest.get('supplementary_archives',[]):
    size+=download(archive['asset_id'],archive['sha256'],archive['filename'])
print(json.dumps({'preview_assets_verified':True,'bytes':size}))
