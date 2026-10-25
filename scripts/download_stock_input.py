#!/usr/bin/env python3
"""Download the user-selected public SM-P900 archive; exact size/hash required."""
import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import urllib.parse
import urllib.request

EXPECTED_SIZE=1403027011
EXPECTED_SHA256='c5f281c6bec43ef6396adac3300b109e0e4d6f454a55fb4971cb068b010ad0c9'

class Form(HTMLParser):
    def __init__(self):super().__init__();self.action=None;self.fields={};self.inside=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='form' and attrs.get('id')=='download-form':
            self.action=attrs.get('action');self.inside=True
        if self.inside and tag=='input' and attrs.get('name'):
            self.fields[attrs['name']]=attrs.get('value','')
    def handle_endtag(self,tag):
        if tag=='form':self.inside=False

def confirmation_url(html,file_id):
    form=Form();form.feed(html)
    parsed=urllib.parse.urlparse(form.action or '')
    if (parsed.scheme,parsed.netloc,parsed.path)!=('https','drive.usercontent.google.com','/download'):
        raise ValueError('Expected public Drive confirmation form; no login or CAPTCHA handling')
    if form.fields.get('id')!=file_id:raise ValueError('Unexpected Drive file identity')
    return form.action+'?'+urllib.parse.urlencode(form.fields)

def download(file_id,target):
    if target.exists():raise ValueError('Output already exists')
    url='https://drive.google.com/uc?'+urllib.parse.urlencode({'id':file_id,'export':'download'})
    response=urllib.request.urlopen(url,timeout=60)
    if 'text/html' in response.headers.get('Content-Type',''):
        with response:html=response.read(1024*1024+1)
        if len(html)>1024*1024:raise ValueError('Oversized confirmation page')
        response=urllib.request.urlopen(confirmation_url(html.decode('utf-8'),file_id),timeout=60)
    temporary=target.with_name(target.name+'.part')
    if temporary.exists():
        response.close()
        raise ValueError('Partial download already exists; refusing to overwrite')
    h=hashlib.sha256();size=0
    try:
        with response,temporary.open('xb') as f:
            while True:
                data=response.read(1024*1024)
                if not data:break
                size+=len(data)
                if size>EXPECTED_SIZE:raise ValueError('Unexpected archive size')
                h.update(data);f.write(data)
        if size!=EXPECTED_SIZE or h.hexdigest()!=EXPECTED_SHA256:
            raise ValueError('Stock archive verification failed')
        temporary.rename(target)
    except BaseException:
        if temporary.exists():temporary.unlink()
        raise
    print('Verified exact SM-P900 stock archive:',size,'bytes')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file_id');p.add_argument('output',type=Path)
    a=p.parse_args();download(a.file_id,a.output)
