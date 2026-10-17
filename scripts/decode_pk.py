import pathlib,re
p=next(pathlib.Path('analysis/integration-java').glob('*_pk.java'));s=p.read_text(encoding='utf8')
for m in re.finditer(r'return new float\[\]\{([^}]+)\}',s):
 try: print('decoded:', ''.join(chr(round(float(v.strip().rstrip('f'))*4)) for v in m.group(1).split(',')))
 except Exception:pass
print('\n'.join(s.splitlines()[145:216]))
