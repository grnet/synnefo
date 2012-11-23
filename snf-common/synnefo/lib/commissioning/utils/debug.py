#!/usr/bin/env python

import logging
from os import environ

_logger = None

def init_logger_file(name, level='DEBUG'):
    logger = logging.getLogger(name)
    handler = logging.FileHandler(name + '.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level = getattr(logging, level, logging.DEBUG)
    logger.setLevel(level)
    global _logger
    _logger = logger
    return logger

def init_logger_stderr(name, level='DEBUG'):
    logger = logging.getLogger(name)
    from sys import stderr
    handler = logging.StreamHandler(stderr)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level = getattr(logging, level, logging.DEBUG)
    logger.setLevel(level)
    global _logger
    _logger = logger
    return logger

def debug(fmt, *args):
    global _logger
    if _logger is None:
        init_logger_stderr('logger', get_level())
    _logger.debug(fmt % args)

def get_level(default='INFO'):
    try:
        return environ['DEBUG_LEVEL']
    except:
        return default
