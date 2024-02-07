#!/usr/bin/env python 
"""
Download ERS SLCs from ESA (https://esar-ds.eo.esa.int/oads/data/SAR_IMS_1P/)

USAGE: ./download_asar.py SAR_IMS_1PNESA20041016_061715_00000015A099_00163_49616_0000.E2 

Assumes env vars for loging present https://esar-ds.eo.esa.int
"""
import os 
import sys
import requests
from urllib.parse import urlparse, parse_qs, quote_plus
from time import sleep

# Better GitHub Actions
#from tqdm import tqdm
import logging
import datetime
from tqdm_loggable.auto import tqdm
from tqdm_loggable.tqdm_logging import tqdm_logging

logger = logging.getLogger(__name__)
tqdm_logging.set_log_rate(datetime.timedelta(seconds=30)) 

def login():
    print('Logging in...')
    username = os.environ['EOIAM_USERNAME']
    password = os.environ['EOIAM_PASSWORD']
    s = requests.Session()

    r = s.get('https://esar-ds.eo.esa.int/oads/access/login')

    sessionkey = parse_qs(urlparse(r.url).query)['sessionDataKey'][0]

    encodeduser = quote_plus(username)
    encodedpass = quote_plus(password)
    postdata=f'tocommonauth=true&usernameUserInput={encodeduser}&username={encodeduser}&password={encodedpass}&sessionDataKey={sessionkey}' 
    r = s.post('https://eoiam-idp.eo.esa.int/samlsso', 
                data=postdata, 
                headers={'Content-Type': 'application/x-www-form-urlencoded'})

    # Hack to get SAMLToken needed for final auth
    htmllines = r.text.splitlines()
    saml = [x for x in htmllines if x.startswith("<input type='hidden' name='SAMLResponse'")][0]
    encodedSAML = quote_plus(saml[48:-3])
    postdata = f'SAMLResponse={encodedSAML}'
    r = s.post('https://esar-ds.eo.esa.int/oads/Shibboleth.sso/SAML2/POST', 
            data=postdata,
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    return s


# Finally we can download a file!
def _dl_file(session, url, outdir, override=False, progressbar=False):
    """Download file from URL."""
    r = session.get(url, stream=True)
    filename = url.split('/')[-1]
    if os.path.isfile(os.path.join(outdir, filename)) and not override:
        raise FileExistsError('%s already exists. Skipping...' % filename)
    length = int(r.headers['Content-Length'])
    if progressbar:
        progress = tqdm(total=length, unit='B', unit_scale=True)
    outfile = os.path.join(outdir, filename)
    with open(outfile, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                if progressbar:
                    progress.update(1024*1024)
    if progressbar:
        progress.close()


def request_download(session, product_id, outdir='./', override=False,
                     progressbar=False):
    """Request download to ESA and interpret the response."""
    if 'SAR_IMS_1P' in product_id:
        product_url = f'https://esar-ds.eo.esa.int/oads/data/SAR_IMS_1P/{product_id}'
    # NOTE: need application to access raw data https://esatellus.service-now.com/csp?id=dsr&dataset=SAR_IM_0P
    elif 'SAR_IM__0P' in product_id:
        product_url = f'https://esar-ds.eo.esa.int/oads/data/SAR_IM__0P_Scenes/{product_id}'
    r = session.get(product_url, stream=True)

    # Product is not available
    if r.status_code == 404:
        raise requests.exceptions.InvalidURL()
    
    # Product is available, but ESA must process the order
    if r.status_code == 202:
        # Resend query to get correct "Retry-After" header value
        r = session.get(product_url, stream=True)
        retry_after = int(r.headers['Retry-After'])
        if progressbar:
            print('The order is being processed by ESA '
                'and will be ready in {} seconds.'.format(retry_after))
            progress = tqdm(total=retry_after)
        for i in range(retry_after):
            sleep(1)
            if progressbar:
                progress.update(1)
        if progressbar:
            progress.close()
        request_download(session, product_id, outdir, override=override,
                         progressbar=progressbar)
    
    # Product is directly available
    if r.status_code == 200:
        _dl_file(session, product_url, outdir, progressbar=progressbar)



if __name__ == '__main__':
    productid = sys.argv[1]
    session = login()
    request_download(session, productid)
