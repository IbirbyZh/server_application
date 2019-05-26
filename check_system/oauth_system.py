import os
import time

import requests


def get_oauth_key(server_ip):
    if os.path.exists('/secrets/oauth.txt'):
        with open('/secrets/oauth.txt') as i:
            return i.read().strip().split()

    data = {
        'name': 'CheckSystem',
        'redirect_uri': 'http://{}:5000/login_finish'.format(server_ip),
        'scopes': '',
    }

    headers = {
        'PRIVATE-TOKEN': os.environ['GITLAB_API_TOKEN'],
    }
    while True:
        try:
            response = requests.post('http://gitlab/api/v4/applications', headers=headers, data=data)
            oauth_key = response.json()['secret']
            application_id = response.json()['application_id']
        except:
            time.sleep(15)
            print('retry register application')
            continue
        break

    with open('/secrets/oauth.txt', 'w') as o:
        o.write(oauth_key)
        o.write('\t')
        o.write(application_id)
    return oauth_key
