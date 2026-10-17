import urllib.request,pathlib,json,re
headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'}
for url,name in [('https://www.tiktok.com/download/en','official-desktop'),('https://www.tiktok.com/download?lang=en','official-download'),('https://www.apkmirror.com/apk/tiktok-pte-ltd/tik-tok-including-musical-ly/','mirror-index')]:
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as r:
   data=r.read(); pathlib.Path('analysis',name+'.html').write_bytes(data)
   print(name,r.url,len(data),flush=True)
   text=data.decode('utf8','replace')
   links=re.findall(r'(?:https?[^\s<>"\x27]+(?:apk|download)[^\s<>"\x27]*|[^\s<>"\x27]+\.apk[^\s<>"\x27]*)',text)
   print('\n'.join(links[:30]),flush=True)
 except Exception as e:print(name,type(e).__name__,str(e),flush=True)
