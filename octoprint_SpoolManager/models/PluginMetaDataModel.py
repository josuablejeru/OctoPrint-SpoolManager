# coding=utf-8
from peewee import CharField

from octoprint_SpoolManager.models.BaseModel import BaseModel


class PluginMetaDataModel(BaseModel):

    KEY_PLUGIN_VERSION = "pluginVersion"
    KEY_DATABASE_SCHEME_VERSION = "databaseSchemeVersion"

    key = CharField(null=False)
    value = CharField(null=False)
