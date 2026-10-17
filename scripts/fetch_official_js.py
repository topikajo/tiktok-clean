import pathlib,json,urllib.request,concurrent.futures,re
urls=json.loads(pathlib.Path('analysis/official-script-urls.json').read_text())
selected=[u for u in urls if 'download' in u or 'growth' in u or 'webapp-desktop.' in u]
print('selected',selected)
def fetch(u):
 try:
  b=urllib.request.urlopen(u,timeout=30).read(); p=pathlib.Path('analysis/official-js');p.mkdir(exist_ok=True);(p/u.split('/')[-1]).write_bytes(b)
  s=b.decode('utf8','replace');hits=[s[max(0,m.start()-100):m.start()+220] for m in re.finditer(r'\.apk|apkUrl|apk_url|download_url|downloadApk|download_apk|downloadAndroid',s,re.I)]
  print(u.split('/')[-1],len(b),'hits',hits[:12],flush=True)
 except Exception as e: print('ERROR',u.split('/')[-1],str(e),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as e:list(e.map(fetch,selected))
