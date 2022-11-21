# coding=utf-8
from __future__ import absolute_import

import datetime

from peewee import AutoField, DateTimeField, FixedCharField, Model, SmallIntegerField


def make_table_name(model_class):
    model_name = model_class.__name__
    return "spo_" + model_name.lower()


class BaseModel(Model):

    databaseId = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    updated = DateTimeField(default=datetime.datetime.now)
    version = SmallIntegerField(null=True)
    originator = FixedCharField(null=True, max_length=60)

    class Meta:
        table_function = make_table_name
        pass
