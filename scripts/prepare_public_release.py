"""Gate public release assets on current-file checks; never includes a signing key or login token."""
import hashlib,json,pathlib,re,shutil
root=pathlib.Path(__file__).resolve().parents[1]
def read(name):return json.loads((root/name).read_text(encoding='utf8'))
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
build=read('release/you-privacy-build.json');verified=read('release/you-privacy-verification.json');android=read('release/you-android-checks.json')
apk=pathlib.Path(build['file']);digest=sha(apk);version=build['versionCode'];tag='clean-'+str(version)
assert digest==build['sha256']==verified['apk_sha256']==android['apk_sha256']
assert verified['normal_startup']['verified'] and build['signature_verified'] and build['zip_16k_alignment_verified']
assert version==int(re.search(r'^VERSION=(\d+)',(root/'scripts/build_you_privacy.py').read_text(encoding='utf8'),re.M)[1])
for path,expected in build['helper_source_sha256'].items():assert sha(root/path)==expected,path
assert all(result['passed'] for result in android['results'].values())
fixed=pathlib.Path((root/'analysis/stress/latest-fixed.txt').read_text(encoding='utf8').strip());baseline=pathlib.Path((root/'analysis/stress/latest-baseline.txt').read_text(encoding='utf8').strip())
manifest=json.loads((fixed/'manifest.json').read_text());stress=json.loads((fixed/'jvm.json').read_text())
assert manifest['exit_code']==0 and stress['sessions']>=100000 and stress['findings']==[]
for path,expected in manifest['source_sha256'].items():assert build['helper_source_sha256']['src/mod/privacy/'+path]==expected,path
update_text=(root/'analysis/you-update-results.txt').read_text(encoding='utf8');assert int(re.search(r'PASS (\d+)',update_text)[1])>=500212
folder=root/'output/publish'/tag;folder.mkdir(parents=True,exist_ok=True)
dest=folder/'TikTokClean-arm64.apk';shutil.copyfile(apk,dest);assert sha(dest)==digest
repo='topikajo/tiktok-clean';base=f'https://github.com/{repo}/releases/download/{tag}'
feed={'packageName':'com.zhiliaoapp.musically','versionCode':version,'versionName':build['baseVersion']+' Clean '+str(version-2024608030),'sha256':digest,'apkUrls':[base+'/'+dest.name],
      'notes':'Уведомление об обновлении один раз; точка во Входящих до проверенной загрузки. Устранены очередь UI и лишние поиски методов; исправлены крайние случаи обновления ленты.'}
(root/'release/update.json').write_text(json.dumps(feed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
public_build={k:v for k,v in build.items() if k not in ('file','source','patch_directory')}
public_build.update(file=dest.name,source='others/TikTok_You-4.4-(46.8.3).apk')
public_verified=dict(verified)
public_verified['normal_startup']={k:v for k,v in verified['normal_startup'].items() if k not in ('serial','pid')}
load={'apk_sha256':digest,'versionCode':version,'baseline_model':json.loads((baseline/'jvm.json').read_text()),'fixed_model':stress,
      'installed_apk':android['results'],'jvm_update_assertions':int(re.search(r'PASS (\d+)',update_text)[1]),
      'limits':['No real TikTok server load, GPU or video decoding benchmark','No physical Pixel/Poco or real account validation','Installed probes use a plain Application and a test-only bundled boot receiver']}
baseline_log=(root/'analysis/you-android-stress-baseline.txt').read_text(encoding='utf8')
load['installed_baseline']=json.loads(re.search(r'INSTRUMENTATION_RESULT: stress_json=(\{[^\r\n]+\})',baseline_log)[1])
for name,data in [('build.json',public_build),('verification.json',public_verified),('stress.json',load)]:
    (folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
shutil.copyfile(root/'release/update.json',folder/'update.json')
(root/'release/stress-results.json').write_text(json.dumps(load,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for name,data in [('you-privacy-build.json',public_build),('you-privacy-verification.json',public_verified)]:
    (folder/('public-'+name)).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(folder/'SHA256SUMS.txt').write_text(''.join(sha(folder/name)+'  '+name+'\n' for name in [dest.name,'update.json','build.json','verification.json','stress.json']),encoding='ascii')
notes=f'''TikTok Clean 46.8.3 · сборка {version}

- Один ненавязчивый баннер на новую версию; точка во «Входящих» остаётся до успешной проверенной загрузки. Кнопка «Скачать» там же, затем «Установить».
- Проверяются SHA-256, имя пакета, возрастающая версия и собственная подпись. Докачка поддерживается; установка запускается только по нажатию.
- Исправлены разрастание очереди UI, повторная рефлексия и два крайних случая сохранения прошлого ролика.
- 100 000 сценариев ленты / 10 547 751 операций, 100 000 циклов уведомлений; 30 проверок установленного APK, 20 проверок обновлений и Android-нагрузка прошли.

ARM64, основа You 4.4 / 46.8.3. Это не последняя официальная версия TikTok. Реальный вход, живая лента, физические Pixel/Poco, стикеры и кадр настоящего плеера пока не проверены. Модели нагрузки не являются проверкой FPS/GPU.

Один раз установите этот APK, чтобы включить опубликованный канал обновлений. Для прошлой сборки Clean этого профиля ключ сохранён; официальный TikTok/чужие моды имеют другую подпись. Перед удалением старого приложения сохраните черновики.
'''
(folder/'notes.md').write_text(notes,encoding='utf8')
(root/'analysis/public-release-path.txt').write_text(str(folder),encoding='utf8')
print(json.dumps({'folder':str(folder),'tag':tag,'sha256':digest,'apk_bytes':dest.stat().st_size},indent=2))
