package mod.privacy;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;

/** Exercise real transport bytes, interrupted downloads, notice lifetime and reflection overloads. */
public final class PrivacyUpdateTest {
    static ArrayDeque<Fake> replies=new ArrayDeque<Fake>();static Fake last;static int cases;
    static class Fake extends HttpURLConnection {
        final int status;final byte[] body;final int length;final String range,location;
        Fake(int s,String b,int n,String r,String l)throws Exception{super(new URL("https://fixture/"));status=s;body=b.getBytes("UTF-8");length=n;range=r;location=l;}
        public void connect(){} public void disconnect(){}public boolean usingProxy(){return false;}
        public int getResponseCode(){return status;}
        public String getHeaderField(String key){return key.equals("Content-Range")?range:key.equals("Location")?location:null;}
        public int getContentLength(){return length;}
        public InputStream getInputStream(){return new ByteArrayInputStream(body);}
    }
    public static class Overloads {
        public String pick(String v){return "instance";}
        public static String pick(Object v){return "static";}
        public String number(int n){return "int";}
        public String number(long n){return "long";}
        public String nullable(Object v){return "object";}
        public String nullable(String v){return "string";}
        public String ambiguous(String v){return "string";}
        public String ambiguous(Integer v){return "integer";}
    }
    static void check(boolean c,String s){if(!c)throw new AssertionError(s);cases++;}
    static String read(File p)throws Exception{return new String(Files.readAllBytes(p.toPath()),"UTF-8");}
    static void fail(File p)throws Exception{try{UpdateChannel.transfer("https://fixture/apk",p);throw new AssertionError("expected transport error");}catch(IOException expected){cases++;}}
    public static void main(String[] args)throws Exception {
        URL.setURLStreamHandlerFactory(new URLStreamHandlerFactory(){public URLStreamHandler createURLStreamHandler(String protocol){return protocol.equals("https")?new URLStreamHandler(){protected URLConnection openConnection(URL u){last=replies.remove();return last;}}:null;}});
        Path dir=Files.createTempDirectory("clean-update-transport-");File part=dir.resolve("update.part").toFile();
        try {
            replies.add(new Fake(200,"abc",6,null,null));fail(part);check(read(part).equals("abc"),"interrupted bytes retained");
            replies.add(new Fake(206,"def",3,"bytes 3-5/6",null));UpdateChannel.transfer("https://fixture/apk",part);check(read(part).equals("abcdef")&&last.getRequestProperty("Range").equals("bytes=3-"),"resume exact offset");
            replies.add(new Fake(200,"new",3,null,null));UpdateChannel.transfer("https://fixture/apk",part);check(read(part).equals("new"),"ignored Range restarts");
            replies.add(new Fake(206,"bad",3,"bytes 1-3/4",null));fail(part);check(read(part).equals("new"),"bad Range keeps prefix");
            replies.add(new Fake(302,"",0,null,"http://fixture/apk"));fail(part);
            replies.add(new Fake(416,"",0,null,null));UpdateChannel.transfer("https://fixture/apk",part);check(read(part).equals("new"),"416 keeps file for verification");
            replies.add(new Fake(302,"",0,null,"https://fixture/new"));replies.add(new Fake(200,"ok",2,null,null));UpdateChannel.transfer("https://fixture/apk",part);check(read(part).equals("ok"),"HTTPS redirect");
            Random random=new Random(1732311L);
            for(int i=0;i<100000;i++) {
                long installed=1+random.nextInt(100),version=installed+1+random.nextInt(50);
                check(UpdatePolicy.prompt(installed,version,version-1,0,false),"new version offered");
                check(!UpdatePolicy.prompt(installed,version,version,0,false)&&UpdatePolicy.pending(installed,version,0,false),"dismissed offer leaves dot");
                check(UpdatePolicy.pending(installed,version,version,false),"missing/failed download keeps dot");
                check(!UpdatePolicy.pending(installed,version,version,true),"verified download clears dot");
                check(!UpdatePolicy.pending(version,version,0,false),"installed release clears dot");
            }
            Overloads o=new Overloads();
            for(int i=0;i<100;i++) {
                check("instance".equals(CachedReflect.call(o,"pick","v")),"instance overload");
                check("static".equals(CachedReflect.call(Overloads.class,"pick","v")),"static cache isolated");
            }
            check("int".equals(CachedReflect.call(o,"number",3)),"primitive overload");
            check("string".equals(CachedReflect.call(o,"nullable",new Object[]{null})),"most specific null overload");
            try{CachedReflect.call(o,"ambiguous",new Object[]{null});throw new AssertionError("ambiguous accepted");}catch(NoSuchMethodException expected){cases++;}
            System.out.println("PASS "+cases+" update/transport/reflection assertions; 100000 notice lifecycles; no network");
        }finally{Files.deleteIfExists(part.toPath());Files.deleteIfExists(dir);}
    }
}
