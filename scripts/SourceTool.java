import jadx.api.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class SourceTool {
    public static void main(String[] a) throws Exception {
        Set<String> names=new HashSet<>(Arrays.asList(Arrays.copyOfRange(a,2,a.length)));
        JadxArgs args=new JadxArgs(); args.setInputFile(new File(a[0]));args.setSkipResources(true);
        args.setThreadsCount(2);args.setShowInconsistentCode(true);
        try(JadxDecompiler d=new JadxDecompiler(args)) {
            d.load();Files.createDirectories(Path.of(a[1]));
            for(JavaClass c:d.getClasses()) if(names.contains(c.getRawName())||names.contains(c.getFullName())||(names.contains("*.pk")&&c.getRawName().endsWith(".pk"))) {
                Files.writeString(Path.of(a[1],c.getRawName().replace('.','_')+".java"),c.getCode());
                System.out.println(c.getRawName());
            }
        }
    }
}
