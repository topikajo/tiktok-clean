import json, pathlib, urllib.request
root=pathlib.Path.cwd()
headers={'User-Agent':'Codex-local-APK-analysis'}
for repo,kind in [('iBotPeaches/Apktool','apktool'),('skylot/jadx','jadx')]:
    data=json.load(urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers=headers)))
    (root/'analysis'/f'{kind}-release.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    assets=[a for a in data['assets'] if (kind=='apktool' and a['name'].endswith('.jar')) or (kind=='jadx' and a['name'].startswith('jadx-') and a['name'].endswith('.zip') and 'gui' not in a['name'])]
    for a in assets[:1]:
        dest=root/'tools'/a['name']
        if not dest.exists():
            urllib.request.urlretrieve(a['browser_download_url'],dest)
        print(kind, data['tag_name'], dest.name, dest.stat().st_size, flush=True)
        if kind=='jadx':
            import zipfile
            with zipfile.ZipFile(dest) as z:z.extractall(root/'tools'/'jadx')
for label,url in [('download','https://www.tiktok.com/download/en'),('download-mobile','https://www.tiktok.com/download')]:
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0.0.0 Mobile Safari/537.36'})
        with urllib.request.urlopen(req,timeout=30) as r:
            page=r.read()
            (root/'analysis'/f'{label}.html').write_bytes(page)
            print(label,r.status,r.url,len(page),flush=True)
    except Exception as e: print(label,type(e).__name__,str(e),flush=True)
