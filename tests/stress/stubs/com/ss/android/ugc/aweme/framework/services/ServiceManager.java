package com.ss.android.ugc.aweme.framework.services;
import com.ss.android.ugc.aweme.IAccountService;
public final class ServiceManager {
    private static final ServiceManager INSTANCE=new ServiceManager();
    public static volatile String uid="account-A";
    public static final class User { public String getCurUserId(){return uid;} }
    public static final class Account implements IAccountService { public Object LJIIJJI(){return new User();} }
    public static ServiceManager get(){return INSTANCE;}
    public Object getService(Class<?> type){return new Account();}
}
