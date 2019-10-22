import logging

import rx

from services.service_provider import SubjectProvider, ImageSourceProvider


class BaseSOP(object):

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger("console")
        self.subjects = SubjectProvider().get_or_create_instance(None)

        self.stoppable = True

    def exec(self) -> rx.Observable:
        pass

    @staticmethod
    def get_name() -> str:
        pass


_sop = []


def register_sop(cls):
    _sop.append(cls)
