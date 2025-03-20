import six

if six.PY2:
    from ccaa import ccaa
    from articles import *
else:
    from .ccaa import ccaa
    from .articles import *
