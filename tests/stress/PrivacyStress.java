import mod.privacy.*;
import com.ss.android.ugc.aweme.framework.services.ServiceManager;
import java.util.*;
import java.util.concurrent.*;
import java.lang.management.*;
import java.io.*;

/** Local component simulation, NOT video decoding, GPU load or TikTok-server traffic. */
public final class PrivacyStress {
    static final long SEED=0x74544b20261017L;
    static long operations,checks;
    static final ArrayList<String> findings=new ArrayList<String>();
    static void require(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    public static class Item {
        final String aid;final boolean ad;
        public Item(String aid){this(aid,false);}public Item(String aid,boolean ad){this.aid=aid;this.ad=ad;}
        public String getAid(){return aid;} public boolean isAd(){return ad;}
    }
    public static class Data {
        List<?> items;Data(List<?> items){this.items=items;}
        public List<?> getItems(){return items;}public void setItems(List<?> values){items=values;}
    }
    public static class Model {public int mListQueryType=1;public boolean mIsNewDataEmpty;public Object mData;public int LLJILJIL=0;Model(List<?> items){mData=new Data(items);}}
    public static class Adapter {
        List<?> items=Collections.emptyList();public int getCount(){return items.size();}public Object getItem(int index){return items.get(index);}
    }
    public static class Pager {
        final Adapter adapter=new Adapter();int current=0;
        public Adapter getAdapter(){return adapter;}public int getCurrentItem(){return current;}
    }
    public static class Ability {final Pager pager;Ability(Pager pager){this.pager=pager;}public Pager bc1(){return pager;}}
    public static class Panel {final Ability ability;Panel(Pager pager){ability=new Ability(pager);}public Ability Ic(){return ability;}}
    public static class Cell {
        public Object LLJJJJLIIL;final Panel panel;String event="homepage_hot";
        Cell(Pager pager,Item item){LLJJJJLIIL=item;panel=new Panel(pager);}public String getEventType(){return event;}public Panel sw2(){return panel;}
    }
    public static class Overload {public String choose(String s){return "string";}public String choose(Integer i){return "integer";}}
    static String id(Object value){return value==null?"":((Item)value).aid;}
    static long gcCount(){long n=0;for(GarbageCollectorMXBean b:ManagementFactory.getGarbageCollectorMXBeans())n+=Math.max(0,b.getCollectionCount());return n;}
    static long heap(){Runtime r=Runtime.getRuntime();return r.totalMemory()-r.freeMemory();}
    static long percentile(long[] values,double p){long[] sorted=values.clone();Arrays.sort(sorted);return sorted[(int)Math.min(sorted.length-1,Math.floor(sorted.length*p))];}
    static void boundaryRegressions()throws Exception {
        Pager pager=new Pager();Cell good=new Cell(pager,new Item("previous"));
        PrivacyRuntime.preferences.enabled=true;ServiceManager.uid="account-A";
        NativeRefresh.selected(good);
        Cell bad=new Cell(pager,new Item(""));NativeRefresh.selected(bad);
        Model missing=new Model(Arrays.asList(new Item("fresh")));NativeRefresh.begin(missing);NativeRefresh.finish(missing);
        if(((Data)missing.mData).items.size()!=1)findings.add("invalid_current_cell_resurrects_previous_video");
        NativeRefresh.selected(good);Model off=new Model(Arrays.asList(new Item("fresh")));
        NativeRefresh.begin(off);PrivacyRuntime.preferences.enabled=false;NativeRefresh.finish(off);
        if(((Data)off.mData).items.size()!=1)findings.add("disabling_retention_during_refresh_ignored");
        PrivacyRuntime.preferences.enabled=true;
        boolean overloaded=true;for(Object value:new Object[]{"text",Integer.valueOf(1)})try {
            String expected=value instanceof String?"string":"integer";
            overloaded&=expected.equals(NativeRefresh.call(new Overload(),"choose",value));
        }catch(Exception e){overloaded=false;}
        if(!overloaded)findings.add("reflection_selects_overload_by_arity_only");
    }
    static long[] modelSessions(int count)throws Exception {
        Random rng=new Random(SEED);long[] duration=new long[count];
        for(int s=0;s<count;s++) {
            long start=System.nanoTime();ServiceManager.uid="account-"+(s%13);PrivacyRuntime.preferences.enabled=true;
            Pager pager=new Pager();Item previous=new Item("old-"+s);Cell cell=new Cell(pager,previous);NativeRefresh.selected(cell);
            for(int p=0;p<32;p++){NativeRefresh.progress(cell,(p*3.0f)%100);operations++;}
            int size=1+rng.nextInt(128);ArrayList<Item> incoming=new ArrayList<Item>(size+2);
            for(int i=0;i<size;i++)incoming.add(new Item("fresh-"+s+"-"+i));
            if((s&1)==0)incoming.add(previous);if((s&3)==0)incoming.add(previous);
            Model model=new Model(Collections.unmodifiableList(incoming));int mode=s%8;
            if(mode==1)model.mListQueryType=4;
            if(mode==2)PrivacyRuntime.preferences.enabled=false;
            if(mode==3){incoming.clear();model.mIsNewDataEmpty=true;}
            NativeRefresh.begin(model);
            if(mode==4)ServiceManager.uid="changed-"+s;
            NativeRefresh.finish(model);List<?> out=((Data)model.mData).items;
            boolean retain=mode!=1&&mode!=2&&mode!=3&&mode!=4;
            if(retain) {
                require(out!=incoming,"response list isolation");require(id(out.get(0)).equals(previous.aid),"previous video available above new feed: session="+s+" mode="+mode+" first="+id(out.get(0))+" count="+out.size());
                int duplicate=0;for(Object item:out)if(id(item).equals(previous.aid))duplicate++;
                require(duplicate==1,"previous video deduplicated");pager.adapter.items=out;
                require(NativeRefresh.initialIndex(pager,0)==1,"refresh initially displays first fresh video");
                require(NativeRefresh.initialIndex(pager,0)==1,"repeated initialization stays on fresh video");
                NativeRefresh.userNavigation();require(NativeRefresh.initialIndex(pager,0)==0,"back swipe remains available");
                require(out.get(1)==incoming.get(0),"fresh ordering preserved");
            }else require(out.size()==incoming.size(),"pagination/disabled/empty/account mismatch do not inject");
            // The real UI owns its current cell strongly; preserve that lifetime in this fixture.
            require(NativeRefresh.current(cell),"fixture current cell remains attached for the whole session");
            operations+=8+out.size();duration[s]=System.nanoTime()-start;
        }
        return duration;
    }
    static long concurrent(int threads,int count)throws Exception {
        ExecutorService pool=Executors.newFixedThreadPool(threads);CountDownLatch go=new CountDownLatch(1);
        ArrayList<Future<Long>> futures=new ArrayList<Future<Long>>();
        for(int t=0;t<threads;t++){final int tid=t;futures.add(pool.submit(new Callable<Long>(){public Long call()throws Exception{
            go.await();long done=0;Random rng=new Random(SEED+tid);for(int i=0;i<count;i++) {
                RefreshPolicy.Selection selection=new RefreshPolicy.Selection("previous","fresh");
                if(selection.index(0,"previous","fresh",true)!=1)throw new AssertionError("concurrent initial selection");
                selection.release();if(selection.index(0,"previous","fresh",true)!=0)throw new AssertionError("concurrent release");
                String url=(i%3==0)?"https://log-va.tiktokv.com/service/2/app_log/?id="+rng.nextInt():"https://api.tiktokv.com/aweme/v2/feed/?id="+rng.nextInt();
                if(PrivacyNet.blocked(url)!=(i%3==0))throw new AssertionError("concurrent URL policy");
                if(!PermissionPolicy.allow(new String[]{"android.permission.CAMERA"},10000,9999,true))throw new AssertionError("concurrent permission policy");
                done+=4;
            }return done;}}));}
        go.countDown();long done=0;try{for(Future<Long> f:futures)done+=f.get(90,TimeUnit.SECONDS);}finally{pool.shutdownNow();}
        return done;
    }
    public static void main(String[] args)throws Exception {
        int sessions=Integer.parseInt(args[0]);String output=args[1];boolean strict=args.length>2&&args[2].equals("strict");
        long started=System.nanoTime();boundaryRegressions();modelSessions(3000);operations=0;checks=0;
        System.gc();Thread.sleep(40);long heapBefore=heap(),gcBefore=gcCount();
        long[] durations=modelSessions(sessions);long concurrentOps=concurrent(8,25000);operations+=concurrentOps;
        System.gc();Thread.sleep(40);long heapAfter=heap();
        String json="{\n  \"scope\":\"JVM production helpers with Android/TikTok fixtures; no GPU, media decoding or server load\",\n"+
          "  \"seed\":"+SEED+",\n  \"sessions\":"+sessions+",\n  \"operations\":"+operations+",\n  \"checks\":"+checks+",\n  \"concurrent_threads\":8,\n  \"concurrent_operations\":"+concurrentOps+",\n"+
          "  \"elapsed_seconds\":"+((System.nanoTime()-started)/1e9)+",\n  \"session_p50_us\":"+(percentile(durations,.50)/1000.0)+",\n  \"session_p95_us\":"+(percentile(durations,.95)/1000.0)+",\n  \"session_p99_us\":"+(percentile(durations,.99)/1000.0)+",\n  \"session_max_us\":"+(percentile(durations,1)/1000.0)+",\n"+
          "  \"heap_before_bytes\":"+heapBefore+",\n  \"heap_after_gc_bytes\":"+heapAfter+",\n  \"gc_collections\":"+(gcCount()-gcBefore)+",\n  \"findings\":[";
        for(int i=0;i<findings.size();i++){if(i>0)json+=",";json+="\""+findings.get(i)+"\"";}json+="]\n}";
        try(Writer w=new OutputStreamWriter(new FileOutputStream(output),"UTF-8")){w.write(json);}System.out.println(json);
        if(strict&&!findings.isEmpty())throw new AssertionError(findings.toString());
    }
}
