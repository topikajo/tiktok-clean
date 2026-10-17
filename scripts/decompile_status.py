import pathlib,re
for kind in ['central','private','platinum']:
 ps=list(pathlib.Path('analysis/decompiled',kind).rglob('*.java'))
 print(kind,len(ps),[str(p) for p in ps[:5]])
