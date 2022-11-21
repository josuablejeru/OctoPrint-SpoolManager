# coding=utf-8
from octoprint_SpoolManager.common import StringUtils
from octoprint_SpoolManager.models.SpoolModel import SpoolModel


def calculateRemainingWeight(usedWeight, totalWeight):
    if usedWeight == None or totalWeight == None:
        return None

    if (type(usedWeight) == int or type(usedWeight) == float) and (
        type(totalWeight) == int or type(totalWeight) == float
    ):
        result = totalWeight - usedWeight
        return result

    return None


def _calculateRemainingPercentage(remainingWeight, totalWeight):
    if remainingWeight == None or totalWeight == None:
        return None

    if (
        (type(remainingWeight) == int or type(remainingWeight) == float)
        and (type(totalWeight) == int or type(totalWeight) == float)
        and (totalWeight > 0)
    ):
        result = remainingWeight / (totalWeight / 100.0)
        return result

    return None


def _calculateUsedPercentage(usedWeight, totalWeight):
    if usedWeight == None or totalWeight == None:
        return None

    if (
        (type(usedWeight) == int or type(usedWeight) == float)
        and (type(totalWeight) == int or type(totalWeight) == float)
        and (totalWeight > 0)
    ):
        result = usedWeight / (totalWeight / 100.0)
        return result

    return None


def transformSpoolModelToDict(spoolModel):
    spoolAsDict = spoolModel.__data__

    # Date time needs to be converted
    spoolAsDict["firstUse"] = StringUtils.formatDateTime(spoolModel.firstUse)
    spoolAsDict["lastUse"] = StringUtils.formatDateTime(spoolModel.lastUse)
    spoolAsDict["purchasedOn"] = StringUtils.formatDateTime(spoolModel.purchasedOn)

    spoolAsDict["created"] = StringUtils.formatDateTime(spoolModel.created)
    spoolAsDict["updated"] = StringUtils.formatDateTime(spoolModel.updated)

    totalWeight = spoolModel.totalWeightInGram
    usedWeight = spoolModel.usedWeightInGram
    remainingWeight = calculateRemainingWeight(usedWeight, totalWeight)
    remainingPercentage = _calculateUsedPercentage(remainingWeight, totalWeight)
    usedPercentage = _calculateUsedPercentage(usedWeight, totalWeight)

    spoolAsDict["remainingWeight"] = StringUtils.formatFloat(remainingWeight)
    spoolAsDict["remainingPercentage"] = StringUtils.formatFloat(remainingPercentage)
    spoolAsDict["usedPercentage"] = StringUtils.formatFloat(usedPercentage)

    # Decimal and date time needs to be converted. ATTENTION orgiginal fields will be modified
    spoolAsDict["totalWeight"] = StringUtils.formatFloat(spoolModel.totalWeightInGram)
    spoolAsDict["spoolWeight"] = StringUtils.formatFloat(spoolModel.spoolWeightInGram)
    spoolAsDict["usedWeight"] = StringUtils.formatFloat(spoolModel.usedWeightInGram)

    usedLength = spoolModel.usedLengthInMM
    totalLength = spoolModel.totalLengthInMM
    remainingLength = calculateRemainingWeight(usedLength, totalLength)
    remainingLengthPercentage = _calculateUsedPercentage(remainingLength, totalLength)
    usedLengthPercentage = _calculateUsedPercentage(usedLength, totalLength)

    spoolAsDict["remainingLength"] = StringUtils.formatInt(remainingLength)
    spoolAsDict["remainingLengthPercentage"] = StringUtils.formatInt(
        remainingLengthPercentage
    )
    spoolAsDict["usedLengthPercentage"] = StringUtils.formatInt(usedLengthPercentage)

    return spoolAsDict


def transformAllSpoolModelsToDict(allSpoolModels):
    result = []
    if allSpoolModels != None:
        for job in allSpoolModels:
            spoolAsDict = transformSpoolModelToDict(job)
            result.append(spoolAsDict)
    return result
