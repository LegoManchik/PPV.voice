import datetime
import logging


class BotLogger:
    def __init__(self):
        self.logger = logging.getLogger("discord")
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        self.file_handler = logging.FileHandler(
            f"logs/log-{datetime.datetime.now().strftime('%d-%m-%Y--%H-%M-%S')}",
            encoding='utf-8')

        self.file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s: %(message)s',
                                      datefmt='%d-%m-%Y %H:%M:%S')

        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        self.logger.addHandler(stream_handler)

    def get_logger(self):
        return self.logger

