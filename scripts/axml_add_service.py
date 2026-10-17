"""Append an Android JobService and install-update permission without rebuilding resources."""
import struct

NO_INDEX=0xffffffff
NS='http://schemas.android.com/apk/res/android'
def u32(data,off):return struct.unpack_from('<I',data,off)[0]
def length8(data,off):
    n=data[off];off+=1
    if n&128:n=((n&127)<<8)|data[off];off+=1
    return n,off
def length16(data,off):
    n=struct.unpack_from('<H',data,off)[0];off+=2
    if n&32768:n=((n&32767)<<16)|struct.unpack_from('<H',data,off)[0];off+=2
    return n,off
def len8(n):return bytes([n]) if n<128 else bytes([128|(n>>8),n&255])
def len16(n):return struct.pack('<H',n) if n<32768 else struct.pack('<HH',32768|(n>>16),n&65535)

def add_service(data):
    if struct.unpack_from('<H',data)[0]!=3:raise ValueError('Expected binary Android XML')
    header=struct.unpack_from('<H',data,2)[0];chunks=[];off=header;strings=[];pool_at=None
    while off<len(data):
        kind,h,size=struct.unpack_from('<HHI',data,off)
        chunk=data[off:off+size];chunks.append([kind,chunk])
        if kind==1:
            pool_at=len(chunks)-1;count,styles,flags,start,style_start=struct.unpack_from('<IIIII',chunk,8)
            old_offsets=list(struct.unpack_from('<'+'I'*count,chunk,h))
            for offset in old_offsets:
                pos=start+offset
                if flags&256:
                    _,pos=length8(chunk,pos);n,pos=length8(chunk,pos);s=chunk[pos:pos+n].decode('utf8')
                else:n,pos=length16(chunk,pos);s=chunk[pos:pos+n*2].decode('utf-16-le')
                strings.append(s)
            pool_meta=(h,count,styles,flags,start,style_start,old_offsets)
        off+=size
    if off!=len(data) or pool_at is None:raise ValueError('Malformed AXML')
    def idx(s):
        if s not in strings:strings.append(s)
        return strings.index(s)
    for s in [NS,'service','uses-permission','application','name','permission','exported','mod.clean.StreakJob','android.permission.BIND_JOB_SERVICE','android.permission.REQUEST_INSTALL_PACKAGES']:idx(s)
    old=chunks[pool_at][1];h,count,styles,flags,start,style_start,offsets=pool_meta
    style_offsets=old[h+4*count:h+4*(count+styles)]
    string_data=bytearray(old[start:style_start or len(old)])
    for s in strings[count:]:
        offsets.append(len(string_data));utf16=len(s.encode('utf-16-le'))//2
        if flags&256:
            raw=s.encode('utf8');string_data+=len8(utf16)+len8(len(raw))+raw+b'\0'
        else:string_data+=len16(utf16)+s.encode('utf-16-le')+b'\0\0'
    while len(string_data)%4:string_data.append(0)
    new_start=h+4*(len(strings)+styles);new_style_start=new_start+len(string_data) if styles else 0
    style_data=old[style_start:] if style_start else b''
    new_size=new_start+len(string_data)+len(style_data)
    pool=bytearray(old[:h]);struct.pack_into('<I',pool,4,new_size);struct.pack_into('<IIIII',pool,8,len(strings),styles,flags,new_start,new_style_start)
    pool+=struct.pack('<'+'I'*len(offsets),*offsets)+style_offsets+string_data+style_data
    chunks[pool_at][1]=bytes(pool)
    def start_node(name,attrs):
        encoded=[]
        for attr,value in attrs:
            if isinstance(value,bool):raw=NO_INDEX;typ=0x12;value_data=NO_INDEX if value else 0
            else:raw=idx(value);typ=3;value_data=raw
            encoded.append(struct.pack('<IIIHBBI',idx(NS),idx(attr),raw,8,0,typ,value_data))
        return struct.pack('<HHIII',0x102,16,36+20*len(attrs),0,NO_INDEX)+struct.pack('<IIHHHHHH',NO_INDEX,idx(name),20,20,len(attrs),0,0,0)+b''.join(encoded)
    def end_node(name):return struct.pack('<HHIIIII',0x103,16,24,0,NO_INDEX,NO_INDEX,idx(name))
    app_end=[];app_start=[]
    permission_present=False
    for i,(kind,chunk) in enumerate(chunks):
        if kind in [0x102,0x103] and strings[u32(chunk,20)]=='application':(app_start if kind==0x102 else app_end).append(i)
        if kind==0x102 and strings[u32(chunk,20)]=='uses-permission':
            atr_start,atr_size,atr_count=struct.unpack_from('<HHH',chunk,24)
            for j in range(atr_count):
                pos=16+atr_start+j*atr_size;name=strings[u32(chunk,pos+4)];raw=u32(chunk,pos+8)
                if name=='name' and raw!=NO_INDEX and strings[raw]=='android.permission.REQUEST_INSTALL_PACKAGES':permission_present=True
    if len(app_end)!=1 or len(app_start)!=1:raise ValueError('Unexpected application nodes')
    service=start_node('service',[('name','mod.clean.StreakJob'),('permission','android.permission.BIND_JOB_SERVICE'),('exported',True)])+end_node('service')
    chunks.insert(app_end[0],[0,service])
    if not permission_present:
        permission=start_node('uses-permission',[('name','android.permission.REQUEST_INSTALL_PACKAGES')])+end_node('uses-permission')
        chunks.insert(app_start[0],[0,permission])
    out=bytearray(data[:header])+b''.join(chunk for kind,chunk in chunks);struct.pack_into('<I',out,4,len(out))
    return bytes(out)
