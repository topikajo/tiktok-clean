import mod.clean.FeedAds;
import com.ss.android.ugc.aweme.feed.model.Aweme;
import java.util.*;

public final class FeedAdsTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        Aweme first=new Aweme(false), second=new Aweme(false), ad=new Aweme(true);
        List<Object> empty=new ArrayList<>();
        check(FeedAds.filter(null)==null,"null input");
        check(FeedAds.filter(empty)==empty,"empty identity");
        List<Object> ordinary=Arrays.asList(first,null,"unknown",second);
        check(FeedAds.filter(ordinary)==ordinary,"ordinary list identity and content");
        List<Object> source=Collections.unmodifiableList(Arrays.asList(ad,first,ad,null,"unknown",second,ad));
        List result=FeedAds.filter(source);
        check(result.equals(ordinary),"remove ads at start/middle/end and retain all other entries");
        check(source.size()==7,"do not mutate unmodifiable input");
        check(FeedAds.filter(result)==result,"idempotence");
        check(FeedAds.filter(Arrays.asList(ad,ad)).isEmpty(),"all-ad response");
        check(FeedAds.filter(Arrays.asList(first,ad,second)).equals(Arrays.asList(first,second)),"order");
        System.out.println("PASS: 8 feed filtering cases");
    }
}
