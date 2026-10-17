import pathlib,re,json
p=pathlib.Path('analysis/official-desktop.html').read_text(encoding='utf-8')
m=re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',p)
d=json.loads(m.group(1)); pathlib.Path('analysis/official-page-state.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
print('scope',list(d['__DEFAULT_SCOPE__']))
for k,v in d['__DEFAULT_SCOPE__'].items():
 if 'download' in k:print(k,json.dumps(v)[:5000])
urls=re.findall(r'<script[^>]*src="([^"]+)"',p)
print('\n'.join(u for u in urls if 'download' in u or 'webapp' in u))
pathlib.Path('analysis/official-script-urls.json').write_text(json.dumps(urls),encoding='utf-8')
