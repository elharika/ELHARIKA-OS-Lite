#!/usr/bin/env python3
"""Build dependency-free apps directly using SDK 30, build-tools 30.0.3, JDK17.
Debug signing only. Never use this key for a firmware release.
"""
import os,subprocess,shutil,zipfile,argparse,xml.etree.ElementTree as ET
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--android-jar',required=True,type=Path);p.add_argument('--build-tools',required=True,type=Path);p.add_argument('--keystore',required=True,type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1];bt=a.build_tools.resolve();jar=a.android_jar.resolve();key=a.keystore.resolve()
def run(args):subprocess.run([str(v) for v in args],check=True)
if not key.exists():
 key.parent.mkdir(parents=True,exist_ok=True)
 run(['keytool','-genkeypair','-keystore',key,'-storepass','android','-keypass','android','-alias','androiddebugkey','-dname','CN=ELHARIKA Development','-keyalg','RSA','-validity','3650'])
for name in ['pen','launcher']:
 src=root/'apps'/name/'src/main';out=root/'out'/name
 if out.exists():shutil.rmtree(out)
 out.mkdir(parents=True);(out/'gen').mkdir();(out/'classes').mkdir();(out/'dex').mkdir()
 ET.register_namespace('android','http://schemas.android.com/apk/res/android')
 tree=ET.parse(src/'AndroidManifest.xml');tree.getroot().set('package','org.elharika.'+name)
 ET.SubElement(tree.getroot(),'uses-sdk',{'{http://schemas.android.com/apk/res/android}minSdkVersion':'29','{http://schemas.android.com/apk/res/android}targetSdkVersion':'30'})
 tree.write(out/'AndroidManifest.xml',encoding='utf-8',xml_declaration=True)
 run([bt/'aapt2','compile','--dir',src/'res','-o',out/'res.zip'])
 run([bt/'aapt2','link','-o',out/'base.apk','-I',jar,'--manifest',out/'AndroidManifest.xml','--java',out/'gen',out/'res.zip'])
 java=list((src/'java').rglob('*.java'))+list((out/'gen').rglob('*.java'))
 run(['javac','-source','8','-target','8','-Xlint:-options','-bootclasspath',str(bt/'core-lambda-stubs.jar')+os.pathsep+str(jar),'-d',out/'classes',*java])
 run(['jar','cf',out/'classes.jar','-C',out/'classes','.'])
 run([bt/'d8','--lib',jar,'--min-api','29','--output',out/'dex',out/'classes.jar'])
 with zipfile.ZipFile(out/'base.apk','a',zipfile.ZIP_DEFLATED) as z:
  for f in (out/'dex').glob('*.dex'):z.write(f,f.name)
 run([bt/'zipalign','-f','4',out/'base.apk',out/'aligned.apk'])
 run([bt/'apksigner','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',out/(name+'-debug.apk'),out/'aligned.apk'])
 run([bt/'apksigner','verify','--verbose',out/(name+'-debug.apk')])
 print('DEBUG APK built:',out/(name+'-debug.apk'),flush=True)
