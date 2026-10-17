import zipfile,pathlib,json,struct
r={}
for p in list(pathlib.Path('others').glob('*.apk'))+list(pathlib.Path('originals').glob('*.apk')):
 with zipfile.ZipFile(p) as z:
  checks=[]
  for i in z.infolist():
   if not i.filename.startswith('lib/') or not i.filename.endswith('.so'):continue
   b=z.read(i)
   if b[:4]!=b'\x7fELF':continue
   elf64=b[4]==2
   off=struct.unpack_from('<Q' if elf64 else '<I',b,32 if elf64 else 28)[0]
   size,num=struct.unpack_from('<HH',b,54 if elf64 else 42)
   aligns=[]
   for j in range(num):
    h=off+j*size
    if struct.unpack_from('<I',b,h)[0]==1:aligns.append(struct.unpack_from('<Q' if elf64 else '<I',b,h+(48 if elf64 else 28))[0])
   if min(aligns,default=0)<16384:checks.append({'lib':i.filename,'load_alignments':aligns})
  r[p.name]=checks
 print(p.name,'ELF <16K',len(checks),'arm64 <16K',sum('arm64-v8a' in c['lib'] for c in checks),'examples',checks[:4],flush=True)
pathlib.Path('analysis/native-page-alignment.json').write_text(json.dumps(r,indent=2),encoding='utf8')
