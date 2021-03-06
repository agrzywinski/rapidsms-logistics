from django.utils.importlib import import_module
from django.conf import settings
from rapidsms.conf import settings
from re import findall
from string import maketrans
from rapidsms.messages.outgoing import OutgoingMessage
from rapidsms.models import Connection, Backend

if hasattr(settings,'LOGISTICS_CONFIG'):
    config = import_module(settings.LOGISTICS_CONFIG)
else:
    import config
    
if hasattr(settings, "CODE_CHARS_RANGE"):
    CODE_CHARS_RANGE = settings.CODE_CHARS_RANGE
else:
    CODE_CHARS_RANGE = (2,4) # from 2 to 4 characters per product code

if hasattr(settings, "NUMERIC_LETTERS"):
    NUMERIC_LETTERS = settings.NUMERIC_LETTERS
else:
    NUMERIC_LETTERS = ("lLO", "110")


def ussd_push_backend():
    if not hasattr(ussd_push_backend, '_backend'):
        backend_name = getattr(settings, 'USSD_PUSH_BACKEND', None)
        if backend_name:
            ussd_push_backend._backend = Backend.objects.get(name=backend_name)
        else:
            ussd_push_backend._backend = None

    return ussd_push_backend._backend


def get_ussd_connection(fallback_connection):
    backend = ussd_push_backend()
    if not backend:
        return fallback_connection

    return Connection(
        backend=backend,
        identity=fallback_connection.identity,
        contact=fallback_connection.contact
    )


def ussd_msg_response(msg, template, **kwargs):
    response = OutgoingMessage(
        get_ussd_connection(msg.connection),
        template,
        **kwargs
    )
    msg.responses.append(response)
    return msg


def parse_report(val):
    """
    Takes a product report string, such as "zi 10 co 20 la 30", and parses it into a list of tuples
    of (code, quantity):

    >>> parse_report("zi 10 co 20 la 30")
    [('zi', 10), ('co', 20), ('la', 30)]

    Properly handles arbitrary whitespace:

    >>> parse_report("zi10 co20 la30")
    [('zi', 10), ('co', 20), ('la', 30)]

    Properly deals with Os being used for 0s:

    >>> parse_report("zi1O co2O la3O")
    [('zi', 10), ('co', 20), ('la', 30)]

    Properly handles extra spam in the string:

    >>> parse_report("randomextradata zi1O co2O la3O randomextradata")
    [('zi', 10), ('co', 20), ('la', 30)]
    """
    
    def _cleanup(s):
        return unicode(s).encode('utf-8')
    
    return [(x[0], int(x[1].translate(maketrans(NUMERIC_LETTERS[0], NUMERIC_LETTERS[1])))) \
            for x in findall("\s*(?P<code>[A-Za-z]{%(minchars)d,%(maxchars)d})\s*(?P<quantity>[\-?0-9%(numeric_letters)s]+)\s*" % \
                                    {"minchars": CODE_CHARS_RANGE[0],
                                     "maxchars": CODE_CHARS_RANGE[1],
                                     "numeric_letters": NUMERIC_LETTERS[0]}, _cleanup(val))]

if __name__ == '__main__':
    import doctest
    doctest.testmod()