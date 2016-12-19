import requests

OH_BASE_URL = 'https://www.openhumans.org/'


def oh_get_member_data(token):
    """
    Exchange OAuth2 token for member data.
    """
    req = requests.get(
        '{}api/direct-sharing/project/exchange-member/'.format(OH_BASE_URL),
        params={'access_token': token})
    if req.status_code == 200:
        return req.json()
    raise Exception('Status code {}'.format(req.status_code))
    return None
