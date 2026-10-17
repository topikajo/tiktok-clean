package mod.clean.probe;

import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.os.Bundle;
import org.json.JSONObject;
import java.lang.reflect.*;

/** Runs against the exact installed APK in the disposable audit emulator; sends no messages. */
public class ProbeInstrumentation extends Instrumentation {
    int cases;
    void progress(String text){Bundle b=new Bundle();b.putString("step",text);sendStatus(1,b);}
    void check(boolean c,String text){if(!c)throw new AssertionError(text);cases++;progress(cases+": "+text);}
    Object call(Object target,String name,Object... args)throws Exception {
        Class<?> type=target instanceof Class?(Class<?>)target:target.getClass();
        for(Method m:type.getMethods())if(m.getName().equals(name)&&m.getParameterTypes().length==args.length){m.setAccessible(true);return m.invoke(target instanceof Class?null:target,args);}
        throw new NoSuchMethodException(name);
    }
    Class<?> cls(String name)throws Exception{return getTargetContext().getClassLoader().loadClass(name);}
    public static class FakeUser {
        public String id="1000";
        public boolean isLogin(){return true;}
        public String getCurUserId(){return id;}
    }
    private boolean begun;
    synchronized void begin(){if(begun)return;begun=true;new Thread(new Runnable(){public void run(){onStart();}},"CleanProbe").start();}
    // TikTok replaces the instrumentation during normal startup. Test its actual SDK DEX
    // with a plain Application; production startup is checked separately by cold launch.
    public Application newApplication(ClassLoader loader,String name,Context context)throws InstantiationException,IllegalAccessException,ClassNotFoundException{return super.newApplication(loader,Application.class.getName(),context);}
    public void callApplicationOnCreate(Application app){super.callApplicationOnCreate(app);try{getTargetContext().getClassLoader().loadClass("mod.clean.CleanApp").getMethod("install",Application.class).invoke(null,app);}catch(Exception e){throw new RuntimeException(e);}begin();}
    public void onCreate(Bundle args){super.onCreate(args);begin();}
    public void onStart(){
        Bundle result=new Bundle();Object originalUsers=null;Field users=null;
        try {
            progress("plain-Application harness against installed production DEX; no native startup or UI assertion");
            check(cls("mod.clean.CleanApp").getField("context").get(null)!=null,"production helper initialized in harness");
            Class<?> bridge=cls("mod.clean.NativeBridge");
            cls("com.ss.android.ugc.aweme.AccountService").getMethod("LJIIJ");cases++;
            cls("X.0qFC").getMethod("LIZ");cls("X.0qAl").getMethod("LIZIZ",String.class);cls("X.0qAl").getMethod("LJFF",cls("X.0BVW"));cases++;
            Object text=cls("com.ss.android.ugc.aweme.im.message.content.TextContent").getMethod("obtain",String.class).invoke(null,"fixture");check(text!=null,"native text content construction");
            cls("X.0qAl").getMethod("LIZLLL",cls("X.0BcJ"));cls("X.0qAl").getMethod("LJIIZILJ",java.util.Map.class);cls("X.0qAl").getMethod("LJIIIIZZ",java.util.Map.class);cases++;
            users=bridge.getDeclaredField("userService");users.setAccessible(true);originalUsers=users.get(null);FakeUser fake=new FakeUser();users.set(null,fake);
            Context context=getTargetContext();SharedPreferences prefs=context.getSharedPreferences("clean_preferences",0);String cid="fixture-cid-"+System.nanoTime();
            prefs.edit().putBoolean("paired|1000|"+cid,true).putBoolean("peer|1000|"+cid,true).commit();
            Class<?> model=cls("X.0BVS");Object message=model.getConstructor().newInstance();
            call(message,"setMsgId",101L);call(message,"setSender",1000L);call(message,"setConversationId",cid);call(message,"setCreatedAt",System.currentTimeMillis());call(message,"setContent","{\"text\":\"original\"}");
            check(new JSONObject((String)call(message,"getContent")).getString("text").equals("original"),"ordinary content unchanged");
            Class<?> hooks=cls("mod.clean.MessageHooks");Method consume=hooks.getDeclaredMethod("consume",String.class,String.class,String.class,String.class);consume.setAccessible(true);
            prefs.edit().putBoolean("peer|1000|"+cid,false).commit();consume.invoke(null,"1000",cid,"2000","{\"op\":\"ack\",\"nonce\":\"fixture\"}");
            check(prefs.getBoolean("peer|1000|"+cid,false),"paired acknowledgement enables peer without sending messages");
            consume.invoke(null,"1000",cid,"2000","{\"op\":\"edit\",\"id\":101,\"rev\":1,\"text\":\"forged\"}");
            check(new JSONObject((String)call(message,"getContent")).getString("text").equals("original"),"foreign sender cannot edit target");
            consume.invoke(null,"1000",cid,"1000","{\"op\":\"edit\",\"id\":101,\"rev\":1,\"text\":\"edited\"}");
            check(new JSONObject((String)call(message,"getContent")).getString("text").equals("edited"),"paired edit renders in real SDK model");
            consume.invoke(null,"1000",cid,"1000","{\"op\":\"edit\",\"id\":101,\"rev\":1,\"text\":\"replayed\"}");
            check(new JSONObject((String)call(message,"getContent")).getString("text").equals("edited"),"replay rejected");
            consume.invoke(null,"1000",cid,"1000","{\"op\":\"delete\",\"id\":101,\"rev\":2}");
            check(Boolean.TRUE.equals(call(message,"isDeleted")),"delete reflected by real isDeleted");
            check(((Number)call(message,"getDeleted")).intValue()==1,"delete reflected by real getDeleted");
            fake.id="1001";
            check(!Boolean.TRUE.equals(call(message,"isDeleted")),"account-scoped delete state");
            check(new JSONObject((String)call(message,"getContent")).getString("text").equals("original"),"account-scoped edit state");
            fake.id="1000";consume.invoke(null,"1000",cid,"1000","{\"op\":\"edit\",\"id\":101,\"rev\":3,\"text\":\"resurrected\"}");
            check(Boolean.TRUE.equals(call(message,"isDeleted")),"delete tombstone does not resurrect");
            prefs.edit().putBoolean("paired|1000|"+cid,false).commit();
            check(!Boolean.TRUE.equals(call(message,"isDeleted"))&&new JSONObject((String)call(message,"getContent")).getString("text").equals("original"),"disabling paired mode restores stock rendering");
            final boolean[] rejected={false};Class<?> completion=cls("mod.clean.NativeBridge$Completion");
            Object receiver=Proxy.newProxyInstance(completion.getClassLoader(),new Class<?>[]{completion},new InvocationHandler(){public Object invoke(Object p,Method method,Object[] args){if(method.getName().equals("finished"))rejected[0]=Boolean.FALSE.equals(args[0]);return null;}});
            bridge.getMethod("send",String.class,String.class,String.class,java.util.Map.class,completion).invoke(null,"1001",cid,"fixture",java.util.Collections.emptyMap(),receiver);
            check(rejected[0],"native sender rejects mismatched account before accessing SDK");
            users.set(null,originalUsers);users=null;
            PackageInfo info=context.getPackageManager().getPackageInfo(context.getPackageName(),PackageManager.GET_SERVICES);
            boolean service=false;for(ServiceInfo s:info.services)if(s.name.equals("mod.clean.StreakJob"))service="android.permission.BIND_JOB_SERVICE".equals(s.permission);check(service,"job service has system binding permission");
            Class<?> updates=cls("mod.clean.UpdateChannel");Method certs=updates.getDeclaredMethod("certificates",PackageInfo.class);certs.setAccessible(true);
            PackageInfo installed=context.getPackageManager().getPackageInfo(context.getPackageName(),PackageManager.GET_SIGNING_CERTIFICATES);
            PackageInfo archive=context.getPackageManager().getPackageArchiveInfo(context.getApplicationInfo().sourceDir,PackageManager.GET_SIGNING_CERTIFICATES);
            check(archive!=null&&Boolean.TRUE.equals(updates.getMethod("sameSigners",byte[][].class,byte[][].class).invoke(null,certs.invoke(null,installed),certs.invoke(null,archive))),"actual installed/archive APK signer validation");
            java.io.File location=new java.io.File(context.getExternalFilesDir(android.os.Environment.DIRECTORY_DOWNLOADS),"probe-update.apk");
            android.net.Uri uri=(android.net.Uri)cls("androidx.core.content.FileProvider").getMethod("getUriForFile",Context.class,String.class,java.io.File.class).invoke(null,context,"com.zhiliaoapp.musically.fileprovider",location);
            check("content".equals(uri.getScheme()),"existing production FileProvider accepts update download path");
            Class<?> chooser=cls("X.1EAt");Method resolve=chooser.getMethod("LJFF",String.class);
            check("google_web".equals(resolve.invoke(null,"google")),"actual native Google chooser selects browser OAuth");
            check("google_web".equals(resolve.invoke(null,"google_onetap")),"actual native Google credential alias selects browser OAuth");
            check("google_web".equals(resolve.invoke(null,"google_web")),"explicit Google browser provider remains supported");
            check("facebook".equals(resolve.invoke(null,"facebook"))&&"line".equals(resolve.invoke(null,"line")),"actual non-Google provider selection retained");
            check("google".equals(chooser.getMethod("LIZLLL",String.class).invoke(null,"google_web")),"original browser callback maps to Google account backend");
            Class<?> routing=cls("mod.clean.AuthRouting");Method normalize=routing.getMethod("normalizeIntent",Intent.class);
            Intent google=new Intent().putExtra("platform","google_onetap").putExtra("is_login",true).putExtra("enter_method","fixture");normalize.invoke(null,google);
            check("google".equals(google.getStringExtra("platform"))&&google.getBooleanExtra("is_login",false)&&"fixture".equals(google.getStringExtra("enter_method")),"Google normalization preserves login and caller context");
            Intent email=new Intent().putExtra("platform","email").putExtra("is_login",true).putExtra("email","fixture@example.invalid");normalize.invoke(null,email);
            check("email".equals(email.getStringExtra("platform"))&&"fixture@example.invalid".equals(email.getStringExtra("email"))&&email.getBooleanExtra("is_login",false),"email login parameters remain unchanged");
            Intent passkey=new Intent().putExtra("platform","passkey");normalize.invoke(null,passkey);check("passkey".equals(passkey.getStringExtra("platform")),"passkey authentication retained");
            Intent callback=new Intent(Intent.ACTION_VIEW,android.net.Uri.parse("com.googleusercontent.apps.616463764658-p01hhcj82u4mqjnp1oca04i3o67fjsm1:/oauthredirect")).addCategory(Intent.CATEGORY_BROWSABLE).setPackage(context.getPackageName());
            ResolveInfo redirect=context.getPackageManager().resolveActivity(callback,PackageManager.MATCH_DEFAULT_ONLY);
            check(redirect!=null&&"net.openid.appauth.RedirectUriReceiverActivity".equals(redirect.activityInfo.name)&&redirect.activityInfo.exported,"existing Google OAuth return URI resolves to installed APK");
            ResolveInfo browser=context.getPackageManager().resolveActivity(new Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://accounts.google.com")),PackageManager.MATCH_DEFAULT_ONLY);
            check(browser!=null,"browser for existing OAuth flow is available");
            check(installed.getLongVersionCode()==2024701041L,"login fix has greater installable versionCode");
            result.putString("result","PASS "+cases+" checks; method bindings and actual SDK message hooks under plain-Application harness. Native app startup/UI and live sending are separate checks. No messages sent.");
            finish(Activity.RESULT_OK,result);
        }catch(Throwable failure){result.putString("result","FAIL after "+cases+" checks: "+failure.toString());result.putString("stack",android.util.Log.getStackTraceString(failure));finish(Activity.RESULT_CANCELED,result);}
        finally{if(users!=null)try{users.set(null,originalUsers);}catch(Exception ignored){}}
    }
}
