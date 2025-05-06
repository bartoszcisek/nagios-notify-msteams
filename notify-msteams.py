#!/usr/bin/env python3
#
# Michael Cone
#

import argparse
import configparser
import json
import os
import requests
from datetime import datetime
from jinja2 import Environment, PackageLoader, select_autoescape

NAGIOS_URL = "http://nagios.my.lan/cgi-bin/nagios3"

now = datetime.now()
current_time = now.strftime("%H:%M:%S")

env = Environment(
    loader=PackageLoader("notify-msteams"),
    autoescape=select_autoescape()
)

nag_template = {
    'HOST' : 'host.json.jinja',
    'SERVICE' : 'service.json.jinja',
    # 'HOST' : 'host_simple.json.jinja',
    # 'SERVICE' : 'service_simple.json.jinja',
}

def _get_nagios_macros():
    """Read all ENV vars then save and rename the Nagios Macros in a dictionary."""
    MACROS=dict()
    for k, v in sorted(os.environ.items()):
        if k.startswith('NAGIOS_'):
            k = k.replace('NAGIOS_', '')
            MACROS[k] = v
    return MACROS

def send_to_teams(url, message_json, debug):
    """ posts the json message to the ms teams webhook url """
    headers = {'Content-Type': 'application/json'}
    r = requests.post(url, data=message_json, headers=headers)
    if r.status_code == requests.codes.ok:
        if debug:
            print('success')
        return True
    else:
        if debug:
            print('failure: {}'.format(r.reason))
        return False

def get_webhook_url(macros):
    """ get webhook url from file or from macro directly"""
    url = macros.get('_CONTACTWEBHOOKURL')
    if url is not None:
        return url
    path = macros.get('_CONTACTWEBHOOKFILE')
    if path is None:
        print('ERROR: no ms-teams webhook url or file was found')
        exit(2)
    if not os.path.exists(path):
        print('ERROR: webhook url file does not exist')
        exit(2)
    with open(path, 'r') as f:
        url = f.read().strip()
    if url is None:
        print("ERROR: no ms-teams webhook url was found in {}".format(path))
        exit(2)
    else:
        return url
def read_config(config_file):
    """ read the config file and return a dictionary """
    if config_file is None:
        return None
    if not os.path.exists(config_file):
        print('ERROR: config file does not exist')
        exit(2)
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except configparser.Error as e:
        print('ERROR: failed to parse config file: {}'.format(e))
        exit(2)
    return config

def main():
    """receive nagios environment data and send notifications via MS-Teams"""

    parser = argparse.ArgumentParser()
    parser.add_argument('msgtype', action='store', help='message subject')
    parser.add_argument('--debug', action='store_true', help='print json message, etc. for debugging')
    parser.add_argument('-c', '--config', action='store', help='config file')
    parsedArgs = parser.parse_args()

    message_type = parsedArgs.msgtype
    debug = parsedArgs.debug

    config_file = parsedArgs.config
    config = read_config(config_file)

    macros = _get_nagios_macros()
    # Inject Nagios location for template base url.
    if config['default']['nagios_url'] is not None:
        macros.update({'nagios_url': config['default']['nagios_url']})
    else:
        macros.update({'nagios_url': NAGIOS_URL})

    url = get_webhook_url(macros)
    # verify url defined
    if url is None:
        # error no url
        print('ERROR: no ms-teams webhook url was found')
        exit(2)

    # get the Jinja template for "HOST" or "SERVICE"
    t = env.get_template(nag_template.get(message_type))
    message_json = t.render(**macros)
    if debug:
        print(message_json + '\n\n--> ' + current_time )
    send_to_teams(url, message_json, debug)


if __name__=='__main__':
    main()
