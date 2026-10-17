package mod.privacy;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.net.Uri;
import android.os.*;
import android.provider.MediaStore;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.lang.ref.WeakReference;
import java.util.concurrent.*;

/** Export only the video's TextureView/SurfaceView, with no UI screenshot fallback. */
public final class FrameActions {
    private static final ExecutorService io=Executors.newSingleThreadExecutor();
    private static WeakReference<View> button=new WeakReference<View>(null);
    private static WeakReference<Object> shownCell=new WeakReference<Object>(null);
    private static boolean busy;
    private static final Object uiLock=new Object();
    private static WeakReference<Object> requestedCell=new WeakReference<Object>(null);
    private static boolean wantPaused,uiQueued;
    private static long uiRevision;
    private static final Runnable updateUi=new Runnable(){public void run(){
        final Object cell;final boolean pause;final long revision;final View old;
        synchronized(uiLock){
            uiQueued=false;cell=requestedCell.get();pause=wantPaused;revision=uiRevision;
            old=button.get();button=new WeakReference<View>(null);shownCell=new WeakReference<Object>(null);
        }
        if(old!=null && old.getParent() instanceof ViewGroup)((ViewGroup)old.getParent()).removeView(old);
        if(pause && cell!=null && NativeRefresh.current(cell))showPaused(cell,revision);
    }};
    private static void queueUi(){if(!uiQueued){uiQueued=true;PrivacyRuntime.main.post(updateUi);}}
    public static void resumed(Object cell) {
        synchronized(uiLock){
            if(cell!=null && shownCell.get()!=cell && requestedCell.get()!=cell)return;
            if(!wantPaused && button.get()==null && !uiQueued)return;
            wantPaused=false;requestedCell=new WeakReference<Object>(null);uiRevision++;
            if(button.get()==null){if(uiQueued){PrivacyRuntime.main.removeCallbacks(updateUi);uiQueued=false;}}
            else queueUi();
        }
    }
    public static void paused(final Object cell) {
        if(!NativeRefresh.current(cell))return;
        synchronized(uiLock){
            if(wantPaused && requestedCell.get()==cell && (uiQueued || button.get()!=null))return;
            wantPaused=true;requestedCell=new WeakReference<Object>(cell);uiRevision++;queueUi();
        }
    }
    private static void showPaused(final Object cell,long revision) {
        try {
            if(!NativeRefresh.current(cell))return;
            final Activity activity=(Activity)NativeRefresh.call(cell,"getActivity");
            if(activity==null || PrivacyRuntime.foregroundActivity()!=activity || activity.isFinishing())return;
            View video=(View)NativeRefresh.call(cell,"getVideoView");
            if(surface(video)==null || NativeRefresh.id(NativeRefresh.field(cell,"LLJJJJLIIL")).isEmpty())return;
            FrameLayout content=video instanceof FrameLayout?(FrameLayout)video:null;
            View root=activity.findViewById(android.R.id.content);
            // Keep the action beneath login, onboarding and settings overlays.
            for(ViewParent parent=video.getParent();content==null && parent instanceof View && parent!=root;parent=parent.getParent())
                if(parent instanceof FrameLayout)content=(FrameLayout)parent;
            if(content==null || content==root)return;
            Button action=new Button(activity);action.setText("Кадр");action.setAllCaps(false);action.setContentDescription("Сохранить кадр видео без интерфейса");
            FrameLayout.LayoutParams params=new FrameLayout.LayoutParams(-2,-2,Gravity.TOP|Gravity.START);
            params.leftMargin=Math.round(12*activity.getResources().getDisplayMetrics().density);
            params.topMargin=Math.round(64*activity.getResources().getDisplayMetrics().density);
            synchronized(uiLock){
                if(revision!=uiRevision || !wantPaused || requestedCell.get()!=cell)return;
                button=new WeakReference<View>(action);shownCell=new WeakReference<Object>(cell);
            }
            content.addView(action,params);
            action.setOnClickListener(new View.OnClickListener(){public void onClick(View view){capture(activity,cell);}});
        }catch(Exception ignored){}
    }
    private static View surface(View view) {
        if(view==null || !view.isShown() || view.getWidth()==0 || view.getHeight()==0)return null;
        Rect visible=new Rect();if(!view.getGlobalVisibleRect(visible))return null;
        if(view instanceof TextureView || view instanceof SurfaceView)return view;
        View best=null;long area=0;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++) {
            View child=surface(((ViewGroup)view).getChildAt(i));if(child==null)continue;
            long n=(long)child.getWidth()*child.getHeight();if(n>area){best=child;area=n;}
        }
        return best;
    }
    private static void capture(final Activity activity,Object cell) {
        if(!NativeRefresh.current(cell)){resumed(null);return;}
        if(busy)return;
        if(Build.VERSION.SDK_INT<29 && activity.checkSelfPermission("android.permission.WRITE_EXTERNAL_STORAGE")!=PackageManager.PERMISSION_GRANTED) {
            PrivacyRuntime.noteAction(activity);PrivacyRuntime.request(activity,new String[]{"android.permission.WRITE_EXTERNAL_STORAGE"},0x6342);
            Toast.makeText(activity,"После разрешения нажмите «Кадр» ещё раз",Toast.LENGTH_SHORT).show();return;
        }
        Bitmap allocated=null;
        try {
            View video=(View)NativeRefresh.call(cell,"getVideoView");final View view=surface(video);
            if(view==null){Toast.makeText(activity,"Кадр ещё не доступен — дождитесь загрузки видео",Toast.LENGTH_SHORT).show();return;}
            busy=true;
            // Bound memory use on large screens while preserving the video aspect ratio.
            float scale=Math.min(1f,2048f/Math.max(view.getWidth(),view.getHeight()));
            int w=Math.max(1,Math.round(view.getWidth()*scale)),h=Math.max(1,Math.round(view.getHeight()*scale));
            if(view instanceof TextureView) {
                allocated=((TextureView)view).getBitmap(w,h);if(allocated==null)throw new IOException("No decoded frame");save(activity,allocated);allocated=null;
            } else if(Build.VERSION.SDK_INT>=24) {
                final Bitmap frame=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
                allocated=frame;
                PixelCopy.request(((SurfaceView)view).getHolder().getSurface(),frame,new PixelCopy.OnPixelCopyFinishedListener(){public void onPixelCopyFinished(int status){
                    if(status==PixelCopy.SUCCESS)save(activity,frame);else{frame.recycle();busy=false;Toast.makeText(activity,"Не удалось получить кадр видео",Toast.LENGTH_SHORT).show();}
                }},PrivacyRuntime.main);
                allocated=null; // PixelCopy callback owns this bitmap after a successful request.
            }else {busy=false;Toast.makeText(activity,"Для этого видеоплеера нужен Android 7 или новее",Toast.LENGTH_SHORT).show();}
        }catch(OutOfMemoryError e){busy=false;Toast.makeText(activity,"Недостаточно памяти для кадра",Toast.LENGTH_SHORT).show();}
        catch(Exception e){busy=false;Toast.makeText(activity,"Не удалось сохранить кадр",Toast.LENGTH_SHORT).show();}
        finally{if(allocated!=null)allocated.recycle();}
    }
    public static Uri writeBitmap(Context context,Bitmap frame)throws IOException {
        ContentValues values=new ContentValues();values.put(MediaStore.Images.Media.DISPLAY_NAME,"TikTokClean_frame_"+System.currentTimeMillis()+".jpg");values.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");
        if(Build.VERSION.SDK_INT>=29){values.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/TikTokClean");values.put(MediaStore.Images.Media.IS_PENDING,1);}
        else {
            File directory=new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES),"TikTokClean");
            if(!directory.isDirectory() && !directory.mkdirs())throw new IOException("Cannot create gallery folder");
            values.put(MediaStore.Images.Media.DATA,new File(directory,values.getAsString(MediaStore.Images.Media.DISPLAY_NAME)).getAbsolutePath());
        }
        Uri uri=context.getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);if(uri==null)throw new IOException("Gallery insert failed");
        try {
            try(OutputStream out=context.getContentResolver().openOutputStream(uri)) {
                if(out==null || !frame.compress(Bitmap.CompressFormat.JPEG,95,out))throw new IOException("Frame write failed");
            }
            if(Build.VERSION.SDK_INT>=29){values.clear();values.put(MediaStore.Images.Media.IS_PENDING,0);context.getContentResolver().update(uri,values,null,null);}
            return uri;
        }catch(IOException|RuntimeException|OutOfMemoryError e){try{context.getContentResolver().delete(uri,null,null);}catch(RuntimeException ignored){}throw e;}
    }
    private static void save(final Activity activity,final Bitmap frame) {
        final Context context=activity.getApplicationContext();io.execute(new Runnable(){public void run(){
            String message;try{writeBitmap(context,frame);message="Кадр сохранён в Pictures/TikTokClean";}catch(Exception e){message="Не удалось сохранить кадр";}
            catch(OutOfMemoryError e){message="Недостаточно памяти для кадра";}
            finally{frame.recycle();}
            final String result=message;PrivacyRuntime.main.post(new Runnable(){public void run(){busy=false;if(!activity.isFinishing())Toast.makeText(activity,result,Toast.LENGTH_SHORT).show();}});
        }});
    }
}
