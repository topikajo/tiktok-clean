package mod.clean;

import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Optional HTTPS release feed. Updates are never forced and must retain this APK's signer. */
public final class UpdateChannel {
    private static final ExecutorService io=Executors.newSingleThreadExecutor();
    private static volatile JSONObject latest;
    private static long checked;
    private static String authority="com.zhiliaoapp.musically.fileprovider";
    static String hex(byte[] bytes){StringBuilder s=new StringBuilder();for(byte b:bytes)s.append(String.format(Locale.ROOT,"%02x",b&255));return s.toString();}
    static byte[] hash(File file)throws Exception{
        MessageDigest d=MessageDigest.getInstance("SHA-256");try(InputStream stream=new FileInputStream(file)){byte[] buf=new byte[65536];int n;while((n=stream.read(buf))!=-1)d.update(buf,0,n);}return d.digest();
    }
    static byte[][] certificates(PackageInfo info){
        Signature[] signatures=Build.VERSION.SDK_INT>=28&&info.signingInfo!=null?info.signingInfo.getApkContentsSigners():info.signatures;
        if(signatures==null)return new byte[0][];byte[][] values=new byte[signatures.length][];for(int i=0;i<values.length;i++)values[i]=signatures[i].toByteArray();return values;
    }
    static long version(PackageInfo info){return Build.VERSION.SDK_INT>=28?info.getLongVersionCode():info.versionCode;}
    public static boolean sameSigners(byte[][] a,byte[][] b){
        if(a.length==0||a.length!=b.length)return false;
        Set<String> first=new HashSet<String>(),second=new HashSet<String>();for(byte[] value:a)first.add(hex(value));for(byte[] value:b)second.add(hex(value));return first.equals(second);
    }
    static PackageInfo current(Context c)throws Exception{return c.getPackageManager().getPackageInfo(c.getPackageName(),Build.VERSION.SDK_INT>=28?PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES);}
    static List<String> feeds(Context c){
        List<String> result=new ArrayList<String>();String custom=CleanApp.prefs().getString("update_feed","");if(!custom.isEmpty())result.add(custom);
        try(InputStream stream=c.getAssets().open("clean-update-channel.json")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buf=new byte[2048];int n;while((n=stream.read(buf))!=-1)bytes.write(buf,0,n);
            JSONArray array=new JSONObject(new String(bytes.toByteArray(),"UTF-8")).optJSONArray("feeds");if(array!=null)for(int i=0;i<array.length();i++)if(!result.contains(array.getString(i)))result.add(array.getString(i));
        }catch(Exception ignored){}return result;
    }
    static HttpURLConnection connection(String source)throws Exception{return connection(source,0);}
    static HttpURLConnection connection(String source,long offset)throws Exception{
        URL url=new URL(source);if(!"https".equalsIgnoreCase(url.getProtocol()))throw new IOException("HTTPS required");
        for(int redirects=0;redirects<4;redirects++){
            HttpURLConnection c=(HttpURLConnection)url.openConnection();c.setConnectTimeout(10000);c.setReadTimeout(20000);c.setInstanceFollowRedirects(false);
            c.setRequestProperty("Accept-Encoding","identity");if(offset>0)c.setRequestProperty("Range","bytes="+offset+"-");
            int status=c.getResponseCode();if(status>=300&&status<=399){String location=c.getHeaderField("Location");c.disconnect();url=new URL(url,location);if(!"https".equalsIgnoreCase(url.getProtocol()))throw new IOException("Insecure redirect");continue;}
            if(status!=200&&!(offset>0&&(status==206||status==416))){c.disconnect();throw new IOException("HTTP "+status);}return c;
        }throw new IOException("Redirect limit");
    }
    static void transfer(String source,File part)throws Exception{
        long offset=part.exists()?part.length():0;
        if(offset>1024L*1024*1024)throw new IOException("APK too large");
        HttpURLConnection conn=connection(source,offset);
        try{
            int status=conn.getResponseCode();
            if(status==206){String range=conn.getHeaderField("Content-Range");if(range==null||!range.startsWith("bytes "+offset+"-"))throw new IOException("Invalid content range");}
            if(status==416)return; // Caller accepts only a complete file with the expected hash.
            boolean append=status==206;long total=append?offset:0;
            long length=conn.getContentLength(),received=0;
            try(InputStream stream=conn.getInputStream();OutputStream out=new FileOutputStream(part,append)){
                byte[] buf=new byte[65536];int n;
                while((n=stream.read(buf))!=-1){total+=n;received+=n;if(total>1024L*1024*1024)throw new IOException("APK too large");out.write(buf,0,n);}
            }
            if(length>=0&&received!=length)throw new IOException("Incomplete download");
        }finally{conn.disconnect();}
    }
    public static void attach(final Activity a){
        final LinearLayout row=CleanApp.insertRow(a,"clean_update_row");if(row==null)return;
        final TextView view;
        if(row.getChildCount()==0){view=CleanApp.button(a,"TikTok Clean · проверить обновления");row.addView(view,new LinearLayout.LayoutParams(-1,-2));}
        else view=(TextView)row.getChildAt(0);
        showState(view);
        view.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(latest!=null)offer(a);else check(a,view,true);}});
        view.setOnLongClickListener(new View.OnLongClickListener(){public boolean onLongClick(View v){
            final EditText address=new EditText(a);address.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);address.setText(CleanApp.prefs().getString("update_feed",""));
            new AlertDialog.Builder(a).setTitle("Источник обновлений").setMessage("Адрес HTTPS, который будет указан вместе с новыми сборками. Можно использовать зеркало.").setView(address).setNegativeButton("Отмена",null).setPositiveButton("Сохранить",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){String url=address.getText().toString().trim();if(url.isEmpty()||url.startsWith("https://")){CleanApp.prefs().edit().putString("update_feed",url).apply();checked=0;latest=null;check(a,view,true);}else Toast.makeText(a,"Нужен адрес HTTPS",Toast.LENGTH_LONG).show();}}).show();return true;
        }});
        check(a,view,false);
    }
    static void showState(TextView view){view.setText(latest==null?"TikTok Clean · проверить обновления":"Доступно обновление "+latest.optString("versionName")+" · скачать");}
    static void check(final Activity a,final TextView view,final boolean manual){
        if(!manual&&System.currentTimeMillis()-checked<6*60*60*1000L)return;
        checked=System.currentTimeMillis();io.execute(new Runnable(){public void run(){
            final List<String> sources=feeds(a);JSONObject found=null;String failure="Обновлений пока нет";
            try{
                long installed=version(current(a));
                if(sources.isEmpty())failure="Источник будет добавлен вместе с первым обновлением";
                for(String source:sources)try{
                    HttpURLConnection conn=connection(source);ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(InputStream stream=conn.getInputStream()){byte[] buf=new byte[2048];int n;while((n=stream.read(buf))!=-1){bytes.write(buf,0,n);if(bytes.size()>65536)throw new IOException("Feed too large");}}finally{conn.disconnect();}
                    JSONObject data=new JSONObject(new String(bytes.toByteArray(),"UTF-8"));
                    if(!a.getPackageName().equals(data.optString("packageName")))throw new IOException("Wrong package");
                    if(data.optLong("versionCode")>installed&&data.optString("sha256").matches("[a-fA-F0-9]{64}")&&data.optJSONArray("apkUrls")!=null){found=data;break;}
                }catch(Exception ignored){failure="Не удалось проверить обновления. Попробуйте позже";}
            }catch(Exception ignored){failure="Не удалось проверить обновления";}
            latest=found;final String message=failure;CleanApp.main.post(new Runnable(){public void run(){if(a.isFinishing())return;showState(view);if(manual&&latest==null)Toast.makeText(a,message,Toast.LENGTH_LONG).show();else if(manual&&latest!=null)offer(a);}});
        }});
    }
    static void offer(final Activity a){
        final JSONObject release=latest;if(release==null)return;
        new AlertDialog.Builder(a).setTitle("Обновление "+release.optString("versionName")).setMessage(release.optString("notes","Доступна новая сборка TikTok Clean")).setNegativeButton("Позже",null).setPositiveButton("Скачать",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){download(a,release);}}).show();
    }
    static void download(final Activity a,final JSONObject release){
        Toast.makeText(a,"Загрузка обновления началась",Toast.LENGTH_LONG).show();io.execute(new Runnable(){public void run(){
            File file=null;String error="Не удалось скачать обновление";
            try{
                String expected=release.getString("sha256").toLowerCase(Locale.ROOT);if(!expected.matches("[a-f0-9]{64}"))throw new SecurityException("Invalid hash");
                File dir=a.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);if(dir==null)throw new IOException("No download directory");
                file=new File(dir,"clean-update-"+expected+".apk");final File part=new File(dir,"clean-update-"+expected+".part");
                JSONArray urls=release.getJSONArray("apkUrls");boolean downloaded=false;
                for(int i=0;i<urls.length();i++)try{
                    if(file.exists()&&expected.equals(hex(hash(file)))){downloaded=true;break;}
                    transfer(urls.getString(i),part);
                    if(!expected.equals(hex(hash(part)))){try(RandomAccessFile reset=new RandomAccessFile(part,"rw")){reset.setLength(0);}throw new IOException("Hash mismatch");}
                    if(!part.renameTo(file))throw new IOException("Cannot finalize APK");downloaded=true;break;
                }catch(Exception ignored){}
                if(!downloaded)throw new IOException("Download failed");
                PackageInfo before=current(a),after=a.getPackageManager().getPackageArchiveInfo(file.getAbsolutePath(),Build.VERSION.SDK_INT>=28?PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES);
                if(after==null||!before.packageName.equals(after.packageName)||version(after)!=release.getLong("versionCode")||version(after)<=version(before)||!sameSigners(certificates(before),certificates(after)))throw new SecurityException("Wrong signer, package or version");
                final File verified=file;CleanApp.main.post(new Runnable(){public void run(){if(a.isFinishing())return;new AlertDialog.Builder(a).setTitle("Обновление готово").setMessage("Подпись и целостность файла проверены. Установить новую сборку?").setNegativeButton("Позже",null).setPositiveButton("Установить",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){
                    try{Class<?> provider=Class.forName("androidx.core.content.FileProvider");Uri uri=(Uri)provider.getMethod("getUriForFile",Context.class,String.class,File.class).invoke(null,a,authority,verified);Intent intent=new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);a.startActivity(intent);}catch(Exception failure){Toast.makeText(a,"Файл сохранён в папке загрузок приложения. Откройте его для установки",Toast.LENGTH_LONG).show();}
                }}).show();}});return;
            }catch(SecurityException failure){error="Обновление отклонено: подпись или версия не совпадает";}catch(Exception ignored){}
            final String message=error;CleanApp.main.post(new Runnable(){public void run(){if(!a.isFinishing())Toast.makeText(a,message,Toast.LENGTH_LONG).show();}});
        }});
    }
}
