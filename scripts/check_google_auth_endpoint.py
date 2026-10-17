"""Check the existing public Google browser route anonymously; never use account credentials."""
import urllib.request,urllib.parse,pathlib,json,hashlib,base64,re
client='616463764658-p01hhcj82u4mqjnp1oca04i3o67fjsm1.apps.googleusercontent.com'
redirect='com.googleusercontent.apps.616463764658-p01hhcj82u4mqjnp1oca04i3o67fjsm1:/oauthredirect'
verifier='local-route-probe-'+'a'*60
challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
query=urllib.parse.urlencode({'client_id':client,'redirect_uri':redirect,'response_type':'code','scope':'profile','state':'local-route-probe','code_challenge':challenge,'code_challenge_method':'S256'})
request=urllib.request.Request('https://accounts.google.com/o/oauth2/v2/auth?'+query,headers={'User-Agent':'Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36'})
result={'authenticated':False,'credentials_used':False}
try:
 with urllib.request.urlopen(request,timeout=25) as response:
  page=response.read().decode('utf8',errors='replace');url=urllib.parse.urlparse(response.url)
  title=re.search(r'<title>(.*?)</title>',page,re.S)
  result.update(status=response.status,final_host=url.hostname,final_path=url.path,title=title.group(1) if title else '',oauth_error_markers=sorted(set(re.findall(r'redirect_uri_mismatch|invalid_client|unauthorized_client|invalid_request|disallowed_useragent',page,re.I))))
except Exception as error:result['error']=type(error).__name__+': '+str(error)
pathlib.Path('analysis/google-browser-endpoint-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
