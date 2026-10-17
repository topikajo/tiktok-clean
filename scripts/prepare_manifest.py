import zipfile,pathlib,json
from axml_add_service import add_service
from axml_version import set_version_code
with zipfile.ZipFile('originals/TikTok_47.1.4_original_apkpure.apk') as z:
 manifest=add_service(z.read('AndroidManifest.xml'))
 plan=json.loads(pathlib.Path('analysis/build-plan.json').read_text(encoding='utf8'))
 if plan.get('original_version_code'):manifest=set_version_code(manifest,plan['original_version_code'])
 with zipfile.ZipFile('analysis/manifest-check.apk','w') as out:out.writestr('AndroidManifest.xml',manifest)
 pathlib.Path('analysis/clean-manifest.axml').write_bytes(manifest)
