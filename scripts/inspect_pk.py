import pathlib,re
p=next(pathlib.Path('analysis/integration-java').glob('*_pk.java'));s=p.read_text(encoding='utf8')
print('pk lines',len(s.splitlines()))
for i,line in enumerate(s.splitlines(),1):
 if re.search(r'(?i)(cert|sign|update|emergen|авар|обнов|https|version|void [a-z]+\()',line):print(i,line[:300])
print('\n'.join(s.splitlines()[:48]))
