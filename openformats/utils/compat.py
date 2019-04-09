import six


def ensure_unicode(pattern):
    if isinstance(pattern, six.binary_type):
        pattern = pattern.decode('utf-8')
    return pattern
