package mod.privacy.probe;
import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.graphics.*;
import android.net.Uri;
import android.os.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.concurrent.*;
import dalvik.system.DexClassLoader;

/** Exercises the installed release DEX with a plain Application, avoiding the base mod's native emulator crash. */
public class PrivacyProbeInstrumentation extends Instrumentation {
    int count;private boolean begun,appReady,configReady;private int expectedVersion;
    static class CaptureActivity extends Activity {
        final CountDownLatch result=new CountDownLatch(1);int[] grants;
        void attach(Context context){attachBaseContext(context);}
        public void onRequestPermissionsResult(int code,String[] permissions,int[] values){grants=values;result.countDown();}
    }
    static class CaptureFragment extends android.app.Fragment {
        final CountDownLatch result=new CountDownLatch(1);int[] grants;
        public void onRequestPermissionsResult(int code,String[] permissions,int[] values){grants=values;result.countDown();}
    }
    Class<?> cls(String name)throws Exception{return getTargetContext().getClassLoader().loadClass(name);}
    void check(boolean ok,String text){if(!ok)throw new AssertionError(text);count++;Bundle b=new Bundle();b.putString("step",count+": "+text);sendStatus(1,b);}
    static Object field(Object target,String name)throws Exception {
        for(Class<?> t=target.getClass();t!=null;t=t.getSuperclass())try{Field f=t.getDeclaredField(name);f.setAccessible(true);return f.get(target);}catch(NoSuchFieldException ignored){}
        throw new NoSuchFieldException(name);
    }
    synchronized void begin(){if(begun||!appReady||!configReady)return;begun=true;new Thread(new Runnable(){public void run(){onStart();}},"PrivacyProbe").start();}
    public Application newApplication(ClassLoader loader,String name,Context context)throws InstantiationException,IllegalAccessException,ClassNotFoundException{return super.newApplication(loader,Application.class.getName(),context);}
    public void callApplicationOnCreate(Application application){super.callApplicationOnCreate(application);try{cls("mod.privacy.PrivacyRuntime").getMethod("install",Application.class).invoke(null,application);}catch(Exception e){throw new RuntimeException(e);}appReady=true;begin();}
    public void onCreate(Bundle state){super.onCreate(state);expectedVersion=Integer.parseInt(state.getString("expected_version","0"));configReady=true;begin();}
    public void onStart(){
        Bundle result=new Bundle();Uri frameUri=null;File dexFile=null;
        try {
            Context context=getTargetContext();Class<?> runtime=cls("mod.privacy.PrivacyRuntime");
            File crash=new File(context.getFilesDir(),"tty_crash/last_java_crash.txt");
            if(crash.isFile())try(InputStream stream=new FileInputStream(crash)) {
                byte[] bytes=new byte[12000];int n=stream.read(bytes);Bundle log=new Bundle();log.putString("saved_crash",new String(bytes,0,Math.max(0,n),"UTF-8"));sendStatus(2,log);
            }
            check(runtime.getMethod("prefs").invoke(null) instanceof SharedPreferences,"privacy runtime installed without native bootstrap");
            PackageInfo info=context.getPackageManager().getPackageInfo(context.getPackageName(),PackageManager.GET_PERMISSIONS);
            check(expectedVersion>0&&info.versionCode==expectedVersion,"installed release version");
            java.util.List<String> permissions=java.util.Arrays.asList(info.requestedPermissions);
            check(!permissions.contains("android.permission.SYSTEM_ALERT_WINDOW"),"no overlay permission");
            check(!permissions.contains("android.permission.USE_FULL_SCREEN_INTENT"),"no full-screen notification permission");
            check(!permissions.contains("android.permission.ACCESS_MEDIA_LOCATION"),"no photo GPS permission");
            check(context.checkSelfPermission("android.permission.CAMERA")==PackageManager.PERMISSION_DENIED,"camera not pre-granted");
            check(context.checkSelfPermission("android.permission.RECORD_AUDIO")==PackageManager.PERMISSION_DENIED,"microphone not pre-granted");
            ApplicationInfo appInfo=context.getPackageManager().getApplicationInfo(context.getPackageName(),PackageManager.GET_META_DATA);
            check(appInfo.metaData.getBoolean("firebase_analytics_collection_deactivated"),"Firebase analytics permanently deactivated");
            final CaptureActivity[] activityHolder=new CaptureActivity[1];
            runOnMainSync(new Runnable(){public void run(){activityHolder[0]=new CaptureActivity();activityHolder[0].attach(context);}});
            CaptureActivity activity=activityHolder[0];
            runtime.getMethod("request",Activity.class,String[].class,int.class).invoke(null,activity,new String[]{"android.permission.CAMERA"},42);
            check(activity.result.await(5,TimeUnit.SECONDS) && activity.grants[0]==PackageManager.PERMISSION_DENIED,"startup denial delivers real callback without permission dialog");
            CaptureFragment fragment=new CaptureFragment();
            runtime.getMethod("requestFragment",android.app.Fragment.class,String[].class,int.class).invoke(null,fragment,new String[]{"android.permission.CAMERA"},43);
            check(fragment.result.await(5,TimeUnit.SECONDS) && fragment.grants[0]==PackageManager.PERMISSION_DENIED,"fragment denial delivers callback");
            Object callbacks=runtime.newInstance();
            runOnMainSync(new Runnable(){public void run(){try{
                runtime.getMethod("onActivityResumed",Activity.class).invoke(callbacks,activity);
                runtime.getMethod("noteAction",Activity.class).invoke(null,activity);
            }catch(Exception e){throw new RuntimeException(e);}}});
            check((Boolean)runtime.getMethod("canRequest",Activity.class,String[].class).invoke(null,activity,new String[]{"android.permission.CAMERA"}),"foreground camera tap accepted");
            check(!(Boolean)runtime.getMethod("canRequest",Activity.class,String[].class).invoke(null,activity,new String[]{"android.permission.POST_NOTIFICATIONS"}),"unsolicited notifications on main-style screen suppressed");
            runtime.getMethod("onActivityPaused",Activity.class).invoke(callbacks,activity);
            check(!(Boolean)runtime.getMethod("canRequest",Activity.class,String[].class).invoke(null,activity,new String[]{"android.permission.CAMERA"}),"background request denied after foreground tap");
            Object adInfo=cls("com.google.android.gms.ads.identifier.AdvertisingIdClient").getMethod("getAdvertisingIdInfo",Context.class).invoke(null,context);
            check("".equals(adInfo.getClass().getMethod("getId").invoke(adInfo)),"advertising ID is blank");
            check((Boolean)field(adInfo,"LIZIZ"),"advertising limit-tracking flag true in this SDK's obfuscated Info class");
            Class<?> cell=cls("com.ss.android.ugc.aweme.feed.adapter.VideoViewCell");
            check(cell.getMethod("onPageSelected",int.class)!=null && cell.getMethod("getEventType")!=null,"native current-video callbacks exist");
            check(cell.getMethod("onPlayProgressChange",float.class)!=null && cell.getMethod("getVideoView")!=null,"native progress and rendering view hooks exist");
            check(cell.getMethod("sw2")!=null && cls("com.ss.android.ugc.feed.platform.panel.player.IPlayerComponentAbility").getMethod("zT0",float.class)!=null,"native player seek binding exists");
            check(cls("X.07ss").getMethod("LJJI",cls("com.ss.android.ugc.aweme.feed.model.FeedItemList"))!=null,"refresh hook matches production model");
            check(cls("com.ss.android.ugc.aweme.IAccountService").getMethod("LJIIJJI")!=null,"retention account-scope binding exists");
            check(cls("com.ss.android.ugc.aweme.common.widget.VerticalViewPager").getMethod("LJJIL",int.class,boolean.class,boolean.class,int.class)!=null,"common native pager selector binding exists");
            check(cls("com.ss.android.ugc.feed.platform.panel.viewpager.IViewPagerAbility").getMethod("bc1")!=null,"retention snapshots identify the actual native pager");
            try {cls("com.windukk.stable.DynamicUpdates").getMethod("importPackage",Context.class,File.class).invoke(null,context,new File(context.getCacheDir(),"missing.ttydyn"));throw new AssertionError("foreign import accepted");}
            catch(InvocationTargetException e){check(e.getCause() instanceof IOException && e.getCause().getMessage().contains("signed APK"),"foreign executable update imports blocked");}
            dexFile=new File(context.getCacheDir(),"clean-probe-bundled-"+System.nanoTime()+".dex");
            try(InputStream in=context.getAssets().open("tty/bundled/classes.dex");OutputStream out=new FileOutputStream(dexFile)){byte[] bytes=new byte[8192];int n;while((n=in.read(bytes))!=-1)out.write(bytes,0,n);}
            dexFile.setReadOnly();ClassLoader bundled=new DexClassLoader(dexFile.getPath(),context.getCodeCacheDir().getPath(),null,context.getClassLoader());
            SharedPreferences preferences=context.getSharedPreferences("privacy_probe_fixture",0);preferences.edit().clear().putBoolean("statistics_enable",true).putBoolean("auto_updates_enable",true).commit();
            Class<?> settings=bundled.loadClass("Z.ua");Object values=settings.getConstructor(SharedPreferences.class).newInstance(preferences);
            check(!(Boolean)field(values,"z") && !(Boolean)field(values,"A"),"persisted foreign telemetry/update opt-ins clamped off");
            check((Boolean)field(values,"d") && (Boolean)field(values,"B"),"ad hiding retained without obsolete startup consent");
            check(!(Boolean)field(values,"o"),"automatic chat messages default to off");
            settings.getMethod("n",boolean.class).invoke(values,true);settings.getMethod("f",boolean.class).invoke(values,true);
            check(!(Boolean)field(values,"z") && !(Boolean)field(values,"A"),"UI setters cannot revive telemetry or foreign OTA");
            preferences.edit().clear().commit();
            Bitmap frame=Bitmap.createBitmap(100,50,Bitmap.Config.ARGB_8888);frame.eraseColor(Color.rgb(32,96,160));
            frameUri=(Uri)cls("mod.privacy.FrameActions").getMethod("writeBitmap",Context.class,Bitmap.class).invoke(null,context,frame);frame.recycle();
            Bitmap decoded;try(InputStream in=context.getContentResolver().openInputStream(frameUri)){decoded=BitmapFactory.decodeStream(in);}
            check(decoded!=null && decoded.getWidth()==100 && decoded.getHeight()==50,"frame saved to real scoped MediaStore without broad storage permission");
            int pixel=decoded.getPixel(50,25);decoded.recycle();
            check(Math.abs(Color.red(pixel)-32)<8 && Math.abs(Color.green(pixel)-96)<8 && Math.abs(Color.blue(pixel)-160)<8,"JPEG export preserves video-frame pixels");
            check(context.checkSelfPermission("android.permission.READ_MEDIA_IMAGES")==PackageManager.PERMISSION_DENIED,"frame export did not request whole gallery access");
            if(frameUri!=null){context.getContentResolver().delete(frameUri,null,null);frameUri=null;}
            if(dexFile!=null){dexFile.delete();dexFile=null;}
            result.putString("result","PASS "+count+" installed-APK harness cases; native startup and real accounts excluded");finish(Activity.RESULT_OK,result);
        } catch(Throwable failure){result.putString("failure",failure.toString());StringWriter trace=new StringWriter();failure.printStackTrace(new PrintWriter(trace));result.putString("trace",trace.toString());finish(Activity.RESULT_CANCELED,result);}
        finally{if(frameUri!=null)getTargetContext().getContentResolver().delete(frameUri,null,null);if(dexFile!=null)dexFile.delete();}
    }
}
