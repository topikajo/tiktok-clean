import zipfile,pathlib
for name in ['TikTok_Central_v47.1.7_(MOD)','TikTok_Platinum_v47.1.7_(MOD)_arm8','TikTok_Private_Plus_v47.1.7_(MOD)_arm8']:
 with zipfile.ZipFile(pathlib.Path('others',name+'.apk')) as z:
  print(name)
  for n in z.namelist():
   if n.startswith('assets/') and ('prime' in n.lower() or 'gold' in n.lower() or 'metadata.txt' in n):
    d=z.read(n);print(n,len(d),d[:1500] if len(d)<2000 else '')
  for n in z.namelist():
   if n.startswith('lib/') and any(t in n.lower() for t in ['prime','gold','jaggu','native-lib','dex','nmmp','protect']): print(n,z.getinfo(n).file_size)
