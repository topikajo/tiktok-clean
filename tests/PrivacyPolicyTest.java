import mod.privacy.*;
import java.util.*;

public final class PrivacyPolicyTest {
    static int cases;
    static void check(boolean value,String text){if(!value)throw new AssertionError(text);cases++;}
    public static void main(String[] args){
        String[] deny={"https://tiktokyou.yzewe.ru/api/v1/updates", "https://tiktokyou-fb.yzewe.ru/api/v1/badges",
            "https://events.appsflyer.com/v1", "https://monitorsdk.appsflyersdk.com/remote-debug/exception-manager",
            "https://app-measurement.com/a", "https://log-va.tiktokv.com/service/2/app_log/?uid=123",
            "https://log16-normal-useast1a.tiktokv.com/service/2/log_settings/", "https://rtlog-sg.tiktokv.com/batch",
            "https://mon-boot.tiktokv.com/monitor/collect/c/crash", "https://api.tiktokv.com/service/2/device_sdk/stats_collect/"};
        for(String url:deny)check(PrivacyNet.blocked(url)&&PrivacyNet.rewrite(url).equals(PrivacyNet.BLOCKED),"telemetry blocked: "+url);
        String[] allow={"https://log-va.tiktokv.com/service/2/device_register/", "https://api-core-boot.tiktokv.com/passport/auth/login/",
            "https://api-core.tiktokv.com/aweme/v2/feed/", "https://frontier-va.tiktokv.com/ws/v2", "https://p16-tiktokcdn.com/media/video.mp4",
            "https://accounts.google.com/o/oauth2/v2/auth", "https://tiktokyou.yzewe.ru.attacker.test/api/v1/updates"};
        for(String url:allow)check(!PrivacyNet.blocked(url)&&PrivacyNet.rewrite(url)==url,"functional request preserved: "+url);
        check(PrivacyNet.rewrite(null)==null,"null URL stays null");
        String[] camera={"android.permission.CAMERA"};
        check(!PermissionPolicy.allow(camera,10000,0,true),"startup has no permission intent");
        check(PermissionPolicy.allow(camera,10000,9999,true),"foreground camera action allowed");
        check(PermissionPolicy.allow(new String[]{"android.permission.CAMERA","android.permission.RECORD_AUDIO"},10000,9999,true),"video recording group allowed after action");
        check(!PermissionPolicy.allow(camera,10000,9999,false),"background never prompts");
        check(!PermissionPolicy.allow(camera,10000,10001,true),"clock reversal denied");
        check(!PermissionPolicy.allow(camera,15001,10000,true),"expired action denied");
        check(!PermissionPolicy.allow(new String[]{"android.permission.READ_PHONE_STATE"},10000,9999,true),"phone identifiers denied");
        check(!PermissionPolicy.allow(new String[]{"android.permission.ACCESS_FINE_LOCATION"},10000,9999,true),"location denied");
        check(!PermissionPolicy.allow(new String[]{"android.permission.CAMERA","unknown"},10000,9999,true),"mixed unsafe permission bundle denied");
        RefreshPolicy.Id ids=new RefreshPolicy.Id(){public String of(Object v){return v==null?null:String.valueOf(v);}};
        List<String> incoming=Collections.unmodifiableList(Arrays.asList("new1","old","new2","old"));
        List<?> out=RefreshPolicy.retain(incoming,"old",ids,true,true);
        check(out.equals(Arrays.asList("old","new1","new2")),"previous video behind initial fresh selection; fresh order and de-duplication");
        check(incoming.equals(Arrays.asList("new1","old","new2","old")),"incoming list never mutated");
        check(RefreshPolicy.retain(incoming,"old",ids,false,true)==incoming,"pagination does not retain old video");
        check(RefreshPolicy.retain(incoming,"old",ids,true,false)==incoming,"account change does not retain old video");
        check(RefreshPolicy.retain(incoming,null,ids,true,true)==incoming,"first launch has no old video");
        check(RefreshPolicy.retain(Collections.emptyList(),"old",ids,true,true).isEmpty(),"failed/empty refresh does not fabricate fresh content");
        check(RefreshPolicy.retain(Arrays.asList("n",null),"old",ids,true,true).equals(Arrays.asList("old","n",null)),"unknown null item preserved");
        RefreshPolicy.Selection selection=new RefreshPolicy.Selection("old","new1");
        check(selection.index(0,"old","stale",true)==0 && !selection.consumed(),"old adapter cannot consume refresh selection");
        check(selection.index(2,"old","new1",true)==2 && !selection.consumed(),"intermediate index cannot consume initial reset");
        check(selection.index(0,"old","new1",false)==0 && !selection.consumed(),"account mismatch does not jump");
        int start=selection.index(0,"old","new1",true);
        check(start==1 && out.get(start).equals("new1"),"refresh displays first NEW video immediately");
        check(out.get(start-1).equals("old"),"ordinary previous-page swipe reaches retained video");
        check(selection.index(0,"old","new1",true)==1,"repeated native startup resets stay on fresh video before first frame");
        selection.displayed("new1");
        check(selection.index(0,"old","new1",true)==0,"back swipe stays on previous video without a repeated jump");
        check(new RefreshPolicy.Selection("old","old").index(0,"old","old",true)==0,"no jump when refresh has no distinct new video");
        check(new RefreshPolicy.Selection("","new").index(0,"","new",true)==0,"invalid previous identity does not change selection");
        RefreshPolicy.Selection alreadyShown=new RefreshPolicy.Selection("old","new1");alreadyShown.displayed("new1");
        check(alreadyShown.index(0,"old","new1",true)==0,"native selection of fresh video cannot trap the next back swipe");
        RefreshPolicy.Selection userSwipe=new RefreshPolicy.Selection("old","new1");userSwipe.release();
        check(userSwipe.index(0,"old","new1",true)==0,"user gesture releases refresh guard even before the first frame");
        System.out.println("PASS "+cases+" privacy / permission / refresh policy cases");
    }
}
