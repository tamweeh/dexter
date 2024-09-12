import datetime as dt
import logging

date = dt.datetime.now().strftime('%Y%m%d')
# class OptionalFieldFilter(logging.Filter):
#     def __init__(self, **kwargs):
#         super().__init__()
#         self.defaults = kwargs
#
#     def filter(self, record):
#         # Check if the field exists, if not, set a default value
#         for key, value in self.defaults.items():
#             if not hasattr(record, key):
#                 setattr(record, key, value)
#         return True


def get_logger(log_format='%(asctime)s app=%(name)s level=%(levelname)s message=%(message)s', log_name='', log_file_info=f'./logs/{date}.log', log_file_error=f'./logs/{date}.err'):
    log = logging.getLogger(log_name)
    log_formatter = logging.Formatter(log_format)

    if log.hasHandlers():
        log.handlers.clear()

    # comment this to suppress console output
    stream_handler = logging.StreamHandler(stream=None)
    stream_handler.setFormatter(log_formatter)
    log.addHandler(stream_handler)

    file_handler_info = logging.FileHandler(log_file_info, mode='a', encoding='utf-8')
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(logging.DEBUG)
    file_handler_info.addFilter(lambda record: record.levelno < logging.ERROR)
    log.addHandler(file_handler_info)

    file_handler_error = logging.FileHandler(log_file_error, mode='a', encoding='utf-8')
    file_handler_error.setFormatter(log_formatter)
    file_handler_error.setLevel(logging.ERROR)
    log.addHandler(file_handler_error)

    # optional_filter = OptionalFieldFilter(query='N/A')
    # log.addFilter(optional_filter)
    log.setLevel(logging.DEBUG)
    log.propagate = False

    return log