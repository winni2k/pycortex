import logging

log_level_conversion_table = {
    0: 'NOTSET',
    10: 'DEBUG',
    20: 'INFO',
    30: 'WARNING',
    40: 'ERROR',
    50: 'CRITICAL',
}


def configure_logging_from_args(args):
    """Checks args for --silent and --verbose mode and sets the logging level appropriately"""
    if args.get('--verbose'):
        log_level = logging.DEBUG
    elif args.get('--silent'):
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    logging.basicConfig(level=log_level)
    logger = logging.getLogger('cortexpy')
    logger.info('Log level is {}'.format(log_level_conversion_table[logger.getEffectiveLevel()]))