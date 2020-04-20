# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import netifaces
from pathlib import Path
import datetime
from OpenSSL import crypto
import urllib3
import io
import json
import logging
import os
import subprocess
import zipfile
from threading import Thread
import time

from odoo import _
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Helper
#----------------------------------------------------------

class IoTRestart(Thread):
    """
    Thread to restart odoo server in IoT Box when we must return a answer before
    """
    def __init__(self, delay):
        Thread.__init__(self)
        self.delay = delay

    def run(self):
        time.sleep(self.delay)
        subprocess.check_call(["sudo", "service", "odoo", "restart"])

def add_server_config(credential):
    """
    Add credential to IoT config file
    """
    iot_box_config = {'iot_box_config': {
        'url_odoo_server': credential[0],
        'token_odoo_server': credential[1],
        }
    }
    if len(credential) > 2:
        # IoT Box send token with db_uuid and enterprise_code only since V13
        add_cert_config({'db_uuid': credential[2], 'enterprise_code': credential[3]})
    write_iot_config(iot_box_config)

def add_cert_config(credential):
    """
    Add certificate credential to IoT config file
    """
    iot_box_config = {'iot_box_config': {
        'db_uuid': credential.get('db_uuid', None),
        'enterprise_code': credential.get('enterprise_code', None)
        }
    }
    write_iot_config(iot_box_config)

def add_wifi_config(credential):
    """
    Add wifi credential to IoT config file
    """
    iot_box_config = {'iot_box_network': {
        'ssid': credential.get('ssid', None),
        'password': credential.get('password', None)
        }
    }
    write_iot_config(iot_box_config)

def access_point():
    return get_ip() == '10.11.12.1'

def check_certificate():
    """
    Check if the current certificate is up to date or not authenticated
    """
    server = get_odoo_server_url()
    if server:
        path = Path('/etc/ssl/certs/nginx-cert.crt')
        if path.exists():
            with path.open('r') as f:
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
                cert_end_date = datetime.datetime.strptime(cert.get_notAfter().decode('utf-8'), "%Y%m%d%H%M%SZ") - datetime.timedelta(days=10)
                iot_box_network = {'iot_box_network': {
                    'cert_end_date': cert_end_date.strftime("%Y/%m/%d")
                    }
                }
                write_iot_config(iot_box_network)
                for key in cert.get_subject().get_components():
                    if key[0] == b'CN':
                        cn = key[1].decode('utf-8')
                if cn == 'OdooTempIoTBoxCertificate' or datetime.datetime.now() > cert_end_date:
                    _logger.info(_('Your certificate %s must be updated') % (cn))
                    load_certificate()
                else:
                    _logger.info(_('Your certificate %s is valid until %s') % (cn, cert_end_date))
        else:
            load_certificate()

def check_git_branch():
    """
    Check if the local branch is the same than the connected Odoo DB and
    checkout to match it if needed.
    """
    server = get_odoo_server_url()
    if server:
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        try:
            response = http.request(
                'POST',
                server + "/web/webclient/version_info",
                body = '{}',
                headers = {'Content-type': 'application/json'}
            )

            if response.status == 200:
                git = ['git', '--work-tree=/home/pi/odoo/', '--git-dir=/home/pi/odoo/.git']

                db_branch = json.loads(response.data)['result']['server_serie'].replace('~', '-')
                iot_box_config = {'iot_box_config': {
                    'db_branch': db_branch
                    }
                }
                write_iot_config(iot_box_config)
                if not subprocess.check_output(git + ['ls-remote', 'origin', db_branch]):
                    db_branch = 'master'

                local_branch = subprocess.check_output(git + ['symbolic-ref', '-q', '--short', 'HEAD']).decode('utf-8').rstrip()

                if db_branch != local_branch:
                    delete_iot_handlers()
                    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
                    subprocess.check_call(git + ['branch', '-m', db_branch])
                    subprocess.check_call(git + ['remote', 'set-branches', 'origin', db_branch])
                    os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/posbox_update.sh')
                    subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])
                    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/etc/cups"])

        except Exception as e:
            _logger.error('Could not reach configured server')
            _logger.error('A error encountered : %s ' % e)

def check_image():
    """
    Check if the current image of IoT Box is up to date
    """
    url = 'http://nightly.odoo.com/master/posbox/iotbox/SHA1SUMS.txt'
    urllib3.disable_warnings()
    http = urllib3.PoolManager(cert_reqs='CERT_NONE')
    response = http.request('GET', url)
    checkFile = {}
    valueActual = ''
    for line in response.data.decode().split('\n'):
        if line:
            value, name = line.split('  ')
            checkFile.update({value: name})
            if name == 'iotbox-latest.zip':
                valueLastest = value
            elif name == get_img_name():
                valueActual = value
    if valueActual == valueLastest:
        return False
    version = checkFile.get(valueLastest, 'Error').replace('iotboxv', '').replace('.zip', '').split('_')
    return {'major': version[0], 'minor': version[1]}

def get_img_name():
    major, minor = get_version().split('.')
    return 'iotboxv%s_%s.zip' % (major, minor)

def get_ip():
    try:
        return netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
    except:
        return netifaces.ifaddresses('wlan0')[netifaces.AF_INET][0]['addr']

def get_mac_address():
    try:
        return netifaces.ifaddresses('eth0')[netifaces.AF_LINK][0]['addr']
    except:
        return netifaces.ifaddresses('wlan0')[netifaces.AF_LINK][0]['addr']

