import zipfile,pathlib
with zipfile.ZipFile('others/TikTok_Central_v47.1.7_(MOD).apk') as src,zipfile.ZipFile('analysis/central-focus-v2.apk','w') as out:
 for n in ['AndroidManifest.xml','resources.arsc','classes.dex','classes33.dex','classes41.dex','classes42.dex']:out.writestr(n,src.read(n))
print('wrote central focus with primary dex')
with zipfile.ZipFile('tools/jadx/lib/jadx-1.5.6-all.jar') as z:print([n for n in z.namelist() if 'DexFileFactory.class' in n or n.endswith('baksmali/Main.class') or n.endswith('smali/Smali.class')])
