package mod.clean;

import android.app.job.*;
import android.content.SharedPreferences;
import java.util.*;
import java.util.concurrent.atomic.*;

/** Uses Android's scheduler; force-stop and Doze remain platform limitations. */
public final class StreakJob extends JobService {
    private static final AtomicBoolean running=new AtomicBoolean();
    private JobParameters active;
    public boolean onStartJob(final JobParameters params){
        active=params;
        boolean started=tick(new Runnable(){public void run(){if(active==params){active=null;jobFinished(params,false);}}});
        if(!started)active=null;
        return started;
    }
    public boolean onStopJob(JobParameters params){if(active==params)active=null;return true;}
    public static void tick(){tick(null);}
    static boolean tick(final Runnable completion){
        if(CleanApp.context==null||!running.compareAndSet(false,true))return false;
        final AtomicBoolean done=new AtomicBoolean();
        final Runnable finish=new Runnable(){public void run(){if(done.compareAndSet(false,true)){running.set(false);if(completion!=null)completion.run();}}};
        // Pending state survives timeout/process death; never blindly repeat uncertain sends.
        CleanApp.main.postDelayed(finish,90000);
        CleanApp.main.post(new Runnable(){public void run(){
          final AtomicInteger outstanding=new AtomicInteger(1);
          final Runnable settle=new Runnable(){public void run(){if(outstanding.decrementAndGet()==0){CleanApp.main.removeCallbacks(finish);CleanApp.main.post(finish);}}};
          try{
            final String owner=NativeBridge.uid();if(owner.isEmpty())return;
            final long now=System.currentTimeMillis();
            for(String key:CleanApp.prefs().getAll().keySet()){
                String prefix="auto|"+owner+"|";if(!key.startsWith(prefix))continue;
                final String cid=key.substring(prefix.length());
                long last=Math.max(CleanApp.prefs().getLong(CleanApp.key(owner,cid,"last"),0),CleanApp.prefs().getLong(CleanApp.key(owner,cid,"manual"),0));
                long pending=CleanApp.prefs().getLong(CleanApp.key(owner,cid,"pending"),0);
                if(CleanApp.prefs().getLong(CleanApp.key(owner,cid,"retry"),0)>now||!Policy.due(CleanApp.prefs().getBoolean(key,false),owner,NativeBridge.uid(),last,pending,now))continue;
                // Record before dispatch: an uncertain send is never blindly repeated after restart.
                if(!CleanApp.prefs().edit().putLong(CleanApp.key(owner,cid,"pending"),now).commit())continue;
                outstanding.incrementAndGet();
                NativeBridge.send(owner,cid,"🔥",Collections.singletonMap(MessageHooks.AUTO,"1"),new NativeBridge.Completion(){public void finished(boolean ok,String error){
                    try{
                        SharedPreferences.Editor edit=CleanApp.prefs().edit().putLong(CleanApp.key(owner,cid,"pending"),0).putLong(CleanApp.key(owner,cid,"retry"),ok?0:now+30*60*1000L).putString(CleanApp.key(owner,cid,"status"),ok?"Огонёк отправлен":error);
                        if(ok)edit.putLong(CleanApp.key(owner,cid,"last"),now);edit.commit();
                    }finally{settle.run();}
                }});
            }
        }finally{settle.run();}}});
        return true;
    }
}
