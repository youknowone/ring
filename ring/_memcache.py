import hashlib
import re

str_key_refactor_rule = re.compile(r'[!-~]+')
bytes_key_refactor_rule = re.compile(b'[!-~]+')


def key_refactor(key):
    is_str = isinstance(key, str)
    if is_str:
        rule = str_key_refactor_rule
    else:
        rule = bytes_key_refactor_rule
    if len(key) < 250 and rule.match(key).group(0) == key:
        return key
    try:
        hashed = hashlib.sha1(key).hexdigest()
    except TypeError:
        # FIXME: ensure key is bytes before key_refactor
        key = key.encode('utf-8')
        hashed = hashlib.sha1(key).hexdigest()
    hashed_key = 'ring-sha1:' + hashed
    if not is_str:
        hashed_key = hashed_key.encode()
    return hashed_key
