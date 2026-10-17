import zipfile,pathlib,json
for p in pathlib.Path('others').glob('*.apk'):
 with zipfile.ZipFile(p) as z:
  dex=[(i.filename,i.file_size,i.CRC) for i in z.infolist() if i.filename.endswith('.dex')]
  libs=[(i.filename,i.file_size) for i in z.infolist() if i.filename.startswith('lib/')]
  assets=[(i.filename,i.file_size) for i in z.infolist() if i.filename.startswith('assets/') and ('mod' in i.filename.lower() or 'ad' in i.filename.lower() or i.file_size>20000000)]
  print(json.dumps({'name':p.name,'entries':len(z.infolist()),'dex':dex,'abis':sorted({n.split('/')[1] for n,s in libs}),'large_or_mod_assets':assets,'lib_count':len(libs)},ensure_ascii=False))
