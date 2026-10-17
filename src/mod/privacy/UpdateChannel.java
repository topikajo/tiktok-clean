package mod.privacy;

import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.graphics.*;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.lang.ref.WeakReference;
import java.net.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Public HTTPS release feed; no GitHub credentials, usage statistics or background jobs. */
public final class UpdateChannel {
    private static final ExecutorService io=Executors.newSingleThreadExecutor();
    private static final AtomicBoolean checking=new AtomicBoolean(),downloading=new AtomicBoolean();
    private static final Map<View,Boolean> inboxRoots=new WeakHashMap<View,Boolean>();
    private static final Map<View,int[]> inboxInsets=new WeakHashMap<View,int[]>();
    private static final Map<View,Dot> dots=new WeakHashMap<View,Dot>();
    private static final Map<View,Boolean> settingsRows=new WeakHashMap<View,Boolean>();
    private static final String OWN_SIGNER="0d45ee683c8c3f375e4d52a258ddbda0775c38f6ab434374e87fed09318cada0";
    private static final long CHECK_MS=60*60*1000L;
    private static volatile JSONObject latest;
    private static volatile boolean loaded;
    private static volatile long installed;
    private static volatile String status="";
    private static final String ROW="clean_update_inbox",OFFER="clean_update_offer";
    private static SharedPreferences prefs(){return PrivacyRuntime.prefs();}
    private static int dp(Context c,float n){return Math.round(n*c.getResources().getDisplayMetrics().density);}
    public static String hex(byte[] bytes){StringBuilder s=new StringBuilder(bytes.length*2);for(byte b:bytes){int v=b&255;s.append("0123456789abcdef".charAt(v>>>4)).append("0123456789abcdef".charAt(v&15));}return s.toString();}
    private static byte[] hash(File f)throws Exception {
        MessageDigest d=MessageDigest.getInstance("SHA-256");try(InputStream in=new FileInputStream(f)){byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)d.update(b,0,n);}return d.digest();
    }
    private static long version(PackageInfo info){return Build.VERSION.SDK_INT>=28?info.getLongVersionCode():info.versionCode;}
    private static int flags(){return Build.VERSION.SDK_INT>=28?PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES;}
    private static byte[][] certificates(PackageInfo info){
        Signature[] signatures=Build.VERSION.SDK_INT>=28&&info.signingInfo!=null?info.signingInfo.getApkContentsSigners():info.signatures;
        if(signatures==null)return new byte[0][];byte[][] result=new byte[signatures.length][];for(int i=0;i<result.length;i++)result[i]=signatures[i].toByteArray();return result;
    }
    public static boolean sameSigners(byte[][] a,byte[][] b){
        if(a.length==0||a.length!=b.length)return false;
        Set<String> first=new HashSet<String>(),second=new HashSet<String>();for(byte[] v:a)first.add(hex(v));for(byte[] v:b)second.add(hex(v));return first.equals(second);
    }
    private static synchronized void load(Context c){
        if(loaded)return;
        try {
            installed=version(c.getPackageManager().getPackageInfo(c.getPackageName(),0));
            String saved=prefs().getString("release_candidate","");
            if(!saved.isEmpty()){JSONObject data=new JSONObject(saved);if(valid(data,c.getPackageName())&&UpdatePolicy.available(installed,data.optLong("versionCode")))latest=data;}
        }catch(Exception ignored){}
        loaded=installed>0;
    }
    private static boolean valid(JSONObject data,String pkg){
        if(!pkg.equals(data.optString("packageName"))||data.optLong("versionCode")<=0||!data.optString("sha256").matches("[a-fA-F0-9]{64}"))return false;
        JSONArray urls=data.optJSONArray("apkUrls");if(urls==null||urls.length()==0||urls.length()>8)return false;
        for(int i=0;i<urls.length();i++)try{URL u=new URL(urls.getString(i));if(!"https".equalsIgnoreCase(u.getProtocol())||u.getHost().isEmpty()||u.getUserInfo()!=null)return false;}catch(Exception e){return false;}
        return true;
    }
    private static List<String> feeds(Context c){
        ArrayList<String> result=new ArrayList<String>();String custom=prefs().getString("update_feed","").trim();if(!custom.isEmpty())result.add(custom);
        try(InputStream in=c.getAssets().open("clean-update-channel.json")){
            JSONObject object=new JSONObject(new String(read(in,65536),"UTF-8"));JSONArray list=object.optJSONArray("feeds");
            if(list!=null)for(int i=0;i<Math.min(8,list.length());i++){String value=list.getString(i);if(!result.contains(value))result.add(value);}
        }catch(Exception ignored){}return result;
    }
    private static byte[] read(InputStream in,int limit)throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[2048];int n;while((n=in.read(b))!=-1){if(out.size()+n>limit)throw new IOException("Response too large");out.write(b,0,n);}return out.toByteArray();
    }
    static HttpURLConnection connection(String address,long offset)throws Exception {
        URL url=new URL(address);
        for(int redirects=0;redirects<5;redirects++){
            if(!"https".equalsIgnoreCase(url.getProtocol())||url.getUserInfo()!=null)throw new IOException("HTTPS required");
            HttpURLConnection c=(HttpURLConnection)url.openConnection();c.setConnectTimeout(10000);c.setReadTimeout(20000);c.setInstanceFollowRedirects(false);
            c.setRequestProperty("Accept-Encoding","identity");if(offset>0)c.setRequestProperty("Range","bytes="+offset+"-");
            int code=c.getResponseCode();
            if(code>=300&&code<=399){String location=c.getHeaderField("Location");c.disconnect();if(location==null)throw new IOException("Missing redirect");url=new URL(url,location);continue;}
            if(code!=200 && !(offset>0&&(code==206||code==416))){c.disconnect();throw new IOException("HTTP "+code);}return c;
        }throw new IOException("Too many redirects");
    }
    static void transfer(String url,File part)throws Exception {
        long offset=part.exists()?part.length():0;if(offset>1024L*1024*1024)throw new IOException("APK too large");
        HttpURLConnection c=connection(url,offset);
        try {
            int code=c.getResponseCode();if(code==416)return;
            if(code==206){String range=c.getHeaderField("Content-Range");if(range==null||!range.startsWith("bytes "+offset+"-"))throw new IOException("Invalid range");}
            boolean append=code==206;long total=append?offset:0,received=0,length=c.getContentLength();
            try(InputStream in=c.getInputStream();OutputStream out=new FileOutputStream(part,append)){
                byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1){total+=n;received+=n;if(total>1024L*1024*1024)throw new IOException("APK too large");out.write(b,0,n);}
            }
            if(length>=0&&received!=length)throw new IOException("Incomplete APK");
        }finally{c.disconnect();}
    }
    private static File downloadedFile(JSONObject release){
        String name=prefs().getString("downloaded_path","");if(name.isEmpty())return null;
        if(prefs().getLong("downloaded_version",0)!=release.optLong("versionCode")||!prefs().getString("downloaded_sha","").equalsIgnoreCase(release.optString("sha256")))return null;
        File file=new File(name);return file.isFile()&&file.length()==prefs().getLong("downloaded_size",-1)?file:null;
    }
    static boolean pending(){JSONObject r=latest;return r!=null&&UpdatePolicy.pending(installed,r.optLong("versionCode"),prefs().getLong("downloaded_version",0),downloadedFile(r)!=null);}
    public static void onResume(final Activity activity){
        load(activity);boolean main=activity.getClass().getName().equals("com.ss.android.ugc.aweme.main.MainActivity");
        if(main){bindBadge(activity);PrivacyRuntime.main.postDelayed(new Runnable(){public void run(){if(!activity.isFinishing())bindBadge(activity);}},350);}
        if(main||activity.getClass().getName().equals("com.ss.android.ugc.aweme.setting.ui.SettingContainerActivity"))check(activity,false);
        if(main)maybeOffer(activity);
    }
    public static void attach(final Activity activity){
        load(activity);LinearLayout row=PrivacyRuntime.insertRow(activity,"clean_update_row");if(row==null)return;
        settingsRows.put(row,Boolean.TRUE);renderSettings(activity,row);check(activity,false);
    }
    private static void renderSettings(final Activity activity,View target){
        final LinearLayout row=(LinearLayout)target;if(row.getChildCount()==0){row.addView(PrivacyRuntime.button(activity,"Обновления TikTok Clean"));}
        TextView button=(TextView)row.getChildAt(0);JSONObject r=latest;
        button.setText(downloading.get()?"Загружается обновление…":r==null?"TikTok Clean · проверить обновления":downloadedFile(r)!=null?"Обновление скачано · установить":"Доступно обновление · скачать");
        button.setOnClickListener(new View.OnClickListener(){public void onClick(View v){JSONObject release=latest;if(release==null)check(activity,true);else action(activity,release);}});
        button.setOnLongClickListener(new View.OnLongClickListener(){public boolean onLongClick(View v){
            final EditText address=new EditText(activity);address.setSingleLine(true);address.setText(prefs().getString("update_feed",""));
            new AlertDialog.Builder(activity).setTitle("Источник обновлений").setMessage("Необязательный HTTPS-адрес зеркала. Пустое поле — основной канал.").setView(address).setNegativeButton("Отмена",null).setPositiveButton("Сохранить",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){
                String value=address.getText().toString().trim();if(value.isEmpty()||value.startsWith("https://")){prefs().edit().putString("update_feed",value).remove("last_release_check").apply();check(activity,true);}
                else Toast.makeText(activity,"Нужен адрес HTTPS",Toast.LENGTH_SHORT).show();
            }}).show();return true;
        }});
    }
    public static void attachInbox(Object fragment){
        try{Activity a=(Activity)CachedReflect.call(fragment,"getActivity");View view=(View)CachedReflect.call(fragment,"getView");if(a!=null&&view!=null){load(a);inboxRoots.put(view,Boolean.TRUE);renderInbox(a,view);check(a,false);}}catch(Exception ignored){}
    }
    private static void renderInbox(final Activity activity,View view){
        if(!(view instanceof FrameLayout))return;final FrameLayout root=(FrameLayout)view;
        LinearLayout row=(LinearLayout)root.findViewWithTag(ROW);final JSONObject r=latest;
        if(row==null && r==null)return;
        if(row==null){
            final int baseTop=root.getPaddingTop();final int[] inset={0};inboxInsets.put(root,inset);
            row=new LinearLayout(activity);row.setTag(ROW);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(activity,12),dp(activity,8),dp(activity,8),dp(activity,8));row.setMinimumHeight(dp(activity,56));row.setBackgroundColor(0xfff2f2f2);row.setElevation(dp(activity,3));
            TextView title=new TextView(activity);title.setTextColor(0xff171717);title.setTextSize(14);title.setMaxLines(3);row.addView(title,new LinearLayout.LayoutParams(0,-2,1));
            Button button=new Button(activity);button.setAllCaps(false);row.addView(button,new LinearLayout.LayoutParams(-2,-2));
            final LinearLayout item=row;root.addView(row,new FrameLayout.LayoutParams(-1,-2,Gravity.TOP));
            row.addOnLayoutChangeListener(new View.OnLayoutChangeListener(){public void onLayoutChange(View v,int l,int t,int right,int bottom,int ol,int ot,int or,int ob){
                int h=item.getVisibility()==View.GONE?0:bottom-t;if(h==inset[0])return;inset[0]=h;root.setPadding(root.getPaddingLeft(),baseTop+h,root.getPaddingRight(),root.getPaddingBottom());
                FrameLayout.LayoutParams p=(FrameLayout.LayoutParams)item.getLayoutParams();p.topMargin=-h;item.setLayoutParams(p);
            }});
        }
        if(r==null){int[] inset=inboxInsets.get(root);if(inset!=null){root.setPadding(root.getPaddingLeft(),root.getPaddingTop()-inset[0],root.getPaddingRight(),root.getPaddingBottom());inset[0]=0;}FrameLayout.LayoutParams p=(FrameLayout.LayoutParams)row.getLayoutParams();p.topMargin=0;row.setLayoutParams(p);row.setVisibility(View.GONE);return;}
        row.setVisibility(View.VISIBLE);
        TextView title=(TextView)row.getChildAt(0);Button button=(Button)row.getChildAt(1);boolean ready=downloadedFile(r)!=null;
        title.setText((pending()?"● ":"")+"Обновление TikTok Clean\n"+(downloading.get()?"Загружается…":ready?"Файл готов к установке":status.isEmpty()?r.optString("versionName","Новая версия"):status));
        title.setContentDescription(title.getText());button.setText(downloading.get()?"Загрузка…":ready?"Установить":"Скачать");button.setEnabled(!downloading.get());
        button.setOnClickListener(new View.OnClickListener(){public void onClick(View v){JSONObject release=latest;if(release!=null)action(activity,release);}});
    }
    private static final class Dot extends Drawable {
        final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);final WeakReference<View> anchor;final float density;
        Dot(View view){anchor=new WeakReference<View>(view);density=view.getResources().getDisplayMetrics().density;paint.setColor(0xfffe2c55);}
        public void draw(Canvas c){View v=anchor.get();if(v!=null)c.drawCircle(Math.max(7*density,v.getWidth()-9*density),9*density,4*density,paint);}
        public void setAlpha(int n){paint.setAlpha(n);}public void setColorFilter(ColorFilter f){paint.setColorFilter(f);}public int getOpacity(){return PixelFormat.TRANSLUCENT;}
    }
    private static void bindBadge(Activity activity){
        View host=activity.findViewById(2131381843);if(!(host instanceof ViewGroup))return;ViewGroup tabs=(ViewGroup)host;
        for(int i=0;i<tabs.getChildCount();i++)try{
            View tab=tabs.getChildAt(i);Object icon=CachedReflect.call(tab,"getIconData");String tag=String.valueOf(CachedReflect.field(icon,"LIZIZ"));
            if(!"NOTIFICATION".equals(tag))continue;
            Dot dot=dots.get(tab);if(pending()){if(dot==null){dot=new Dot(tab);dots.put(tab,dot);tab.getOverlay().add(dot);}dot.setBounds(0,0,tab.getWidth(),tab.getHeight());dot.invalidateSelf();}
            else if(dot!=null){tab.getOverlay().remove(dot);dots.remove(tab);}
        }catch(Exception ignored){}
    }
    private static void refreshViews(){
        for(View view:new ArrayList<View>(inboxRoots.keySet())){Activity a=activity(view.getContext());if(a!=null&&!a.isFinishing())renderInbox(a,view);}
        for(View view:new ArrayList<View>(settingsRows.keySet())){Activity a=activity(view.getContext());if(a!=null&&!a.isFinishing())renderSettings(a,view);}
        for(View tab:new ArrayList<View>(dots.keySet()))if(!pending()){Dot dot=dots.remove(tab);if(dot!=null)tab.getOverlay().remove(dot);}
        Activity a=PrivacyRuntime.foregroundActivity();if(a!=null&&!a.isFinishing()){bindBadge(a);maybeOffer(a);}
    }
    private static Activity activity(Context c){for(int i=0;i<12&&c!=null;i++){if(c instanceof Activity)return (Activity)c;if(!(c instanceof ContextWrapper))break;c=((ContextWrapper)c).getBaseContext();}return null;}
    private static void maybeOffer(final Activity a){
        final JSONObject release=latest;if(release==null||a.isFinishing()||PrivacyRuntime.foregroundActivity()!=a||!a.getClass().getName().equals("com.ss.android.ugc.aweme.main.MainActivity"))return;
        long v=release.optLong("versionCode");if(!UpdatePolicy.prompt(installed,v,prefs().getLong("offered_version",0),prefs().getLong("downloaded_version",0),downloadedFile(release)!=null))return;
        View parent=a.findViewById(android.R.id.content);if(!(parent instanceof FrameLayout)||parent.findViewWithTag(OFFER)!=null)return;
        final FrameLayout root=(FrameLayout)parent;final LinearLayout card=new LinearLayout(a);card.setTag(OFFER);card.setGravity(Gravity.CENTER_VERTICAL);card.setPadding(dp(a,12),dp(a,4),dp(a,4),dp(a,4));card.setBackgroundColor(0xffeeeeee);card.setElevation(dp(a,5));
        TextView text=new TextView(a);text.setText("Доступно обновление TikTok Clean");text.setTextColor(0xff111111);card.addView(text,new LinearLayout.LayoutParams(0,-2,1));
        Button get=new Button(a);get.setText("Скачать");get.setAllCaps(false);card.addView(get);Button close=new Button(a);close.setText("×");close.setMinWidth(0);close.setMinimumWidth(0);card.addView(close,new LinearLayout.LayoutParams(dp(a,44),-2));
        FrameLayout.LayoutParams p=new FrameLayout.LayoutParams(-1,-2,Gravity.TOP);p.setMargins(dp(a,10),dp(a,48),dp(a,10),0);root.addView(card,p);
        prefs().edit().putLong("offered_version",v).apply();
        get.setOnClickListener(new View.OnClickListener(){public void onClick(View view){root.removeView(card);download(a,release);}});close.setOnClickListener(new View.OnClickListener(){public void onClick(View view){root.removeView(card);}});
        PrivacyRuntime.main.postDelayed(new Runnable(){public void run(){if(card.getParent()==root)root.removeView(card);}},10000);
    }
    private static void check(final Activity activity,final boolean manual){
        load(activity);long now=System.currentTimeMillis(),last=prefs().getLong("last_release_check",0);
        if(!manual&&now>=last&&now-last<CHECK_MS)return;if(!checking.compareAndSet(false,true))return;
        final Context context=activity.getApplicationContext();final WeakReference<Activity> origin=new WeakReference<Activity>(activity);
        io.execute(new Runnable(){public void run(){String failure="Обновлений пока нет";JSONObject found=null;boolean answered=false;
            try{List<String> sources=feeds(context);if(sources.isEmpty())failure="Источник обновлений пока не задан";
                for(String source:sources)try{
                    HttpURLConnection c=connection(source,0);byte[] bytes;try(InputStream in=c.getInputStream()){bytes=read(in,65536);}finally{c.disconnect();}
                    JSONObject data=new JSONObject(new String(bytes,"UTF-8"));if(!valid(data,context.getPackageName()))throw new IOException("Invalid release feed");
                    answered=true;if(UpdatePolicy.available(installed,data.optLong("versionCode"))){found=data;break;}
                }catch(Exception ignored){failure="Не удалось проверить обновления";}
                SharedPreferences.Editor edit=prefs().edit().putLong("last_release_check",System.currentTimeMillis());
                if(found!=null){latest=found;edit.putString("release_candidate",found.toString());status="";}
                else if(latest!=null&&!UpdatePolicy.available(installed,latest.optLong("versionCode"))){latest=null;edit.remove("release_candidate");}
                // A network failure never clears a previously discovered update or its badge.
                edit.apply();
            }catch(Exception ignored){failure="Не удалось проверить обновления";}
            finally{checking.set(false);}
            final String message=failure;PrivacyRuntime.main.post(new Runnable(){public void run(){refreshViews();Activity a=origin.get();if(manual&&a!=null&&!a.isFinishing()&&latest==null)Toast.makeText(a,message,Toast.LENGTH_SHORT).show();}});
        }});
    }
    private static void action(Activity activity,JSONObject release){if(downloadedFile(release)==null)download(activity,release);else install(activity,release);}
    static void verifyCandidate(Context context,JSONObject release,File file)throws Exception {
        if(!valid(release,context.getPackageName())||!release.getString("sha256").equalsIgnoreCase(hex(hash(file))))throw new SecurityException("Wrong hash");
        PackageManager pm=context.getPackageManager();PackageInfo current=pm.getPackageArchiveInfo(context.getApplicationInfo().sourceDir,flags()),after=pm.getPackageArchiveInfo(file.getPath(),flags());
        if(current==null||after==null||!context.getPackageName().equals(after.packageName)||version(after)!=release.getLong("versionCode")||!UpdatePolicy.available(version(current),version(after)))throw new SecurityException("Wrong package/version");
        byte[][] before=certificates(current),signers=certificates(after);
        if(!sameSigners(before,signers)||signers.length!=1||!OWN_SIGNER.equals(hex(MessageDigest.getInstance("SHA-256").digest(signers[0]))))throw new SecurityException("Wrong signer");
    }
    private static void download(final Activity activity,final JSONObject release){
        if(!downloading.compareAndSet(false,true))return;status="";refreshViews();final Context context=activity.getApplicationContext();
        io.execute(new Runnable(){public void run(){boolean success=false;
            try{
                if(!valid(release,context.getPackageName()))throw new SecurityException("Invalid release");
                File dir=context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);if(dir==null)throw new IOException("No download directory");
                String expected=release.getString("sha256").toLowerCase(Locale.ROOT);File file=new File(dir,"clean-update-"+expected+".apk"),part=new File(dir,"clean-update-"+expected+".part");
                JSONArray urls=release.getJSONArray("apkUrls");boolean complete=file.isFile()&&expected.equals(hex(hash(file)));
                for(int i=0;i<urls.length()&&!complete;i++)try{transfer(urls.getString(i),part);if(!expected.equals(hex(hash(part)))){try(RandomAccessFile reset=new RandomAccessFile(part,"rw")){reset.setLength(0);}throw new IOException("Hash mismatch");}if(!part.renameTo(file))throw new IOException("Cannot finalize APK");complete=true;}catch(Exception ignored){}
                if(!complete)throw new IOException("Download failed");verifyCandidate(context,release,file);
                prefs().edit().putLong("downloaded_version",release.getLong("versionCode")).putString("downloaded_sha",expected).putString("downloaded_path",file.getPath()).putLong("downloaded_size",file.length()).apply();success=true;status="";
            }catch(Exception e){status=e instanceof SecurityException?"Файл не прошёл проверку":"Не удалось скачать. Попробуйте ещё раз";}
            finally{downloading.set(false);}
            final boolean ok=success;PrivacyRuntime.main.post(new Runnable(){public void run(){refreshViews();Activity a=PrivacyRuntime.foregroundActivity();if(ok&&a!=null&&!a.isFinishing())Toast.makeText(a,"Обновление скачано. Установить можно во «Входящих»",Toast.LENGTH_LONG).show();}});
        }});
    }
    private static void install(final Activity activity,final JSONObject release){
        final File file=downloadedFile(release);if(file==null){download(activity,release);return;}
        if(Build.VERSION.SDK_INT>=26&&!activity.getPackageManager().canRequestPackageInstalls()){
            activity.startActivity(new Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+activity.getPackageName())));return;
        }
        io.execute(new Runnable(){public void run(){try{verifyCandidate(activity.getApplicationContext(),release,file);PrivacyRuntime.main.post(new Runnable(){public void run(){if(activity.isFinishing())return;try{
            Class<?> provider=Class.forName("androidx.core.content.FileProvider");Uri uri=(Uri)provider.getMethod("getUriForFile",Context.class,String.class,File.class).invoke(null,activity,"com.zhiliaoapp.musically.fileprovider",file);
            activity.startActivity(new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION));
        }catch(Exception e){Toast.makeText(activity,"Не удалось открыть установщик",Toast.LENGTH_LONG).show();}}});}
        catch(Exception e){prefs().edit().remove("downloaded_version").remove("downloaded_sha").apply();PrivacyRuntime.main.post(new Runnable(){public void run(){status="Файл не прошёл проверку";refreshViews();}});}}});
    }
}
