"""Add immutable genuine ARMv7 APK aliases, archive reports, then publish its independent feed."""
import hashlib,json,pathlib,subprocess
from publish_github_release import root,repo,gh,run,api,sha,find_release,ensure_tag,publish_assets,advance_feed,get_public_json
NAMES=('ttc-arm7.apk','ttc-arm32.apk')
TECH=('update-arm32.json','SHA256SUMS-arm32.txt','build-arm32.json','android-checks-arm32.json','startup-arm32.json')

def main():
    assert not run('git','status','--porcelain').stdout.strip(),'Commit and push reviewed source/reports first'
    head=run('git','rev-parse','HEAD').stdout.strip()
    assert run('git','ls-remote','origin','refs/heads/main').stdout.split()[0]==head,'Push main first'
    record=json.loads((root/'release/arm32-distribution.json').read_text(encoding='utf8'))
    folder=pathlib.Path((root/'analysis/arm32-public-release-path.txt').read_text(encoding='utf8').strip())
    assert folder.resolve()==(root/'output/publish'/record['technical_tag']).resolve()
    build=json.loads((folder/'build-arm32.json').read_text(encoding='utf8'))
    checks=json.loads((folder/'android-checks-arm32.json').read_text(encoding='utf8'))
    for name,expected in {**build['source_sha256s'],**checks['test_source_sha256']}.items():
        assert sha(root/name)==expected,name
        # Bind the published source tag to the exact bytes used to build.
        contents=subprocess.check_output(['git','show','HEAD:'+name],cwd=root)
        assert hashlib.sha256(contents).hexdigest()==expected,'Git source bytes differ: '+name
    for name in NAMES:assert sha(folder/name)==record['sha256'] and (folder/name).stat().st_size==record['size']
    feed=json.loads((folder/'update-arm32.json').read_text(encoding='utf8'))
    assert feed['sha256']==record['sha256'] and feed['versionCode']==record['versionCode']
    url='https://github.com/'+repo+'/releases/download/'+record['consumer_tag']+'/ttc-arm7.apk'
    assert feed['apkUrls']==[url]
    latest=api('repos/'+repo+'/releases/latest');assert latest['tag_name']==record['consumer_tag']
    assert not latest['draft'] and not latest['prerelease']
    arm64=json.loads((root/'release/update.json').read_text(encoding='utf8'))
    existing={a['name']:a for a in latest['assets']}
    assert set(existing)<=set(NAMES)|{'ttc-arm8.apk','ttc-arm64.apk'}
    for name in ('ttc-arm8.apk','ttc-arm64.apk'):assert existing[name]['digest']=='sha256:'+arm64['sha256'],name
    for name in NAMES:
        if name in existing:assert existing[name]['digest']=='sha256:'+record['sha256'] and existing[name]['size']==record['size'],'Published APK bytes are immutable'
    source=ensure_tag(record['technical_tag'],head)
    technical=publish_assets(record['technical_tag'],'Технические файлы · ARMv7 '+str(record['versionCode']),folder/'technical-notes.md',TECH,folder,True)
    # Make experimental status visible before the first ARMv7 download appears.
    run(gh,'release','edit',record['consumer_tag'],'--repo',repo,'--title','TikTok Clean · ARM64 и ARMv7','--notes-file',folder/'consumer-notes.md')
    missing=[folder/name for name in NAMES if name not in existing]
    if missing:run(gh,'release','upload',record['consumer_tag'],'--repo',repo,*missing)
    consumer=api('repos/'+repo+'/releases/'+str(latest['id']));assets={a['name']:a for a in consumer['assets']}
    assert set(assets)=={'ttc-arm8.apk','ttc-arm64.apk',*NAMES}
    for name in NAMES:assert assets[name]['digest']=='sha256:'+record['sha256'] and assets[name]['size']==record['size']
    for name in ('ttc-arm8.apk','ttc-arm64.apk'):assert assets[name]['digest']=='sha256:'+arm64['sha256']
    assert api('repos/'+repo+'/releases/latest')['tag_name']==record['consumer_tag']
    assert get_public_json('https://github.com/'+repo+'/releases/download/'+record['technical_tag']+'/update-arm32.json')==feed
    channel=advance_feed(feed,'update-arm32.json')
    assert get_public_json('https://raw.githubusercontent.com/'+repo+'/updates/update.json?commit='+channel)==arm64,'ARM64 channel must remain unchanged'
    print(json.dumps({'consumer':consumer['html_url'],'technical':technical['html_url'],'source_commit':source,'channel_commit':channel,'apk':url,'experimental':record['experimental']},indent=2))
if __name__=='__main__':main()
