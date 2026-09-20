"""Synthetic local tests only. They do not contact Stripe or take payment."""
from __future__ import annotations
import hashlib, hmac, io, json, os, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temp=tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH']=str(Path(temp.name)/'test.sqlite3')
os.environ['APP_MODE']='preview'
import server

class BackendTests(unittest.TestCase):
    def setUp(self):
        server.MODE='live';server.ORIGIN='https://pilot.example';server.CONTACT='host@example.com'
        server.PAYMENT_LINK='https://buy.stripe.com/test_example';server.PAYMENT_LINK_ID='plink_example'
        server.WEBHOOK_SECRET='whsec_synthetic_test_only';server.LIVE_PAYMENTS=False;server.CLOSES=time.time()+86400
        with server.connect() as con:
            for t in ['payments','stripe_events','applications','rate_limits']:con.execute('DELETE FROM '+t)
    def req(self,path,data,headers=None):
        body=json.dumps(data).encode() if not isinstance(data,bytes) else data
        environ={'REQUEST_METHOD':'POST','PATH_INFO':path,'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body),'HTTP_ORIGIN':server.ORIGIN,'REMOTE_ADDR':'127.0.0.1'}
        environ.update(headers or {})
        meta=[]
        result=b''.join(server.application(environ,lambda s,h:meta.append((s,h))))
        return int(meta[0][0].split()[0]),json.loads(result)
    def payload(self):
        p={key:'An example of real hands-on AI work in an independent business.' for key in server.TEXT_RULES}
        p.update(name='Test Founder',email='test@example.com',location='Berlin',profile='https://example.com',stage='building',notes='',submissionKey='a'*32,websiteConfirm='')
        p.update({key:'on' for key in server.CONSENTS})
        return p
    def save(self):
        status,result=self.req('/api/applications',self.payload());self.assertEqual(status,200);return result['applicationId']
    def event(self,app_id,event_id='evt_one',session='cs_test_one',paid=True):
        return {'id':event_id,'type':'checkout.session.completed','livemode':False,'created':int(time.time()),'data':{'object':{'id':session,'client_reference_id':app_id,'payment_link':server.PAYMENT_LINK_ID,'amount_subtotal':5900,'amount_total':7021,'total_details':{'amount_tax':1121},'currency':'eur','payment_status':'paid' if paid else 'unpaid','payment_intent':'pi_example'}}}
    def post_event(self,event,secret=None,timestamp=None):
        raw=json.dumps(event).encode();stamp=str(timestamp or int(time.time()))
        sig=hmac.new((secret or server.WEBHOOK_SECRET).encode(),stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        return self.req('/api/stripe-webhook',raw,{'HTTP_STRIPE_SIGNATURE':f't={stamp},v1={sig}'})
    def test_application_saved_before_checkout(self):
        status,result=self.req('/api/applications',self.payload())
        self.assertEqual(status,200);self.assertIn('client_reference_id='+result['applicationId'],result['checkoutUrl'])
        with server.connect() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM applications').fetchone()[0],1)
    def test_idempotent_retry(self):
        _,first=self.req('/api/applications',self.payload());_,second=self.req('/api/applications',self.payload());self.assertEqual(first,second)
    def test_missing_acknowledgement_rejected(self):
        payload=self.payload();payload.pop('privacy');self.assertEqual(self.req('/api/applications',payload)[0],422)
    def test_cross_origin_rejected(self):
        self.assertEqual(self.req('/api/applications',self.payload(),{'HTTP_ORIGIN':'https://unrelated.example'})[0],403)
    def test_closed_and_preview_blocked(self):
        server.CLOSES=time.time()-1;self.assertEqual(self.req('/api/applications',self.payload())[0],410)
        server.MODE='preview';self.assertEqual(self.req('/api/applications',self.payload())[0],503)
    def test_signed_payment_and_duplicate_delivery(self):
        ref=self.save();event=self.event(ref);self.assertEqual(self.post_event(event)[0],200)
        status,result=self.post_event(event);self.assertTrue(result['duplicate'])
        with server.connect() as con:
            self.assertEqual(con.execute('SELECT payment_status FROM payments').fetchone()[0],'paid')
            self.assertEqual(con.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
    def test_bad_and_old_signature_rejected(self):
        event=self.event(self.save())
        self.assertEqual(self.post_event(event,secret='not_the_secret')[0],400)
        self.assertEqual(self.post_event(event,timestamp=int(time.time())-600)[0],400)
    def test_wrong_amount_not_marked_paid(self):
        event=self.event(self.save());event['data']['object']['amount_total']=1;self.post_event(event)
        with server.connect() as con:self.assertEqual(con.execute('SELECT payment_status FROM payments').fetchone()[0],'needs_review')
    def test_net_without_vat_not_marked_paid(self):
        event=self.event(self.save());event['data']['object']['amount_total']=5900;event['data']['object']['total_details']={'amount_tax':0}
        self.post_event(event)
        with server.connect() as con:self.assertEqual(con.execute('SELECT payment_status FROM payments').fetchone()[0],'needs_review')
    def test_delayed_unpaid_event_does_not_unpay(self):
        ref=self.save();self.post_event(self.event(ref));self.post_event(self.event(ref,event_id='evt_two',paid=False))
        with server.connect() as con:self.assertEqual(con.execute('SELECT payment_status FROM payments').fetchone()[0],'paid')
    def test_unrelated_link_ignored(self):
        event=self.event(self.save());event['data']['object']['payment_link']='plink_other';self.post_event(event)
        with server.connect() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM payments').fetchone()[0],0)
    def test_private_files_not_served(self):
        for path in ['/.env','/private-data/applications.sqlite3','/server.py']:
            meta=[];payload=b''.join(server.application({'REQUEST_METHOD':'GET','PATH_INFO':path},lambda s,h:meta.append(s)))
            self.assertTrue(meta[0].startswith('404'))
    def test_legal_and_assets(self):
        meta=[]
        body=b''.join(server.application({'REQUEST_METHOD':'GET','PATH_INFO':'/legal/impressum'},lambda s,h:meta.append(s)))
        self.assertTrue(meta[0].startswith('200'))
        self.assertIn(b'Impressum', body)
        self.assertIn(b'DE343190995', body)
        self.assertNotIn(b'DRAFT', body)
        meta=[]
        server.application({'REQUEST_METHOD':'GET','PATH_INFO':'/legal/imprint'},lambda s,h:meta.append((s,h)))
        self.assertTrue(meta[0][0].startswith('302'))
        meta=[]
        css=b''.join(server.application({'REQUEST_METHOD':'GET','PATH_INFO':'/assets/site.css'},lambda s,h:meta.append(s)))
        self.assertTrue(meta[0].startswith('200'))
        self.assertIn(b'--display', css)
        meta=[]
        font=b''.join(server.application({'REQUEST_METHOD':'GET','PATH_INFO':'/assets/fonts/figtree-normal-latin.woff2'},lambda s,h:meta.append(s)))
        self.assertTrue(meta[0].startswith('200'))
        self.assertGreater(len(font), 1000)
        meta=[]
        chooser=b''.join(server.application({'REQUEST_METHOD':'GET','PATH_INFO':'/options/'},lambda s,h:meta.append(s)))
        self.assertTrue(meta[0].startswith('200'))
        self.assertIn(b'Workshop direction', chooser)

if __name__=='__main__':unittest.main(verbosity=2)
