"""Exercise release verification with local fixtures; never contact or mutate GitHub."""
import importlib.util,json,pathlib,tempfile,unittest
source=pathlib.Path(__file__).resolve().parents[1]/'scripts/publish_github_release.py'
spec=importlib.util.spec_from_file_location('publisher',source);publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)

class ReleaseLayout(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.old=publisher.root;publisher.root=self.root
        (self.root/'release').mkdir();self.files=self.root/'files';self.files.mkdir()
        for name in publisher.APK_NAMES:(self.files/name).write_bytes(b'arm64-fixture')
        self.release={'tag_name':'clean-fixture','assets':[{'name':n,'size':(self.files/n).stat().st_size,'digest':'sha256:'+publisher.sha(self.files/n)} for n in publisher.APK_NAMES]}
    def tearDown(self):publisher.root=self.old;self.temp.cleanup()
    def add32(self):
        for name in ('ttc-arm7.apk','ttc-arm32.apk'):
            (self.files/name).write_bytes(b'arm32-fixture');self.release['assets'].append({'name':name,'size':13,'digest':'sha256:'+publisher.sha(self.files/name)})
        record={'consumer_tag':'clean-fixture','size':13,'sha256':publisher.sha(self.files/'ttc-arm7.apk')}
        (self.root/'release/arm32-distribution.json').write_text(json.dumps(record))
    def test_primary_pair(self):publisher.verify_assets(self.release,publisher.APK_NAMES,self.files)
    def test_four_apks(self):
        self.add32();publisher.verify_assets(self.release,publisher.APK_NAMES,self.files)
        publisher.verify_assets(self.release,publisher.APK_NAMES+('ttc-arm7.apk','ttc-arm32.apk'),self.files)
    def test_arm64_under_arm7_name_rejected(self):
        self.add32();self.release['assets'][2]['digest']=self.release['assets'][0]['digest']
        with self.assertRaises(AssertionError):publisher.verify_assets(self.release,publisher.APK_NAMES,self.files)
    def test_technical_asset_in_consumer_rejected(self):
        self.release['assets'].append({'name':'update.json'})
        with self.assertRaises(AssertionError):publisher.verify_assets(self.release,publisher.APK_NAMES,self.files)
    def test_changed_published_bytes_rejected(self):
        self.release['assets'][0]['digest']='sha256:'+'0'*64
        with self.assertRaises(AssertionError):publisher.verify_assets(self.release,publisher.APK_NAMES,self.files)
    def test_unsafe_feed_filename_rejected_before_git(self):
        with self.assertRaises(AssertionError):publisher.advance_feed({},'../update.json')

if __name__=='__main__':unittest.main()
