"""Prepare an isolated Android 11 AVD with ARM32 translation using Google's checked SDK image."""
import argparse,hashlib,json,os,pathlib,shutil,time,urllib.request,xml.etree.ElementTree as ET,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
sdk=pathlib.Path(os.environ['LOCALAPPDATA'])/'Android/Sdk'
parser=argparse.ArgumentParser();parser.add_argument('--native-arm',action='store_true');parser.add_argument('--api',choices=['30','31'],default='30');args=parser.parse_args();native=args.native_arm
abi='armeabi-v7a' if native else 'x86_64';api='24' if native else args.api;tag='default' if native else 'google_apis'
avd_name='TikTokAuditArmNative' if native else 'TikTokAudit32' if api=='30' else 'TikTokAudit32Api31';serial='emulator-5584' if native else 'emulator-5582' if api=='30' else 'emulator-5586'
base='https://dl.google.com/android/repository/sys-img/'+('android' if native else 'google_apis')+'/'
xml=urllib.request.urlopen(base+'sys-img2-3.xml',timeout=30).read()
(root/('analysis/arm32-sys-img-native.xml' if native else 'analysis/arm32-sys-img-api'+api+'.xml')).write_bytes(xml)
node=next(n for n in ET.fromstring(xml).iter() if n.tag.endswith('remotePackage') and n.get('path')=='system-images;android-'+api+';'+tag+';'+abi)
complete=node.find('archives/archive/complete');url=base+complete.findtext('url');size=int(complete.findtext('size'));expected=complete.findtext('checksum')
cache=root/'tools/android-images';cache.mkdir(parents=True,exist_ok=True)
archive=cache/complete.findtext('url');part=archive.with_suffix('.zip.part')
def digest(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha1').hexdigest()
if not archive.exists():
 offset=part.stat().st_size if part.exists() else 0
 request=urllib.request.Request(url,headers={'Range':'bytes='+str(offset)+'-'} if offset else {})
 with urllib.request.urlopen(request,timeout=60) as source:
  append=source.status==206
  if not append:offset=0
  last=offset
  with part.open('ab' if append else 'wb') as output:
   while True:
    block=source.read(4*1024*1024)
    if not block:break
    output.write(block);offset+=len(block)
    if offset-last>=64*1024*1024:print(f'Google SDK image {offset}/{size} bytes',flush=True);last=offset
 assert part.stat().st_size==size and digest(part)==expected,'SDK image checksum mismatch'
 part.replace(archive)
assert archive.stat().st_size==size and digest(archive)==expected
image=sdk/'system-images'/('android-'+api)/tag/abi
if not (image/'source.properties').exists():
 assert not image.exists() or not any(image.iterdir()),'Existing SDK image directory is not empty'
 image.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   path=pathlib.PurePosixPath(item.filename)
   assert path.parts[0]==abi and '..' not in path.parts and not path.is_absolute(),item.filename
   if len(path.parts)==1:continue
   target=image.joinpath(*path.parts[1:]);assert target.resolve().is_relative_to(image.resolve())
   if item.is_dir():target.mkdir(parents=True,exist_ok=True)
   else:
    target.parent.mkdir(parents=True,exist_ok=True)
    with z.open(item) as source,target.open('wb') as output:shutil.copyfileobj(source,output,4*1024*1024)
avds=root/'analysis/avd';avd=avds/(avd_name+'.avd');avd.mkdir(parents=True,exist_ok=True)
config=dict(line.split('=',1) for line in (avds/'TikTokAudit.avd/config.ini').read_text().splitlines() if '=' in line)
config.update({'AvdId':avd_name,'avd.ini.displayname':avd_name+' Disposable','image.sysdir.1':str(image)+'/',
 'hw.cpu.arch':'arm' if native else 'x86_64','abi.type':abi,'hw.ramSize':'1536' if native else '3072','PlayStore.enabled':'false',
 'tag.id':tag,'tag.display':'Default' if native else 'Google APIs','hw.lcd.width':'720','hw.lcd.height':'1280','fastboot.forceColdBoot':'yes'})
if native:config.update({'hw.cpu.model':'cortex-a15','hw.cpu.ncore':'2','hw.lcd.density':'240'})
(avd/'config.ini').write_text('\n'.join(k+'='+v for k,v in config.items())+'\n')
(avds/(avd_name+'.ini')).write_text('avd.ini.encoding=UTF-8\npath='+str(avd.resolve())+'\ntarget=android-'+api+'\n')
(root/('analysis/arm32-image-native.json' if native else 'analysis/arm32-image-api'+api+'.json')).write_text(json.dumps({'url':url,'sha1':expected,'size':size,'image':str(image),'avd':avd_name,'serial':serial},indent=2),encoding='utf8')
print('Prepared '+avd_name+'; verify device abilist contains armeabi-v7a before testing',flush=True)
