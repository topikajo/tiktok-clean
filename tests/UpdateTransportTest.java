package mod.clean;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;

/** Test the production download transport with deterministic HTTP responses, no network. */
public final class UpdateTransportTest {
    static ArrayDeque<Fake> replies=new ArrayDeque<>();static Fake last;static int cases;
    static class Fake extends HttpURLConnection {
        final int status;final byte[] body;final long length;final String range,location;
        Fake(int s,String b,long n,String r,String l)throws Exception{super(new URL("https://fixture/"));status=s;body=b.getBytes("UTF-8");length=n;range=r;location=l;}
        public void connect(){} public void disconnect(){}public boolean usingProxy(){return false;}
        public int getResponseCode(){return status;}
        public String getHeaderField(String key){return key.equals("Content-Range")?range:key.equals("Location")?location:null;}
        public int getContentLength(){return (int)length;}
        public InputStream getInputStream(){return new ByteArrayInputStream(body);}
    }
    static void check(boolean c,String s){if(!c)throw new AssertionError(s);cases++;}
    static String read(File p)throws Exception{return new String(Files.readAllBytes(p.toPath()),"UTF-8");}
    static void fail(File p)throws Exception{try{UpdateChannel.transfer("https://fixture/apk",p);throw new AssertionError("expected transport error");}catch(IOException expected){cases++;}}
    public static void main(String[] args)throws Exception{
        URL.setURLStreamHandlerFactory(new URLStreamHandlerFactory(){public URLStreamHandler createURLStreamHandler(String protocol){return protocol.equals("https")?new URLStreamHandler(){protected URLConnection openConnection(URL u){last=replies.remove();return last;}}:null;}});
        Path dir=Files.createTempDirectory("clean-update-transport-");File part=dir.resolve("update.part").toFile();
        try{
            replies.add(new Fake(200,"abc",6,null,null));fail(part);check(read(part).equals("abc"),"interrupted transfer retained");
            replies.add(new Fake(206,"def",3,"bytes 3-5/6",null));UpdateChannel.transfer("https://fixture/apk",part);check(read(part).equals("abcdef")&&last.getRequestProperty("Range").equals("bytes=3-"),"resume preserves prefix and requests exact offset");
            replies.add(new Fake(200,"new",3,null,null));UpdateChannel.transfer("https://fixture/apk",part);check(read(part).equals("new"),"server ignoring Range restarts without concatenation");
            replies.add(new Fake(206,"bad",3,"bytes 1-3/4",null));fail(part);check(read(part).equals("new"),"invalid range does not overwrite partial file");
            replies.add(new Fake(302,"",0,null,"http://fixture/apk"));fail(part);
            replies.add(new Fake(416,"",0,null,null));UpdateChannel.transfer("https://fixture/apk",part);check(read(part).equals("new"),"416 preserves file for hash verification");
            check(UpdateChannel.hex(UpdateChannel.hash(part)).equals("11507a0e2f5e69d5dfa40a62a1bd7b6ee57e6bcd85c67c9b8431b36fff21c437"),"real SHA-256 of saved bytes");
            System.out.println("PASS: "+cases+" update transport cases; no network");
        }finally{Files.deleteIfExists(part.toPath());Files.deleteIfExists(dir);}
    }
}
