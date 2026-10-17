"""Minimal binary manifest edits; resource IDs and all original string indices remain intact."""
import struct
from axml_add_service import NS,NO_INDEX,u32,length8,length16,len8,len16
from axml_version import set_version_code

REMOVE={
 'android.permission.SYSTEM_ALERT_WINDOW','android.permission.USE_FULL_SCREEN_INTENT',
 'android.permission.DETECT_SCREEN_RECORDING','android.permission.DETECT_SCREEN_CAPTURE',
 'android.permission.ACCESS_LOCAL_NETWORK','android.permission.CHANGE_WIFI_STATE',
 'android.permission.ACCESS_WIFI_STATE','android.permission.REORDER_TASKS',
 'android.permission.ACCESS_MEDIA_LOCATION','android.permission.READ_MEDIA_AUDIO',
 'android.permission.NFC','android.permission.SET_WALLPAPER','android.permission.USE_EXACT_ALARM',
 'com.android.launcher.permission.READ_SETTINGS','com.oplus.ocs.permission.third',
 'com.orange.update.permission.READ_ATTRIBUTION','com.samsung.android.mapsagent.permission.READ_APP_INFO',
 'com.tiktok.preload.permission.IDENTIFY','com.tiktok.manager.SYS_START_PERMISSION',
 'com.huawei.appmarket.service.commondata.permission.GET_COMMON_DATA',
 'com.google.android.gms.permission.AD_ID','android.permission.READ_PHONE_STATE',
 'android.permission.ACCESS_FINE_LOCATION','android.permission.ACCESS_COARSE_LOCATION',
 'com.zhiliao.musically.livewallpaper.permission.wallpaperplugin',
}
METADATA={'firebase_analytics_collection_deactivated':True,
 'firebase_analytics_collection_enabled':False,
 'google_analytics_adid_collection_enabled':False,
 'google_analytics_default_allow_ad_personalization_signals':False,
 'google_analytics_automatic_screen_reporting_enabled':False}

def patch(data,version):
 data=set_version_code(data,version);head=struct.unpack_from('<H',data,2)[0];off=head;chunks=[];strings=[];pool=None
 while off<len(data):
  kind,h,size=struct.unpack_from('<HHI',data,off);chunk=data[off:off+size];chunks.append([kind,chunk]);off+=size
  if kind==1:
   pool=len(chunks)-1;count,styles,flags,start,style_start=struct.unpack_from('<IIIII',chunk,8)
   offsets=list(struct.unpack_from('<'+'I'*count,chunk,h));meta=(h,count,styles,flags,start,style_start,offsets)
   for offset in offsets:
    pos=start+offset
    if flags&256:_,pos=length8(chunk,pos);n,pos=length8(chunk,pos);strings.append(chunk[pos:pos+n].decode('utf8'))
    else:n,pos=length16(chunk,pos);strings.append(chunk[pos:pos+n*2].decode('utf-16-le'))
 if off!=len(data) or pool is None:raise ValueError('Invalid AXML')
 def idx(s):
  if s not in strings:strings.append(s)
  return strings.index(s)
 for s in [NS,'meta-data','name','value','uses-permission','android.permission.REQUEST_INSTALL_PACKAGES','TikTok Clean',*METADATA]:idx(s)
 def attrs(c):
  start,stride,count=struct.unpack_from('<HHH',c,24)
  return [(16+start+i*stride,strings[u32(c,16+start+i*stride+4)]) for i in range(count)]
 def attr(c,name):
  for pos,n in attrs(c):
   if n==name:
    raw=u32(c,pos+8)
    return strings[raw] if raw!=NO_INDEX else None
  return None
 removed=[];kept=[];skip=0
 for kind,c in chunks:
  if skip:
   if kind==0x102:skip+=1
   elif kind==0x103:skip-=1
   continue
  if kind==0x102:
   tag=strings[u32(c,20)];name=attr(c,'name')
   if (tag in ('uses-permission','uses-permission-sdk-23') and name in REMOVE) or (tag=='meta-data' and name in METADATA):
    if tag.startswith('uses-permission'):removed.append(name)
    skip=1;continue
   # Give the fork its own launcher label, including aliases, without rebuilding resources.
   if tag in ('application','activity-alias'):
    c=bytearray(c)
    for pos,n in attrs(c):
     if n=='label':struct.pack_into('<I',c,pos+8,idx('TikTok Clean'));c[pos+15]=3;struct.pack_into('<I',c,pos+16,idx('TikTok Clean'))
    c=bytes(c)
  kept.append([kind,c])
 def node(tag,attributes):
  encoded=[]
  for name,value in attributes:
   if isinstance(value,bool):raw=NO_INDEX;typ=0x12;val=NO_INDEX if value else 0
   else:raw=idx(value);typ=3;val=raw
   encoded.append(struct.pack('<IIIHBBI',idx(NS),idx(name),raw,8,0,typ,val))
  return struct.pack('<HHIII',0x102,16,36+20*len(attributes),0,NO_INDEX)+struct.pack('<IIHHHHHH',NO_INDEX,idx(tag),20,20,len(attributes),0,0,0)+b''.join(encoded)+struct.pack('<HHIIIII',0x103,16,24,0,NO_INDEX,NO_INDEX,idx(tag))
 app_start=next(i for i,(k,c) in enumerate(kept) if k==0x102 and strings[u32(c,20)]=='application')
 if not any(k==0x102 and strings[u32(c,20)]=='uses-permission' and attr(c,'name')=='android.permission.REQUEST_INSTALL_PACKAGES' for k,c in kept):
  kept.insert(app_start,[0,node('uses-permission',[('name','android.permission.REQUEST_INSTALL_PACKAGES')])])
 app_end=next(i for i,(k,c) in enumerate(kept) if k==0x103 and strings[u32(c,20)]=='application')
 kept.insert(app_end,[0,b''.join(node('meta-data',[('name',k),('value',v)]) for k,v in METADATA.items())])
 old=chunks[pool][1];h,count,styles,flags,start,style_start,offsets=meta
 style_offsets=old[h+4*count:h+4*(count+styles)];blob=bytearray(old[start:style_start or len(old)])
 for s in strings[count:]:
  offsets.append(len(blob));n=len(s.encode('utf-16-le'))//2
  if flags&256:raw=s.encode('utf8');blob+=len8(n)+len8(len(raw))+raw+b'\0'
  else:blob+=len16(n)+s.encode('utf-16-le')+b'\0\0'
 while len(blob)%4:blob.append(0)
 new_start=h+4*(len(strings)+styles);new_style=new_start+len(blob) if styles else 0;style_data=old[style_start:] if style_start else b''
 pool_chunk=bytearray(old[:h]);struct.pack_into('<I',pool_chunk,4,new_start+len(blob)+len(style_data));struct.pack_into('<IIIII',pool_chunk,8,len(strings),styles,flags,new_start,new_style)
 pool_chunk+=struct.pack('<'+'I'*len(offsets),*offsets)+style_offsets+blob+style_data
 for item in kept:
  if item[0]==1:item[1]=bytes(pool_chunk)
 out=bytearray(data[:head])+b''.join(c for _,c in kept);struct.pack_into('<I',out,4,len(out))
 return bytes(out),removed
