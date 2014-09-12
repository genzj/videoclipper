import logging
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG

_logger = None
_children = []
def __init(projname):
    global _logger
    _logger = logging.getLogger(projname)
    if not _logger.handlers:
        _loggerHandler = logging.StreamHandler()
        _loggerHandler.setLevel(DEBUG)
        _loggerHandler.setFormatter(
            logging.Formatter('%(name)s - [%(levelname)s] %(message)s'))
        _logger.addHandler(_loggerHandler)
        _logger.setLevel(INFO)

def getChild(*args, **kwargs):
    l = _logger.getChild(*args, **kwargs)
    if l not in _children:
        _children.append(l)
    return l

def setDebugLevel(level):
    _logger.setLevel(level)
    list(map(lambda l:l.setLevel(level), _children))

# not use project name
__init(None)

if __name__ == '__main__':
    log = _logger.getChild('logtest')
    log.setLevel(logging.DEBUG)
    log.info('Info test')
    log.warn('Warn test')
    log.error('Error test')
    log.critical('Critical test')
    log.debug('debug test')
    try:
        def __ex_test():
            raise Exception('exception test')
        __ex_test()
    except Exception as ex:
        log.exception(ex)
