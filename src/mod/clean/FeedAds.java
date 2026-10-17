package mod.clean;

import com.ss.android.ugc.aweme.feed.model.Aweme;
import java.util.ArrayList;
import java.util.List;

/** Filters only posts which TikTok itself identifies as advertising. */
public final class FeedAds {
    private FeedAds() {}

    public static List filter(List items) {
        if (items == null || items.isEmpty()) return items;
        ArrayList<Object> clean = null;
        for (int index = 0; index < items.size(); index++) {
            Object item = items.get(index);
            boolean ad = item instanceof Aweme && ((Aweme) item).isAd();
            if (ad) {
                if (clean == null) {
                    clean = new ArrayList<Object>(items.size());
                    for (int prior = 0; prior < index; prior++) clean.add(items.get(prior));
                }
            } else if (clean != null) {
                clean.add(item);
            }
        }
        return clean == null ? items : clean;
    }
}
