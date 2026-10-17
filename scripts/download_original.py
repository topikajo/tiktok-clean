import pathlib,urllib.request,json,time
url='https://d-ru.apkpure.net/b/APK/com.zhiliaoapp.musically?versionCode=2024701040&nc=arm64-v8a%2Carmeabi-v7a&sv=23'
p=pathlib.Path('originals/TikTok_47.1.4_original_apkpure.apk')
req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://apkpure.net/tiktok-app/com.zhiliaoapp.musically/download'})
try:
 with urllib.request.urlopen(req,timeout=30) as r,p.with_suffix('.apk.part').open('wb') as f:
  meta={'url':url,'final_url':r.url,'headers':dict(r.headers),'catalog_version':'47.1.4','catalog_certificate_sha1':'d79f7cb8509a5e7e71c4f2afcfb75ea8c87177ca','catalog_sha256':'4226ed5d3031b68208c29f62d80ac421b281fc74201bc4163d98e442d0991a40'}
  pathlib.Path('analysis/original-acquisition.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
  print(r.status,r.headers.get('Content-Length'),r.headers.get('Content-Type'),flush=True)
  total=0;last=0
  while b:=r.read(1024*1024):
   f.write(b);total+=len(b)
   if total-last>=50*1024*1024:print(total,flush=True);last=total
 p.with_suffix('.apk.part').replace(p)
 print('Downloaded',p,p.stat().st_size,flush=True)
except Exception as e:print(type(e).__name__,str(e),flush=True)