def get_ssid():
    ap = subprocess.call(['systemctl', 'is-active', 'hostapd']) # if service is active return 0 else inactive
    if not ap:
        return subprocess.check_output(['grep', '-oP', '(?<=ssid=).*', '/etc/hostapd/hostapd.conf']).decode('utf-8').rstrip()
    process_iwconfig = subprocess.Popen(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process_grep = subprocess.Popen(['grep', 'ESSID:"'], stdin=process_iwconfig.stdout, stdout=subprocess.PIPE)
    return subprocess.check_output(['sed', 's/.*"\\(.*\\)"/\\1/'], stdin=process_grep.stdout).decode('utf-8').rstrip()

def get_odoo_server_url():
    ap = subprocess.call(['systemctl', 'is-active', 'hostapd']) # if service is active return 0 else inactive
    if not ap:
        return False
    return read_iot_config('iot_box_config').get('url_odoo_server', False)

def get_token():
    return read_iot_config('iot_box_config').get('token_odoo_server', False)

def get_version():
    return subprocess.check_output(['cat', '/var/odoo/iotbox_version']).decode().rstrip()

def get_wifi_essid():
    wifi_options = []
    process_iwlist = subprocess.Popen(['sudo', 'iwlist', 'wlan0', 'scan'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process_grep = subprocess.Popen(['grep', 'ESSID:"'], stdin=process_iwlist.stdout, stdout=subprocess.PIPE).stdout.readlines()
    for ssid in process_grep:
        essid = ssid.decode('utf-8').split('"')[1]
        if essid not in wifi_options:
            wifi_options.append(essid)
    return wifi_options

def load_certificate():
    """
    Send a request to Odoo with customer db_uuid and enterprise_code to get a true certificate
    """
    db_uuid = read_iot_config('iot_box_config').get('db_uuid', False)
    enterprise_code = read_iot_config('iot_box_config').get('enterprise_code', False)
    if db_uuid and enterprise_code:
        url = 'https://www.odoo.com/odoo-enterprise/iot/x509'
        data = {
            'params': {
                'db_uuid': db_uuid,
                'enterprise_code': enterprise_code
            }
        }
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        response = http.request(
            'POST',
            url,
            body = json.dumps(data).encode('utf8'),
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        )
        result = json.loads(response.data.decode('utf8'))['result']
        if result:
            iot_box_config = {'iot_box_network': {
                'odoo-subject': result['subject_cn']
                }
            }
            write_iot_config(iot_box_config)
            subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
            subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/"])
            Path('/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'])
            Path('/root_bypass_ramdisks/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'])
            Path('/etc/ssl/private/nginx-cert.key').write_text(result['private_key_pem'])
            Path('/root_bypass_ramdisks/etc/ssl/private/nginx-cert.key').write_text(result['private_key_pem'])
            subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])
            subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/root_bypass_ramdisks/"])
            subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/etc/cups"])
            subprocess.check_call(["sudo", "service", "nginx", "restart"])


def delete_iot_handlers():
    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
    subprocess.check_call(["rm", "-rf", Path.home() / "odoo/addons/hw_drivers/iot_handlers/drivers/*"])
    subprocess.check_call(["rm", "-rf", Path.home() / "odoo/addons/hw_drivers/iot_handlers/interfaces/*"])
    subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])
    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/etc/cups"])

def download_iot_handlers(auto=True):
    """
    Get the drivers from the configured Odoo server
    """
    server = get_odoo_server_url()
    if server:
        urllib3.disable_warnings()
        pm = urllib3.PoolManager(cert_reqs='CERT_NONE')
        server = server + '/iot/get_handlers'
        try:
            resp = pm.request('POST', server, fields={'mac': get_mac_address(), 'auto': auto})
            if resp.data:
                subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
                drivers_path = Path.home() / 'odoo/addons/hw_drivers/iot_handlers'
                zip_file = zipfile.ZipFile(io.BytesIO(resp.data))
                zip_file.extractall(drivers_path)
                subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])
                subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/etc/cups"])
        except Exception as e:
            _logger.error('Could not reach configured server')
            _logger.error('A error encountered : %s ' % e)

def odoo_restart(delay):
    IR = IoTRestart(delay)
    IR.start()

def delete_iot_config(parent, key):
    iot_box_config = read_iot_config()
    iot_box_config.get(parent, {}).pop(key, None)
    write_iot_config(iot_box_config, False)

def read_iot_config(key=False):
    path = Path.home() / 'iot_config'
    if path.exists():
        with path.open('r') as iot_config_file:
            iot_config_text = iot_config_file.read()
            if iot_config_text:
                iot_config = json.loads(iot_config_text)
                return iot_config.get(key, iot_config)
    return {}

def write_iot_config(new_config, update=True):
    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
    path = Path.home() / 'iot_config'
    iot_config = read_iot_config()
    if iot_config and update:
        for new_config_key in new_config.keys():
            ic = iot_config.get(new_config_key, False)
            if ic:
                ic.update(new_config.get(new_config_key))
            else:
                iot_config.update(new_config)
    else:
        iot_config = new_config
    with path.open('w') as iot_config_file:
        json.dump(iot_config, iot_config_file)
    subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])
    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/etc/cups"])
