"""Prepare APK-only public releases and separate technical release assets."""
import hashlib,json,pathlib,re,shutil,zipfile

root=pathlib.Path(__file__).resolve().parents[1]
repo='topikajo/tiktok-clean'
APK_NAMES=('ttc-arm8.apk','ttc-arm64.apk')

def read(name):return json.loads((root/name).read_text(encoding='utf8'))
def sha(file):
    digest=hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def main():
    build=read('release/you-privacy-build.json');verified=read('release/you-privacy-verification.json');android=read('release/you-android-checks.json')
    apk=pathlib.Path(build['file']);digest=sha(apk);version=build['versionCode'];tag='clean-'+str(version);technical_tag='technical-'+str(version)
    assert digest==build['sha256']==verified['apk_sha256']==android['apk_sha256']
    assert verified['normal_startup']['verified'] and build['signature_verified'] and build['zip_16k_alignment_verified']
    assert version==int(re.search(r'^VERSION=(\d+)',(root/'scripts/build_you_privacy.py').read_text(encoding='utf8'),re.M)[1])
    for path,expected in {**build['helper_source_sha256'],**build['build_inputs_sha256']}.items():assert sha(root/path)==expected,path
    assert all(result['passed'] for result in android['results'].values())
    fixed=pathlib.Path((root/'analysis/stress/latest-fixed.txt').read_text(encoding='utf8').strip());baseline=pathlib.Path((root/'analysis/stress/latest-baseline.txt').read_text(encoding='utf8').strip())
    manifest=json.loads((fixed/'manifest.json').read_text());stress=json.loads((fixed/'jvm.json').read_text())
    assert manifest['exit_code']==0 and stress['sessions']>=100000 and stress['findings']==[]
    for path,expected in manifest['source_sha256'].items():assert build['helper_source_sha256']['src/mod/privacy/'+path]==expected,path
    update_text=(root/'analysis/you-update-results.txt').read_text(encoding='utf8');update_assertions=int(re.search(r'PASS (\d+)',update_text)[1]);assert update_assertions>=500212
    folder=root/'output/publish'/tag;folder.mkdir(parents=True,exist_ok=True)
    # ARMv8 and ARM64 are aliases for this arm64-v8a build, not separate ports.
    for name in APK_NAMES:
        shutil.copyfile(apk,folder/name);assert sha(folder/name)==digest,name
    # Carry the already checked, immutable ARMv7 binary into future consumer releases.
    # Its independent updater continues to use the URL/version of its own publication.
    carry_path=folder/'arm32-carry.json'
    if carry_path.exists():carry_path.unlink()
    arm32_note='ARMv7 / 32-битная версия пока недоступна.'
    if (root/'release/arm32-distribution.json').exists():
        arm32=read('release/arm32-distribution.json');arm32_build=read('release/arm32-build.json')
        source32=pathlib.Path(arm32_build['file'])
        assert sha(source32)==arm32['sha256']==arm32_build['sha256'] and source32.stat().st_size==arm32['size']
        assert arm32_build['abis']==['armeabi-v7a'] and arm32_build['signature_verified']
        with zipfile.ZipFile(source32) as archive:
            libs=[n for n in archive.namelist() if n.startswith('lib/') and not n.endswith('/')]
            assert libs and all(n.startswith('lib/armeabi-v7a/') for n in libs)
        for name in ('ttc-arm7.apk','ttc-arm32.apk'):shutil.copyfile(source32,folder/name)
        carry_path.write_text(json.dumps(arm32,indent=2)+'\n',encoding='utf8')
        arm32_note='Также доступны ttc-arm7.apk / ttc-arm32.apk — одна отдельная ARMv7 / 32-битная сборка на основе '+arm32['baseVersion']+'. **Экспериментальная, физический телефон не проверен.** Функции You, сохранение прошлого ролика и кадра в ARM32 отсутствуют. [Проверки ARM32](https://github.com/'+repo+'/releases/tag/'+arm32['technical_tag']+').'
    base=f'https://github.com/{repo}/releases/download/{tag}'
    feed={'packageName':'com.zhiliaoapp.musically','versionCode':version,'versionName':build['baseVersion']+' Clean '+str(version-2024608030),'sha256':digest,'apkUrls':[base+'/'+APK_NAMES[0]],
          'notes':'Короткие имена APK; технические файлы отделены от загрузок приложения. Обновления проверяются через отдельный канал.'}
    (root/'release/update.json').write_text(json.dumps(feed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    public_build={k:v for k,v in build.items() if k not in ('file','source','patch_directory')}
    public_build.update(file=APK_NAMES[0],aliases=list(APK_NAMES),abi='arm64-v8a',source='others/TikTok_You-4.4-(46.8.3).apk')
    public_verified=dict(verified)
    public_verified['normal_startup']={k:v for k,v in verified['normal_startup'].items() if k not in ('serial','pid')}
    load={'apk_sha256':digest,'versionCode':version,'baseline_model':json.loads((baseline/'jvm.json').read_text()),'fixed_model':stress,
          'installed_apk':android['results'],'jvm_update_assertions':update_assertions,
          'limits':['No real TikTok server load, GPU or video decoding benchmark','No physical Pixel/Poco or real account validation','Installed probes use a plain Application and a test-only bundled boot receiver']}
    baseline_log=(root/'analysis/you-android-stress-baseline.txt').read_text(encoding='utf8')
    load['installed_baseline']=json.loads(re.search(r'INSTRUMENTATION_RESULT: stress_json=(\{[^\r\n]+\})',baseline_log)[1])
    for name,data in [('build.json',public_build),('verification.json',public_verified),('stress.json',load)]:
        (folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    shutil.copyfile(root/'release/update.json',folder/'update.json')
    (root/'release/stress-results.json').write_text(json.dumps(load,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for name,data in [('you-privacy-build.json',public_build),('you-privacy-verification.json',public_verified)]:
        (folder/('public-'+name)).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (folder/'SHA256SUMS.txt').write_text(''.join(sha(folder/name)+'  '+name+'\n' for name in [*APK_NAMES,'update.json','build.json','verification.json','stress.json']),encoding='ascii')
    notes=f'''[Скачать ttc-arm8.apk]({base}/ttc-arm8.apk) · [Скачать ttc-arm64.apk]({base}/ttc-arm64.apk)

Оба файла — одна и та же сборка для **ARMv8 / ARM64 (arm64-v8a)**. Достаточно скачать любой один APK. {arm32_note}

TikTok Clean {build['baseVersion']} · сборка {version}. Обновление предлагается один раз; кнопка скачивания находится во «Входящих». После обновления ленты предыдущий ролик доступен одним обратным свайпом.

Канал обновлений вынесен отдельно. Сборку 2024608033 нужно один раз обновить вручную, чтобы перейти на новый адрес канала.

[Технические файлы, контрольные суммы и результаты проверок](https://github.com/{repo}/releases/tag/{technical_tag}). GitHub также автоматически показывает архивы исходников; для установки нужен только APK.
'''
    (folder/'notes.md').write_text(notes,encoding='utf8')
    technical_notes=f'''Технические файлы TikTok Clean · сборка {version}

Для установки приложения откройте [обычный релиз](https://github.com/{repo}/releases/tag/{tag}) и скачайте один APK. В этом техническом релизе находятся манифест обновления, SHA-256, данные сборки и результаты проверок.

Проверены {stress['sessions']:,} сценариев компонентов; количество операций и проверки установленного APK/обновлений приведены в stress.json. Модели нагрузки не измеряют FPS/GPU. Реальный вход, живая лента, физические Pixel/Poco, стикеры и кадр настоящего плеера пока не проверены.

Основа You 4.4 / {build['baseVersion']}; это не последняя официальная версия TikTok. Поддерживается arm64-v8a. Файлы ttc-arm8.apk и ttc-arm64.apk идентичны. APK подписан прежним локальным ключом Clean; ключ, токены и данные аккаунтов не публикуются.

Рабочий канал: https://raw.githubusercontent.com/{repo}/updates/update.json . Он обновляется отдельным техническим push только после проверки опубликованных APK.
'''
    (folder/'technical-notes.md').write_text(technical_notes,encoding='utf8')
    (root/'analysis/public-release-path.txt').write_text(str(folder),encoding='utf8')
    print(json.dumps({'folder':str(folder),'tag':tag,'technical_tag':technical_tag,'sha256':digest,'apk_bytes':apk.stat().st_size,'apk_names':APK_NAMES},indent=2))

if __name__=='__main__':main()
