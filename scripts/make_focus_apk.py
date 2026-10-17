import zipfile,pathlib
p=pathlib.Path('analysis/central-focus.apk')
with zipfile.ZipFile('others/TikTok_Central_v47.1.7_(MOD).apk') as src,zipfile.ZipFile(p,'w') as out:
 for n in ['AndroidManifest.xml','resources.arsc','classes33.dex','classes41.dex','classes42.dex']:
  out.writestr(n,src.read(n))
print(p)
