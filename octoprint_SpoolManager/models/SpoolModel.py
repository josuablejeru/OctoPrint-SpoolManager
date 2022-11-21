# coding=utf-8
from peewee import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    FloatField,
    IntegerField,
    TextField,
)

from octoprint_SpoolManager.models.BaseModel import BaseModel


class SpoolModel(BaseModel):
    isActive = BooleanField(null=True)
    isTemplate = BooleanField(null=True)
    displayName = CharField(null=True)
    vendor = CharField(null=True, index=True)
    totalWeightInGram = FloatField(null=True)
    spoolWeightInGram = FloatField(null=True)
    usedWeightInGram = FloatField(null=True)
    remainingWeightInGram = FloatField(null=True)

    totalLengthInMM = IntegerField(null=True)
    usedLengthInMM = IntegerField(null=True)
    BarOrQRcode = CharField(null=True)

    firstUse = DateTimeField(null=True)
    lastUse = DateTimeField(null=True)

    purchasedFrom = CharField(null=True)
    purchasedOn = DateField(null=True)
    cost = FloatField(null=True)
    costUnit = CharField(
        null=True
    )  # deprecated needs to be removed, value should be used from pluginSettings

    labels = TextField(null=True)

    noteText = TextField(null=True)
    noteDeltaFormat = TextField(null=True)
    noteHtml = TextField(null=True)

    material = CharField(null=True, index=True)
    materialCharacteristic = CharField(null=True, index=True)
    density = FloatField(null=True)

    diameter = FloatField(null=True)
    diameterTolerance = FloatField(null=True)
    colorName = CharField(null=True)
    color = CharField(null=True)

    flowRateCompensation = IntegerField(null=True)

    temperature = IntegerField(null=True)
    bedTemperature = IntegerField(null=True)
    enclosureTemperature = IntegerField(null=True)
    offsetTemperature = IntegerField(null=True)
    offsetBedTemperature = IntegerField(null=True)
    offsetEnclosureTemperature = IntegerField(null=True)
