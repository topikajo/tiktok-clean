package mod.arm32.probe;
import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.lang.reflect.*;
import java.security.*;
import java.util.*;
import org.json.*;

/** Installed updater, real package parser/certificates, FileProvider and Android layout; no account. */
public final class Arm32ProbeInstrumentation extends Instrumentation {
    boolean begun,appReady,configReady;int cases;
    public Application newApplication(ClassLoader loader,String name,Context c)throws InstantiationException,IllegalAccessException,ClassNotFoundException{return super.newApplication(loader,Application.class.getName(),c);}
    public void callApplicationOnCreate(Application app){super.callApplicationOnCreate(app);try{cls("mod.arm32.Runtime32").getMethod("install",Application.class).invoke(null,app);cls("mod.clean.CleanApp").getMethod("install",Application.class).invoke(null,app);}catch(Exception e){throw new RuntimeException(e);}appReady=true;begin();}
    public void onCreate(Bundle args){super.onCreate(args);configReady=true;begin();}
    synchronized void begin(){if(begun||!appReady||!configReady)return;begun=true;new Thread(new Runnable(){public void run(){onStart();}},"UpdateProbe").start();}
    Class<?> cls(String name)throws Exception{return getTargetContext().getClassLoader().loadClass(name);}
    static Field field(Class<?> owner,String name)throws Exception{Field f=owner.getDeclaredField(name);f.setAccessible(true);return f;}
    static Method method(Class<?> owner,String name,Class<?>... types)throws Exception{Method m=owner.getDeclaredMethod(name,types);m.setAccessible(true);return m;}
    void check(boolean ok,String text){if(!ok)throw new AssertionError(text);cases++;Bundle b=new Bundle();b.putString("step",cases+": "+text);sendStatus(1,b);}
    public static class FixtureActivity extends Activity{void attach(Context c){attachBaseContext(c);}public Object getSystemService(String name){return getBaseContext().getSystemService(name);}}
    String digest(File file)throws Exception{MessageDigest hash=MessageDigest.getInstance("SHA-256");try(InputStream in=new FileInputStream(file)){byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)hash.update(b,0,n);}return (String)cls("mod.arm32.UpdateChannel").getMethod("hex",byte[].class).invoke(null,(Object)hash.digest());}
    JSONObject release(File file,long version)throws Exception{return new JSONObject().put("packageName",getTargetContext().getPackageName()).put("versionCode",version).put("versionName","fixture").put("sha256",digest(file)).put("apkUrls",new JSONArray().put("https://fixture.invalid/app.apk"));}
    public void onStart(){
        Bundle result=new Bundle();int code=Activity.RESULT_CANCELED;ArrayList<File> files=new ArrayList<File>();SharedPreferences prefs=null;
        try {
            Context c=getTargetContext();check(!android.os.Process.is64Bit(),"actual 32-bit Android app process");Class<?> updater=cls("mod.arm32.UpdateChannel");prefs=(SharedPreferences)cls("mod.arm32.Runtime32").getMethod("prefs").invoke(null);
            long installed=c.getPackageManager().getPackageInfo(c.getPackageName(),0).versionCode;
            android.content.pm.PackageInfo info=c.getPackageManager().getPackageInfo(c.getPackageName(),android.content.pm.PackageManager.GET_PERMISSIONS);
            java.util.List<String> permissions=java.util.Arrays.asList(info.requestedPermissions);
            check(!permissions.contains("android.permission.SYSTEM_ALERT_WINDOW")&&!permissions.contains("android.permission.USE_FULL_SCREEN_INTENT"),"no overlay/fullscreen permission");
            check(!permissions.contains("android.permission.READ_PHONE_STATE")&&!permissions.contains("android.permission.ACCESS_FINE_LOCATION"),"no phone ID/location permission");
            check(c.checkSelfPermission("android.permission.CAMERA")==android.content.pm.PackageManager.PERMISSION_DENIED,"camera not granted at startup");
            android.app.job.JobScheduler scheduler=(android.app.job.JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);boolean scheduled=false;for(android.app.job.JobInfo job:scheduler.getAllPendingJobs())if(job.getId()==47141)scheduled=true;
            check(!scheduled,"no automatic streak job before opting in");
            Object ad=cls("com.google.android.gms.ads.identifier.AdvertisingIdClient").getMethod("getAdvertisingIdInfo",Context.class).invoke(null,c);
            check("".equals(ad.getClass().getMethod("getId").invoke(ad)),"advertising ID blank without Google services");
            Class<?> net=cls("mod.arm32.PrivacyNet");check((Boolean)net.getMethod("blocked",String.class).invoke(null,"https://log-va.tiktokv.com/service/2/app_log/"),"analytics URL blocked");
            check(!(Boolean)net.getMethod("blocked",String.class).invoke(null,"https://api-core.tiktokv.com/passport/auth/login/"),"login URL preserved");
            Class<?> aweme=cls("com.ss.android.ugc.aweme.feed.model.Aweme");Object item=aweme.getConstructor().newInstance();aweme.getMethod("setAid",String.class).invoke(item,"arm32-offline-fixture");
            Method dispatch=cls("mod.clean.NativeBridge").getMethod("call",Object.class,String.class,Object[].class);Object[] none=new Object[0];for(int i=0;i<1000;i++)dispatch.invoke(null,item,"getAid",none);
            long started=System.nanoTime();for(int i=0;i<100000;i++)if(!"arm32-offline-fixture".equals(dispatch.invoke(null,item,"getAid",none)))throw new AssertionError("wrong SDK model reflection");
            check(true,"100000 real Aweme/NativeBridge lookups in 32-bit process");result.putLong("reflection_100000_ms",(System.nanoTime()-started)/1000000);
            Method verify=method(updater,"verifyCandidate",Context.class,JSONObject.class,File.class),valid=method(updater,"valid",JSONObject.class,String.class),pending=method(updater,"pending");
            File dir=c.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("fixture directory");
            File future=null;JSONObject futureRelease=null;
            for(String name:new String[]{"future","same-version","wrong-package","wrong-signer","wrong-abi"}) {
                File file=new File(dir,"update-probe-"+name+".apk");files.add(file);
                try(InputStream in=getContext().getAssets().open(name+".apk");OutputStream out=new FileOutputStream(file)){byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}
                JSONObject r=release(file,name.equals("same-version")?installed:installed+1);
                if(name.equals("future")){verify.invoke(null,c,r,file);check(true,"future APK with real matching signer accepted");future=file;futureRelease=r;}
                else try{verify.invoke(null,c,r,file);throw new AssertionError(name+" accepted");}catch(InvocationTargetException e){check(e.getCause() instanceof SecurityException,name+" rejected");}
            }
            JSONObject broken=new JSONObject(futureRelease.toString()).put("sha256",String.format("%064d",0));
            try{verify.invoke(null,c,broken,future);throw new AssertionError("hash accepted");}catch(InvocationTargetException e){check(e.getCause() instanceof SecurityException,"changed bytes/hash rejected");}
            check(!(Boolean)valid.invoke(null,new JSONObject(futureRelease.toString()).put("apkUrls",new JSONArray().put("http://fixture.invalid/a")),c.getPackageName()),"HTTP rejected");
            check(!(Boolean)valid.invoke(null,new JSONObject(futureRelease.toString()).put("apkUrls",new JSONArray().put("https://user:secret@fixture.invalid/a")),c.getPackageName()),"URL credentials rejected");
            Class<?> provider=cls("androidx.core.content.FileProvider");Uri uri=(Uri)provider.getMethod("getUriForFile",Context.class,String.class,File.class).invoke(null,c,"com.zhiliaoapp.musically.fileprovider",future);
            check("content".equals(uri.getScheme()),"download path supported by actual FileProvider");
            try(InputStream in=c.getContentResolver().openInputStream(uri)){check(in.read()=='P'&&in.read()=='K',"installer URI opens actual APK bytes");}
            check(cls("com.ss.android.ugc.aweme.inbox.InboxShellFragment").getMethod("onResume")!=null,"native Inbox resume binding");
            check(cls("com.ss.android.ugc.aweme.notification.sysnotice.SystemNotificationContainerFragment").getMethod("onViewCreated",View.class,Bundle.class)!=null,"notification screen binding");
            field(updater,"installed").set(null,installed);field(updater,"loaded").set(null,true);field(updater,"latest").set(null,futureRelease);
            prefs.edit().remove("downloaded_version").remove("downloaded_sha").remove("downloaded_path").remove("downloaded_size").commit();
            check((Boolean)pending.invoke(null),"new release has pending dot");
            prefs.edit().putLong("offered_version",installed+1).commit();check((Boolean)pending.invoke(null),"dismissing once leaves dot");
            final FixtureActivity[] activities=new FixtureActivity[1];final FrameLayout[] roots=new FrameLayout[1];final Class<?> target=updater;
            runOnMainSync(new Runnable(){public void run(){try{FixtureActivity a=new FixtureActivity();a.attach(c);activities[0]=a;FrameLayout root=new FrameLayout(a);root.setPadding(5,17,5,9);root.addView(new TextView(a),new FrameLayout.LayoutParams(-1,-1));roots[0]=root;method(target,"renderInbox",Activity.class,View.class).invoke(null,a,root);int w=View.MeasureSpec.makeMeasureSpec(1080,View.MeasureSpec.EXACTLY),h=View.MeasureSpec.makeMeasureSpec(1920,View.MeasureSpec.EXACTLY);root.measure(w,h);root.layout(0,0,1080,1920);}catch(Exception e){throw new RuntimeException(e);}}});
            FrameLayout root=roots[0];View row=root.findViewWithTag("clean_update_inbox");check(row!=null&&row.getVisibility()==View.VISIBLE,"real Android Inbox row attached");
            check(root.getPaddingTop()>17,"update row reserves space above native content");
            check((Boolean)pending.invoke(null),"viewing Inbox leaves dot");
            prefs.edit().putLong("downloaded_version",installed+1).putString("downloaded_sha",futureRelease.getString("sha256")).putString("downloaded_path",future.getPath()).putLong("downloaded_size",future.length()).commit();
            check(!(Boolean)pending.invoke(null),"verified present download clears dot");
            runOnMainSync(new Runnable(){public void run(){try{method(target,"renderInbox",Activity.class,View.class).invoke(null,activities[0],root);}catch(Exception e){throw new RuntimeException(e);}}});
            check("Установить".contentEquals(((Button)((LinearLayout)row).getChildAt(1)).getText()),"download button becomes Install");
            prefs.edit().putLong("downloaded_size",future.length()+1).commit();check((Boolean)pending.invoke(null),"truncated/missing file restores dot");
            field(updater,"latest").set(null,null);
            runOnMainSync(new Runnable(){public void run(){try{method(target,"renderInbox",Activity.class,View.class).invoke(null,activities[0],root);}catch(Exception e){throw new RuntimeException(e);}}});
            check(row.getVisibility()==View.GONE&&root.getPaddingTop()==17,"removing release restores native content padding");
            result.putString("result","PASS "+cases+" ARM32 plain-Application/update cases; native cold start checked separately; live account and Inbox excluded");code=Activity.RESULT_OK;
        }catch(Throwable e){result.putString("failure",e.toString());StringWriter trace=new StringWriter();e.printStackTrace(new PrintWriter(trace));result.putString("trace",trace.toString());}
        finally{if(prefs!=null)prefs.edit().remove("offered_version").remove("release_candidate").remove("last_release_check").remove("downloaded_version").remove("downloaded_sha").remove("downloaded_path").remove("downloaded_size").commit();for(File f:files)f.delete();}
        finish(code,result);
    }
}
