package mod.privacy.stress;
import android.app.*;
import android.content.*;
import android.os.*;
import android.util.Printer;
import java.lang.ref.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import org.json.*;

/** Actual installed helper DEX and Android message queue; native TikTok startup excluded. */
public final class PrivacyStressInstrumentation extends Instrumentation {
    boolean begun,applicationReady,configurationReady;Bundle arguments;
    public Application newApplication(ClassLoader loader,String name,Context c)throws InstantiationException,IllegalAccessException,ClassNotFoundException {
        return super.newApplication(loader,Application.class.getName(),c);
    }
    public void callApplicationOnCreate(Application app){super.callApplicationOnCreate(app);try{cls("mod.privacy.PrivacyRuntime").getMethod("install",Application.class).invoke(null,app);}catch(Exception e){throw new RuntimeException(e);}applicationReady=true;begin();}
    public void onCreate(Bundle args){super.onCreate(args);arguments=args;configurationReady=true;begin();}
    private synchronized void begin(){if(begun||!applicationReady||!configurationReady)return;begun=true;new Thread(new Runnable(){public void run(){onStart();}},"PrivacyStress").start();}
    Class<?> cls(String n)throws Exception{return getTargetContext().getClassLoader().loadClass(n);}
    static Field field(Class<?> c,String n)throws Exception{Field f=c.getDeclaredField(n);f.setAccessible(true);return f;}
    static int queuedFrameMessages() {
        final int[] n={0};Looper.getMainLooper().dump(new Printer(){public void println(String s){if(s.contains("callback=mod.privacy.FrameActions"))n[0]++;}},"");return n[0];
    }
    static long p(long[] a,double percentile){long[] copy=a.clone();Arrays.sort(copy);return copy[Math.min(copy.length-1,(int)(copy.length*percentile))];}
    void event(String message){Bundle b=new Bundle();b.putString("progress",message);sendStatus(1,b);}
    public void onStart() {
        Bundle result=new Bundle();int resultCode=Activity.RESULT_CANCELED;final CountDownLatch release=new CountDownLatch(1);
        Handler handler=null;Object oldActive=null;Field active=null;
        try {
            String mode=arguments==null?"fixed":arguments.getString("mode","fixed");boolean strict=!mode.equals("baseline");
            Class<?> refresh=cls("mod.privacy.NativeRefresh"),frames=cls("mod.privacy.FrameActions");
            handler=(Handler)cls("mod.privacy.PrivacyRuntime").getField("main").get(null);
            active=field(refresh,"active");oldActive=active.get(null);final Object marker=new Object();active.set(null,new WeakReference<Object>(marker));
            final CountDownLatch entered=new CountDownLatch(1);
            handler.post(new Runnable(){public void run(){entered.countDown();try{release.await(6,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}});
            if(!entered.await(2,TimeUnit.SECONDS))throw new AssertionError("main loop barrier failed");
            Method pause=frames.getMethod("paused",Object.class),resume=frames.getMethod("resumed",Object.class);
            int calls=20000;long begin=System.nanoTime();
            for(int i=0;i<calls;i++)pause.invoke(null,marker);
            int pending=queuedFrameMessages();resume.invoke(null,marker);int afterResume=queuedFrameMessages();
            long queueMs=(System.nanoTime()-begin)/1000000;
            // Cancel only this fork's test handler before unblocking: no Buttons or gallery items are created.
            handler.removeCallbacksAndMessages(null);release.countDown();waitForIdleSync();active.set(null,oldActive);
            if(strict&&(pending>1||afterResume!=0))throw new AssertionError("frame queue backlog "+pending+" after resume "+afterResume);
            event("frame queue: "+calls+" callbacks, pending="+pending+", afterResume="+afterResume);
            Class<?> aweme=cls("com.ss.android.ugc.aweme.feed.model.Aweme");Object item=aweme.getConstructor().newInstance();
            aweme.getMethod("setAid",String.class).invoke(item,"offline-stress-fixture");
            Method id=refresh.getMethod("id",Object.class);for(int i=0;i<1000;i++)id.invoke(null,item);
            int iterations=mode.equals("baseline")?20000:100000;long[] times=new long[iterations];
            long heapBefore=Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory();
            long gcBefore=Long.parseLong(android.os.Debug.getRuntimeStat("art.gc.gc-count"));long start=System.nanoTime();
            for(int i=0;i<iterations;i++) {
                long t=System.nanoTime();Object value=id.invoke(null,item);times[i]=System.nanoTime()-t;
                if(!"offline-stress-fixture".equals(value))throw new AssertionError("wrong production reflection result");
                if(i%20000==0)event("installed Aweme reflection "+i+"/"+iterations);
            }
            long elapsed=System.nanoTime()-start;long heapAfter=Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory();
            long gcAfter=Long.parseLong(android.os.Debug.getRuntimeStat("art.gc.gc-count"));
            JSONObject report=new JSONObject();report.put("scope","Installed APK helpers, actual Aweme class and Android UI queue; no real feed, decoder or GPU");
            report.put("mode",mode);report.put("frame_pause_callbacks",calls);report.put("frame_pending_messages",pending);report.put("frame_pending_after_resume",afterResume);report.put("frame_queue_test_ms",queueMs);
            report.put("reflection_operations",iterations);report.put("reflection_total_ms",elapsed/1e6);report.put("reflection_p50_us",p(times,.5)/1000.0);report.put("reflection_p95_us",p(times,.95)/1000.0);report.put("reflection_p99_us",p(times,.99)/1000.0);report.put("reflection_max_us",p(times,1)/1000.0);
            report.put("heap_before_bytes",heapBefore);report.put("heap_after_bytes",heapAfter);report.put("gc_collections",gcAfter-gcBefore);report.put("main_heartbeat_verified",true);
            result.putString("stress_json",report.toString());resultCode=Activity.RESULT_OK;
        }catch(Throwable e){result.putString("failure",e.toString());java.io.StringWriter trace=new java.io.StringWriter();e.printStackTrace(new java.io.PrintWriter(trace));result.putString("trace",trace.toString());}
        finally{release.countDown();if(handler!=null)handler.removeCallbacksAndMessages(null);if(active!=null)try{active.set(null,oldActive);}catch(Exception ignored){}}
        finish(resultCode,result);
    }
}
