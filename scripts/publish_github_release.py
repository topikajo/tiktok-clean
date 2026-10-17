"""Publish verified, versioned assets. Authentication stays in GitHub CLI/Desktop, never in the APK."""
import hashlib,json,pathlib,subprocess,urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
gh=root/'tools/gh/gh.exe';repo='topikajo/tiktok-clean'
def run(*args,check=True):
    result=subprocess.run(list(map(str,args)),cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8')
    if check and result.returncode:raise RuntimeError(result.stderr.strip())
    return result
def api(path):return json.loads(run(gh,'api',path).stdout)
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
assert not run('git','status','--porcelain').stdout.strip(),'Commit and push reviewed changes first'
assert run('git','remote','get-url','origin').stdout.strip()=='https://github.com/'+repo+'.git'
head=run('git','rev-parse','HEAD').stdout.strip()
remote=run('git','ls-remote','origin','refs/heads/main').stdout.split()[0];assert head==remote,'Push main through GitHub Desktop first'
feed=json.loads((root/'release/update.json').read_text(encoding='utf8'));tag='clean-'+str(feed['versionCode'])
folder=pathlib.Path((root/'analysis/public-release-path.txt').read_text(encoding='utf8').strip())
apk=folder/'TikTokClean-arm64.apk';assert sha(apk)==feed['sha256']
assert json.loads((folder/'update.json').read_text(encoding='utf8'))==feed
verification=json.loads((folder/'verification.json').read_text(encoding='utf8'));assert verification['apk_sha256']==feed['sha256'] and verification['normal_startup']['verified']
for path,expected in json.loads((folder/'build.json').read_text(encoding='utf8'))['helper_source_sha256'].items():assert sha(root/path)==expected
tag_ref=run('git','rev-parse','--verify','refs/tags/'+tag,check=False)
if tag_ref.returncode:
    run('git','tag','-a',tag,'-m','TikTok Clean '+str(feed['versionCode']))
assert run('git','rev-list','-n','1',tag).stdout.strip()==head,'Tag points to another commit'
run('git','push','origin','refs/tags/'+tag)
existing=run(gh,'api','repos/'+repo+'/releases/tags/'+tag,check=False)
if existing.returncode==0:
    release=json.loads(existing.stdout);assert release['draft'],'Published versions are immutable; increase VERSION'
else:
    run(gh,'release','create',tag,'--repo',repo,'--verify-tag','--draft','--title','TikTok Clean 46.8.3 · '+str(feed['versionCode']),'--notes-file',folder/'notes.md')
names=['TikTokClean-arm64.apk','update.json','SHA256SUMS.txt','build.json','verification.json','stress.json']
run(gh,'release','upload',tag,'--repo',repo,'--clobber',*[folder/name for name in names])
assets=api('repos/'+repo+'/releases/tags/'+tag)['assets'];remote_assets={a['name']:a for a in assets}
for name in names:
    a=remote_assets[name];assert a['size']==(folder/name).stat().st_size,name
    assert a.get('digest')=='sha256:'+sha(folder/name),'Uploaded digest mismatch: '+name
run(gh,'release','edit',tag,'--repo',repo,'--draft=false','--latest')
latest=api('repos/'+repo+'/releases/latest');assert latest['tag_name']==tag and not latest['draft']
url='https://github.com/'+repo+'/releases/latest/download/update.json'
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TikTokClean-release-check'}),timeout=60) as response:public=json.load(response)
assert public==feed,'Public latest feed mismatch'
assert next(a for a in latest['assets'] if a['name']=='TikTokClean-arm64.apk')['browser_download_url']==feed['apkUrls'][0]
print(json.dumps({'release':latest['html_url'],'apk':feed['apkUrls'][0],'feed':url,'sha256':feed['sha256'],'commit':head},indent=2))
