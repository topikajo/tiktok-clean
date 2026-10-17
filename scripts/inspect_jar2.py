import zipfile,collections
with zipfile.ZipFile('tools/apktool_3.0.3.jar') as z:
 ns=z.namelist();print(ns[:35]);print([n for n in ns if n.endswith('.jar')]);print([n for n in ns if 'smali' in n][:15])
