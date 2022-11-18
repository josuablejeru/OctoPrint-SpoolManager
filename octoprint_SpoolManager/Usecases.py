# coding=utf-8
from __future__ import absolute_import


##############
#
######
class Usecases:
    """
    Class is responsible for the needed usecases. E.g. saveSpool, calculations,, transaction
    No technical stuff should be implemented here. E.g. sql-query, ..
    """

    def __init__(self, parentLogger, databaseManager):
        self._logger = logging.getLogger(
            parentLogger.name + "." + self.__class__.__name__
        )

    def saveSpool(self, spoolModel):
        pass
