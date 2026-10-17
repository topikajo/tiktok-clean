import zipfile
with zipfile.ZipFile('tools/apktool_3.0.3.jar') as z:
 print('\n'.join(n for n in z.namelist() if 'smali' in n and ('Main.class' in n or 'cli/' in n or 'Smali.class' in n)))
