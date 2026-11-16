"""Exercise the HTTP boundary without opening a network port."""
import io,json,tempfile,unittest
from http.client import HTTPResponse
from pathlib import Path
from unittest.mock import patch
import app

class Wire:
    def __init__(self,raw): self.input=io.BytesIO(raw);self.output=io.BytesIO()
    def makefile(self,*args):return self.input
    def sendall(self,b):self.output.write(b)

class HTTPFlow(unittest.TestCase):
    def test_company_flow(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(app,'DATA',Path(tmp)),patch.dict('os.environ',{},clear=True),patch.object(app.Handler,'log_message'):
            app.init()
            cookie=''
            def send(path,data=None,origin=app.ORIGIN):
                body=json.dumps(data).encode() if data is not None else b''
                method='POST' if data is not None else 'GET'
                w=Wire(f'{method} {path} HTTP/1.0\r\nHost: localhost\r\nOrigin: {origin}\r\nCookie: {cookie}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n'.encode()+body)
                app.Handler(w,('local',1),None)
                r=HTTPResponse(Wire(w.output.getvalue()));r.begin();return r
            for asset in ['/','/ui.js','/style.css']:self.assertEqual(send(asset).status,200)
            self.assertEqual(send('/api/signup',{},'https://other.test').status,403)
            self.assertEqual(send('/api/run',{}).status,401)
            r=send('/api/signup',dict(company='Pilot',email='owner@example.test',password='long password here'));self.assertEqual(r.status,200)
            cookie=r.getheader('Set-Cookie').split(';')[0]
            self.assertEqual(send('/api/run',dict(goal='10 demos',offer='Scheduling',audience='Salons',budget=50)).status,200)
            run=json.load(send('/api/state'))['runs'][0]
            self.assertEqual(send('/api/approve',dict(id=run['id'],draft='Approved text')).status,200)
            self.assertEqual(json.load(send('/api/state'))['runs'][0]['status'],'approved')
            self.assertEqual(send('/api/logout',{}).status,200)
            self.assertFalse(json.load(send('/api/state'))['signedIn'])
