"""Publish APK-only releases, separate technical assets, then advance the public feed."""
import hashlib,json,pathlib,subprocess,time,urllib.error,urllib.request

root=pathlib.Path(__file__).resolve().parents[1]
gh=root/'tools/gh/gh.exe';repo='topikajo/tiktok-clean'
APK_NAMES=('ttc-arm8.apk','ttc-arm64.apk')
TECHNICAL_NAMES=('update.json','SHA256SUMS.txt','build.json','verification.json','stress.json')
FEED_URL='https://raw.githubusercontent.com/'+repo+'/updates/update.json'

def run(*args,check=True,cwd=None):
    result=subprocess.run(list(map(str,args)),cwd=cwd or root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8')
    if check and result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result

def api(path,*args):return json.loads(run(gh,'api',path,*args).stdout)

def sha(file):
    digest=hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def find_release(tag):
    result=run(gh,'api','repos/'+repo+'/releases/tags/'+tag,check=False)
    if result.returncode==0:return json.loads(result.stdout)
    if 'HTTP 404' not in result.stderr:raise RuntimeError(result.stderr.strip())
    # Authenticated lists include drafts, unlike the public by-tag endpoint.
    pages=api('repos/'+repo+'/releases?per_page=100','--paginate','--slurp')
    return next((release for page in pages for release in page if release['tag_name']==tag),None)

def ensure_tag(tag,head):
    tag_ref=run('git','rev-parse','--verify','refs/tags/'+tag,check=False)
    if tag_ref.returncode:run('git','tag','-a',tag,'-m','TikTok Clean '+tag)
    commit=run('git','rev-list','-n','1',tag).stdout.strip()
    if commit!=head:
        # Resume a draft after correcting the publisher without altering APK sources.
        changed=set(run('git','diff','--name-only',tag,head).stdout.splitlines())
        assert changed<={'scripts/publish_github_release.py'},'Tag points to different APK source'
    run('git','push','origin','refs/tags/'+tag)
    return commit

def verify_assets(release,names,folder):
    assets={asset['name']:asset for asset in release['assets']}
    assert set(assets)==set(names),'Unexpected or missing release assets: '+release['tag_name']
    for name in names:
        assert assets[name]['size']==(folder/name).stat().st_size,name
        assert assets[name].get('digest')=='sha256:'+sha(folder/name),'Uploaded digest mismatch: '+name
    return assets

def publish_assets(tag,title,notes,names,folder,technical):
    release=find_release(tag)
    if release is None:
        args=[gh,'release','create',tag,'--repo',repo,'--verify-tag','--draft','--title',title,'--notes-file',notes,'--latest=false']
        if technical:args.append('--prerelease')
        run(*args)
        # A newly created draft can briefly be absent from the release list.
        for delay in (0,1,2,4,8):
            if delay:time.sleep(delay)
            release=find_release(tag)
            if release is not None:break
        assert release is not None,'Created draft is not yet visible; retry safely'
    assert release['prerelease']==technical,'Existing release has the wrong role'
    if release['draft']:
        # Only unpublished drafts may be repaired or have an asset replaced.
        assets={asset['name']:asset for asset in release['assets']}
        assert set(assets)<=set(names),'Remove unexpected draft assets explicitly before publishing'
        upload=[name for name in names if name not in assets or assets[name].get('digest')!='sha256:'+sha(folder/name)]
        if upload:
            print('Uploading '+tag+': '+', '.join(upload),flush=True)
            run(gh,'release','upload',tag,'--repo',repo,'--clobber',*[folder/name for name in upload])
        release=api('repos/'+repo+'/releases/'+str(release['id']));verify_assets(release,names,folder)
        run(gh,'release','edit',tag,'--repo',repo,'--title',title,'--notes-file',notes,'--draft=false','--latest=false' if technical else '--latest')
    # Published assets are never replaced. A retry may only verify and continue.
    release=api('repos/'+repo+'/releases/'+str(release['id']))
    assert not release['draft'] and release['prerelease']==technical
    verify_assets(release,names,folder)
    return release

def get_public_json(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TikTokClean-release-check','Cache-Control':'no-cache'}),timeout=30) as response:return json.load(response)

def advance_feed(feed):
    """Use an isolated checkout; never switch or rewrite the GitHub Desktop worktree."""
    checkout=root/'tools/update-channel';origin='https://github.com/'+repo+'.git'
    checkout.mkdir(parents=True,exist_ok=True)
    def git(*args,check=True):return run('git',*args,check=check,cwd=checkout)
    if not (checkout/'.git').exists():
        assert not any(checkout.iterdir()),'Channel directory contains unrelated files'
        git('init','-b','updates');git('remote','add','origin',origin)
    assert git('rev-parse','--show-toplevel').stdout.strip().replace('\\','/').lower()==str(checkout).replace('\\','/').lower()
    assert git('remote','get-url','origin').stdout.strip()==origin
    assert git('symbolic-ref','--short','HEAD').stdout.strip()=='updates','Unexpected channel branch'
    assert not git('status','--porcelain').stdout.strip(),'Resolve pending channel work before publishing'
    assert set(git('ls-files').stdout.splitlines())<={'update.json','README.md'},'Unexpected files in the channel checkout'
    name=run('git','config','user.name').stdout.strip();email=run('git','config','user.email').stdout.strip()
    assert name and email,'Configure the Git author in the main checkout first'
    git('config','user.name',name);git('config','user.email',email)
    remote=git('ls-remote','--heads','origin','refs/heads/updates').stdout.strip()
    has_head=git('rev-parse','--verify','HEAD',check=False).returncode==0
    if remote:
        git('fetch','origin','refs/heads/updates:refs/remotes/origin/updates')
        if has_head:git('merge','--ff-only','refs/remotes/origin/updates')
        else:git('switch','-C','updates','refs/remotes/origin/updates')
    assert set(git('ls-files').stdout.splitlines())<={'update.json','README.md'},'Unexpected remote channel contents'
    assert not git('status','--porcelain').stdout.strip(),'Channel checkout changed during synchronization'
    # The first channel commit is orphaned; source history is not copied here.
    target=checkout/'update.json'
    if target.exists():
        before=json.loads(target.read_text(encoding='utf8'))
        assert before['versionCode']<=feed['versionCode'],'Refusing to roll back the update channel'
        if before['versionCode']==feed['versionCode']:assert before==feed,'Published version metadata changed'
    target.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    readme=checkout/'README.md'
    if not readme.exists():readme.write_text('Public TikTok Clean update channel.\n\nOnly update.json is consumed by the application. APKs and user downloads are published in the main repository Releases; no credentials or signing keys belong in this branch.\n',encoding='utf8')
    git('add','--','update.json','README.md')
    staged=git('diff','--cached','--quiet',check=False)
    assert staged.returncode in (0,1),'Cannot inspect the channel index'
    if staged.returncode:git('commit','-m','Update channel to Clean '+str(feed['versionCode']))
    commit=git('rev-parse','HEAD').stdout.strip()
    git('push','origin','HEAD:refs/heads/updates')
    remote_commit=git('ls-remote','--heads','origin','refs/heads/updates').stdout.split()[0]
    assert remote_commit==commit,'Channel push did not publish the expected commit'
    assert get_public_json('https://raw.githubusercontent.com/'+repo+'/'+commit+'/update.json')==feed
    failure=None
    for delay in (0,1,2,4,8,16):
        if delay:time.sleep(delay)
        try:
            if get_public_json(FEED_URL+'?commit='+commit)==feed:return commit
            failure=RuntimeError('Public channel still serves a previous manifest')
        except (urllib.error.URLError,ValueError) as error:failure=error
    raise RuntimeError('Channel pushed but its public endpoint could not be verified') from failure

def main():
    assert not run('git','status','--porcelain').stdout.strip(),'Commit and push reviewed changes first'
    assert run('git','remote','get-url','origin').stdout.strip()=='https://github.com/'+repo+'.git'
    head=run('git','rev-parse','HEAD').stdout.strip()
    remote=run('git','ls-remote','origin','refs/heads/main').stdout.split()[0];assert head==remote,'Push main through GitHub Desktop first'
    feed=json.loads((root/'release/update.json').read_text(encoding='utf8'));tag='clean-'+str(feed['versionCode']);technical_tag='technical-'+str(feed['versionCode'])
    folder=pathlib.Path((root/'analysis/public-release-path.txt').read_text(encoding='utf8').strip())
    assert folder.resolve()==(root/'output/publish'/tag).resolve(),'Unexpected prepared release folder'
    for name in APK_NAMES:assert sha(folder/name)==feed['sha256'],name
    assert feed['apkUrls']==['https://github.com/'+repo+'/releases/download/'+tag+'/'+APK_NAMES[0]]
    assert json.loads((folder/'update.json').read_text(encoding='utf8'))==feed
    verification=json.loads((folder/'verification.json').read_text(encoding='utf8'));assert verification['apk_sha256']==feed['sha256'] and verification['normal_startup']['verified']
    build=json.loads((folder/'build.json').read_text(encoding='utf8'));assert build['sha256']==feed['sha256'] and build['versionCode']==feed['versionCode']
    for path,expected in {**build['helper_source_sha256'],**build['build_inputs_sha256']}.items():assert sha(root/path)==expected
    source_commit=ensure_tag(tag,head);assert ensure_tag(technical_tag,head)==source_commit
    technical=publish_assets(technical_tag,'Технические файлы · '+str(feed['versionCode']),folder/'technical-notes.md',TECHNICAL_NAMES,folder,True)
    consumer=publish_assets(tag,'TikTok Clean '+build['baseVersion']+' · '+str(feed['versionCode']),folder/'notes.md',APK_NAMES,folder,False)
    latest=api('repos/'+repo+'/releases/latest');assert latest['tag_name']==tag and not latest['draft'] and not latest['prerelease'],'Another release became latest; the channel was not advanced'
    assets=verify_assets(latest,APK_NAMES,folder);assert assets[APK_NAMES[0]]['browser_download_url']==feed['apkUrls'][0]
    assert get_public_json('https://github.com/'+repo+'/releases/download/'+technical_tag+'/update.json')==feed
    channel_commit=advance_feed(feed)
    print(json.dumps({'release':consumer['html_url'],'technical':technical['html_url'],'apk':feed['apkUrls'][0],'feed':FEED_URL,'sha256':feed['sha256'],'commit':source_commit,'channel_commit':channel_commit},indent=2))

if __name__=='__main__':main()
