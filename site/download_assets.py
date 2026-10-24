from pathlib import Path
import hashlib
import json
import subprocess

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'site/previews.json').read_text(encoding='utf-8'))
asset=manifest['asset_id']
if type(asset) is not int or asset<=0:raise ValueError('A pinned preview Release asset is required')
target=root/'previews.zip'
with target.open('xb') as output:
    subprocess.run(['gh','api','-H','Accept: application/octet-stream',f'repos/IcyRyna/war-thunder-liveries/releases/assets/{asset}'],stdout=output,check=True)
h=hashlib.sha256()
with target.open('rb') as source:
    for block in iter(lambda:source.read(1048576),b''):h.update(block)
if h.hexdigest()!=manifest['bundle_sha256']:raise ValueError('Downloaded preview archive does not match the pinned SHA-256')
print(json.dumps({'preview_assets_verified':True,'bytes':target.stat().st_size}))
