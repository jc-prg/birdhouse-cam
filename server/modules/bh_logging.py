import logging
import time
from logging.handlers import RotatingFileHandler
from modules.presets import birdhouse_log_filename, birdhouse_loglevel_module
from modules.presets import logger_list, loggers, logger_exists


def Logging(name, log_as_file):

    init_time = time.time()

    if loggers.get(name) or name in logger_list:
        print("... logger already exists: " + name)
        return loggers.get(name)

    else:
        logger_exists[name] = init_time
        logger_list.append(name)

        if name not in birdhouse_loglevel_module:
            log_level = logging.INFO
            print("Key '" + name + "' is not defined in preset.py in 'birdhouse_loglevel_module'.")
        else:
            log_level = birdhouse_loglevel_module[name]

        logger = logging.getLogger(name+str(init_time))
        logger.setLevel(log_level)

        if log_as_file:
            # log_format = logging.Formatter(fmt='%(asctime)s |' + str(len(logger_list)).zfill(
            #    3) + '| %(levelname)-8s '+name.ljust(10)+' | %(message)s', # + "\n" + str(logger_list),
            #                               datefmt='%m/%d %H:%M:%S')

            log_format = logging.Formatter(fmt='%(asctime)s | %(levelname)-8s '+name.ljust(10)+' | %(message)s',
                                           datefmt='%m/%d %H:%M:%S')
            handler = RotatingFileHandler(filename=birdhouse_log_filename, mode='a',
                                          maxBytes=int(2.5 * 1024 * 1024),
                                          backupCount=2, encoding=None, delay=False)
            handler.setFormatter(log_format)
            logger.addHandler(handler)

        else:
            logging.basicConfig(format='%(asctime)s | %(levelname)-8s %(name)-10s | %(message)s',
                                datefmt='%m/%d %H:%M:%S',
                                level=log_level)

        loggers[name] = logger
        return logger
