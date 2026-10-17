package mod.privacy;
/** Local notice state: opening Inbox or dismissing the offer never marks an APK downloaded. */
public final class UpdatePolicy {
    public static boolean available(long installed,long latest){return installed>0 && latest>installed;}
    public static boolean pending(long installed,long latest,long downloaded,boolean filePresent){
        return available(installed,latest) && (downloaded!=latest || !filePresent);
    }
    public static boolean prompt(long installed,long latest,long prompted,long downloaded,boolean filePresent){
        return pending(installed,latest,downloaded,filePresent) && prompted<latest;
    }
}
