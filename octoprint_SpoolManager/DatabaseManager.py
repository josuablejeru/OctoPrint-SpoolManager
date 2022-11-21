# coding=utf-8
import datetime
import json
import os
import logging
import shutil

from octoprint_SpoolManager.WrappedLoggingHandler import WrappedLoggingHandler
from peewee import *

from octoprint_SpoolManager.api import Transformer
from octoprint_SpoolManager.common import StringUtils
from octoprint_SpoolManager.models.PluginMetaDataModel import PluginMetaDataModel
from octoprint_SpoolManager.models.SpoolModel import SpoolModel


FORCE_CREATE_TABLES = False

CURRENT_DATABASE_SCHEME_VERSION = 7

# List all Models
MODELS = [PluginMetaDataModel, SpoolModel]


class DatabaseManager:
    class DatabaseSettings:
        # Internal stuff
        baseFolder = ""
        fileLocation = ""
        # External stuff
        useExternal = False
        type = "postgresql"  # postgresql,  mysql NOT sqlite
        name = ""
        host = ""
        port = 0
        user = ""
        password = ""

        def __str__(self):
            return str(self.__dict__)

    def __init__(self, parentLogger, sqlLoggingEnabled):
        self.sqlLoggingEnabled = sqlLoggingEnabled
        self._logger = logging.getLogger(
            parentLogger.name + "." + self.__class__.__name__
        )
        self._sqlLogger = logging.getLogger(
            parentLogger.name + "." + self.__class__.__name__ + ".SQL"
        )

        self._database = None
        self._databseSettings = None
        self._sendDataToClient = None
        self._isConnected = False
        self._currentErrorMessageDict = None

    def _buildDatabaseConnection(self):
        database = None
        if self._databaseSettings.useExternal == False:
            # local database`
            database = SqliteDatabase(self._databaseSettings.fileLocation)
        else:
            databaseType = self._databaseSettings.type
            databaseName = self._databaseSettings.name
            host = self._databaseSettings.host
            port = self._databaseSettings.port
            user = self._databaseSettings.user
            password = self._databaseSettings.password
            if "postgres" == databaseType:
                # Connect to a Postgres database.
                database = PostgresqlDatabase(
                    databaseName, user=user, password=password, host=host, port=port
                )
            else:
                # Connect to a MySQL database on network.
                database = MySQLDatabase(
                    databaseName, user=user, password=password, host=host, port=port
                )

        return database

    def _createDatabase(self, forceCreateTables):
        if forceCreateTables:
            self._logger.info("Creating new database-tables, because FORCE == TRUE!")
            self._createDatabaseTables()
        else:
            # check, if we need an scheme upgrade
            self._createOrUpgradeSchemeIfNecessary()

        self._logger.info("Database created-check done")

    def _createOrUpgradeSchemeIfNecessary(self):
        self._logger.info("Check if database-scheme upgrade needed...")
        schemeVersionFromDatabaseModel = None
        schemeVersionFromDatabase = None
        try:
            cursor = self.db.execute_sql(
                'select "value" from "spo_pluginmetadatamodel" where key="'
                + PluginMetaDataModel.KEY_DATABASE_SCHEME_VERSION
                + '";'
            )
            result = cursor.fetchone()
            if result != None:
                schemeVersionFromDatabase = int(result[0])
                self._logger.info(
                    "Current databasescheme: " + str(schemeVersionFromDatabase)
                )
            else:
                self._logger.warn(
                    "Strange, table is found (maybe), but there is no result of the schem version. Try to recreate a new db-scheme"
                )
                self.backupDatabaseFile()  # safty first
                self._createDatabaseTables()
                return
            pass
        except Exception as e:
            self._logger.exception(e)
            self.closeDatabase()
            errorMessage = str(e)
            if (
                # - SQLLite
                errorMessage.startswith("no such table")
                or
                # - Postgres
                "does not exist" in errorMessage
                or
                # - mySQL errorcode=1146
                "doesn't exist" in errorMessage
            ):
                self._createDatabaseTables()
                return
            else:
                self._logger.error(str(e))

        if not schemeVersionFromDatabase == None:
            currentDatabaseSchemeVersion = schemeVersionFromDatabase
            if currentDatabaseSchemeVersion < CURRENT_DATABASE_SCHEME_VERSION:
                # auto upgrade done only for local database
                if self._databaseSettings.useExternal == True:
                    self._logger.warn("Scheme upgrade is only done for local database")
                    return

                # evautate upgrade steps (from 1-2 , 1...6)
                self._logger.info(
                    "We need to upgrade the database scheme from: '"
                    + str(currentDatabaseSchemeVersion)
                    + "' to: '"
                    + str(CURRENT_DATABASE_SCHEME_VERSION)
                    + "'"
                )

                try:
                    self.backupDatabaseFile()
                    self._upgradeDatabase(
                        currentDatabaseSchemeVersion, CURRENT_DATABASE_SCHEME_VERSION
                    )
                except Exception as e:
                    self._logger.error("Error during database upgrade!!!!")
                    self._logger.exception(e)
                    return
                self._logger.info("...Database-scheme successfully upgraded.")
            else:
                self._logger.info("...Database-scheme upgraded not needed.")
        else:
            self._logger.warn(
                "...something was strange. Should not be shwon in log. Check full log"
            )
        pass

    def _executeSQLQuietly(self, cursor, sqlStatement):
        try:
            cursor.execute(sqlStatement)
        except Exception as e:
            self._logger.error(sqlStatement)
            self._logger.exception(e)

    def _createDatabaseTables(self):
        self._logger.info("Creating new database tables for spoolmanager-plugin")
        self._database.connect(reuse_if_open=True)
        self._database.drop_tables(MODELS)
        self._database.create_tables(MODELS)

        PluginMetaDataModel.create(
            key=PluginMetaDataModel.KEY_DATABASE_SCHEME_VERSION,
            value=CURRENT_DATABASE_SCHEME_VERSION,
        )
        self.closeDatabase()

    def _storeErrorMessage(self, type, title, message, sendErrorPopUp):
        # store current error message
        self._currentErrorMessageDict = {
            "type": type,
            "title": title,
            "message": message,
        }
        # send to client, if needed
        if sendErrorPopUp == True:
            self._passMessageToClient(type, title, message)

    ################################################################################################### public functions
    @staticmethod
    def buildDefaultDatabaseFileLocation(pluginDataBaseFolder):
        databaseFileLocation = os.path.join(pluginDataBaseFolder, "spoolmanager.db")
        return databaseFileLocation

    def initDatabase(self, databaseSettings, sendMessageToClient):

        self._logger.info("Init DatabaseManager")
        self._currentErrorMessageDict = None
        self._passMessageToClient = sendMessageToClient
        self._databaseSettings = databaseSettings

        databaseFileLocation = DatabaseManager.buildDefaultDatabaseFileLocation(
            databaseSettings.baseFolder
        )
        self._databaseSettings.fileLocation = databaseFileLocation
        existsDatabaseFile = str(os.path.exists(self._databaseSettings.fileLocation))
        self._logger.info(
            "Databasefile '"
            + self._databaseSettings.fileLocation
            + "' exists: "
            + existsDatabaseFile
        )

        import logging

        logger = logging.getLogger("peewee")
        # we need only the single logger without parent
        logger.parent = None
        # logger.addHandler(logging.StreamHandler())
        # activate SQL logging on PEEWEE side and on PLUGIN side
        # logger.setLevel(logging.DEBUG)
        # self._sqlLogger.setLevel(logging.DEBUG)
        self.showSQLLogging(self.sqlLoggingEnabled)

        wrappedHandler = WrappedLoggingHandler(self._sqlLogger)
        logger.addHandler(wrappedHandler)

        connected = self.connectoToDatabase(sendErrorPopUp=False)
        if connected == True:
            self._createDatabase(FORCE_CREATE_TABLES)
            self.closeDatabase()

        return self._currentErrorMessageDict

    def assignNewDatabaseSettings(self, databaseSettings):
        self._databaseSettings = databaseSettings

    def getDatabaseSettings(self):
        return self._databaseSettings

    def testDatabaseConnection(self, databaseSettings=None):
        result = None
        backupCurrentDatabaseSettings = None
        try:
            # use provided databasesettings or default if not provided
            if databaseSettings != None:
                backupCurrentDatabaseSettings = self._databaseSettings
                self._databaseSettings = databaseSettings

            succesfull = self.connectoToDatabase()
            if succesfull == False:
                result = self.getCurrentErrorMessageDict()
        finally:
            try:
                self.closeDatabase()
            except:
                pass  # do nothing
            if backupCurrentDatabaseSettings != None:
                self._databaseSettings = backupCurrentDatabaseSettings

        return result

    def getCurrentErrorMessageDict(self):
        return self._currentErrorMessageDict

    def connectoToDatabase(self, withMetaCheck=False, sendErrorPopUp=True):
        """
        connect to the current database
        """
        # reset current errorDict
        self._currentErrorMessageDict = None
        self._isConnected = False

        # build connection
        try:
            if self.sqlLoggingEnabled:
                self._logger.info("Databaseconnection with...")
                self._logger.info(self._databaseSettings)
            self._database = self._buildDatabaseConnection()

            # connect to Database
            DatabaseManager.db = self._database
            self._database.bind(MODELS)

            self._database.connect()
            if self.sqlLoggingEnabled:
                self._logger.info(
                    "Database connection succesful. Checking Scheme versions"
                )
            # TODO do I realy need to check the meta-infos in the connect function
            # schemeVersionFromPlugin = str(CURRENT_DATABASE_SCHEME_VERSION)
            # schemeVersionFromDatabaseModel = str(PluginMetaDataModel.get(PluginMetaDataModel.key == PluginMetaDataModel.KEY_DATABASE_SCHEME_VERSION).value)
            # if (schemeVersionFromPlugin != schemeVersionFromDatabaseModel):
            # 	errorMessage = "Plugin needs database scheme version: "+str(schemeVersionFromPlugin)+", but database has version: "+str(schemeVersionFromDatabaseModel);
            # 	self._storeErrorMessage("error", "database scheme version", errorMessage , False)
            # 	self._logger.error(errorMessage)
            # 	self._isConnected = False
            # else:
            # 	self._logger.info("...succesfull connected")
            # 	self._isConnected = True
            self._isConnected = True
        except Exception as e:
            errorMessage = str(e)
            self._logger.exception("connectoToDatabase")
            self.closeDatabase()
            # type, title, message
            self._storeErrorMessage(
                "error", "connection problem", errorMessage, sendErrorPopUp
            )
            return False
        return self._isConnected

    def closeDatabase(
        self,
    ):
        self._currentErrorMessageDict = None
        try:
            self._database.close()
            pass
        except Exception as e:
            pass  ## ignore close exception
        self._isConnected = False

    def isConnected(self):
        return self._isConnected

    def showSQLLogging(self, enabled):
        import logging

        logger = logging.getLogger("peewee")

        if enabled:
            logger.setLevel(logging.DEBUG)
            self._sqlLogger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.ERROR)
            self._sqlLogger.setLevel(logging.ERROR)

    def backupDatabaseFile(self):

        if os.path.exists(self._databaseSettings.fileLocation):
            self._logger.info("Starting database backup")
            now = datetime.datetime.now()
            currentDate = now.strftime("%Y%m%d-%H%M")
            currentSchemeVersion = "unknown"
            try:
                currentSchemeVersion = PluginMetaDataModel.get(
                    PluginMetaDataModel.key
                    == PluginMetaDataModel.KEY_DATABASE_SCHEME_VERSION
                )
                if currentSchemeVersion != None:
                    currentSchemeVersion = str(currentSchemeVersion.value)
            except Exception as e:
                self._logger.exception(
                    "Could not read databasescheme version:" + str(e)
                )

            backupDatabaseFilePath = (
                self._databaseSettings.fileLocation[0:-3]
                + "-backup-V"
                + currentSchemeVersion
                + "-"
                + currentDate
                + ".db"
            )
            # backupDatabaseFileName = "spoolmanager-backup-"+currentDate+".db"
            # backupDatabaseFilePath = os.path.join(backupFolder, backupDatabaseFileName)
            if not os.path.exists(backupDatabaseFilePath):
                shutil.copy(self._databaseSettings.fileLocation, backupDatabaseFilePath)
                self._logger.info(
                    "Backup of spoolmanager database created '"
                    + backupDatabaseFilePath
                    + "'"
                )
            else:
                self._logger.warn(
                    "Backup of spoolmanager database ('"
                    + backupDatabaseFilePath
                    + "') is already present. No backup created."
                )
            return backupDatabaseFilePath
        else:
            self._logger.info(
                "No database backup needed, because there is no databasefile '"
                + str(self._databaseSettings.fileLocation)
                + "'"
            )

    def reCreateDatabase(self, databaseSettings=None):
        self._currentErrorMessageDict = None
        self._logger.info("ReCreating Database")

        backupCurrentDatabaseSettings = None
        if databaseSettings != None:
            backupCurrentDatabaseSettings = self._databaseSettings
            self._databaseSettings = databaseSettings
        try:
            # - connect to dataabase
            self.connectoToDatabase()

            self._createDatabase(True)

            # - close dataabase
            self.closeDatabase()
        finally:
            # - restore database settings
            if backupCurrentDatabaseSettings != None:
                self._databaseSettings = backupCurrentDatabaseSettings

    def _handleReusableConnection(
        self,
        databaseCallMethode,
        withReusedConnection,
        methodeNameForLogging,
        defaultReturnValue=None,
    ):
        try:
            if withReusedConnection == True:
                if self._isConnected == False:
                    self._logger.error(
                        "Database not connected. Check database-settings!"
                    )
                    return defaultReturnValue
            else:
                self.connectoToDatabase()
            return databaseCallMethode()
        except Exception as e:
            errorMessage = "Database call error in methode " + methodeNameForLogging
            self._logger.exception(errorMessage)

            self._passMessageToClient(
                "error",
                "DatabaseManager",
                errorMessage + ". See OctoPrint.log for details!",
            )
            return defaultReturnValue
        finally:
            try:
                if withReusedConnection == False:
                    self._closeDatabase()
            except:
                pass  # do nothing
        pass

    def loadDatabaseMetaInformations(self, databaseSettings=None):

        backupCurrentDatabaseSettings = None
        if databaseSettings != None:
            backupCurrentDatabaseSettings = self._databaseSettings
        else:
            # use default settings
            databaseSettings = self._databaseSettings
            backupCurrentDatabaseSettings = self._databaseSettings
        # filelocation
        # backupname
        # scheme version
        # spoolitem count
        schemeVersionFromPlugin = CURRENT_DATABASE_SCHEME_VERSION
        localSchemeVersionFromDatabaseModel = "-"
        localSpoolItemCount = "-"
        externalSchemeVersionFromDatabaseModel = "-"
        externalSpoolItemCount = "-"
        errorMessage = ""
        loadResult = False
        # - save current DatbaseSettings
        # currentDatabaseSettings = self._databaseSettings
        # currentDatabase = self._database
        # externalConnected = False
        # always read local meta data
        try:
            currentDatabaseType = databaseSettings.type

            # First load meta from local sqlite database
            databaseSettings.type = "sqlite"
            databaseSettings.baseFolder = self._databaseSettings.baseFolder
            databaseSettings.fileLocation = self._databaseSettings.fileLocation
            self._databaseSettings = databaseSettings
            try:
                self.connectoToDatabase(sendErrorPopUp=False)
                localSchemeVersionFromDatabaseModel = PluginMetaDataModel.get(
                    PluginMetaDataModel.key
                    == PluginMetaDataModel.KEY_DATABASE_SCHEME_VERSION
                ).value
                localSpoolItemCount = self.countSpoolsByQuery()
                self.closeDatabase()
            except Exception as e:
                errorMessage = "local database: " + str(e)
                self._logger.error("Connecting to local database not possible")
                self._logger.exception(e)
                try:
                    self.closeDatabase()
                except Exception:
                    pass  # ignore close exception

            # Use orign Databasetype to collect the other meta dtaa (if neeeded)
            databaseSettings.type = currentDatabaseType
            if databaseSettings.useExternal == True:
                # External DB
                self._databaseSettings = databaseSettings
                self.connectoToDatabase(sendErrorPopUp=False)
                externalSchemeVersionFromDatabaseModel = PluginMetaDataModel.get(
                    PluginMetaDataModel.key
                    == PluginMetaDataModel.KEY_DATABASE_SCHEME_VERSION
                ).value
                externalSpoolItemCount = self.countSpoolsByQuery()
                self.closeDatabase()
            loadResult = True
        except Exception as e:
            errorMessage = str(e)
            self._logger.exception(e)
            try:
                self.closeDatabase()
            except Exception:
                pass  # ignore close exception
        finally:
            # restore orig. databasettings
            if backupCurrentDatabaseSettings != None:
                self._databaseSettings = backupCurrentDatabaseSettings

        return {
            "success": loadResult,
            "errorMessage": errorMessage,
            "schemeVersionFromPlugin": schemeVersionFromPlugin,
            "localSchemeVersionFromDatabaseModel": localSchemeVersionFromDatabaseModel,
            "localSpoolItemCount": localSpoolItemCount,
            "externalSchemeVersionFromDatabaseModel": externalSchemeVersionFromDatabaseModel,
            "externalSpoolItemCount": externalSpoolItemCount,
        }

    def loadFirstSingleSpool(self, withReusedConnection=False):
        def databaseCallMethode():
            return SpoolModel.select().limit(1)[0]

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadFirstSingleSpool"
        )

    def loadSpool(self, databaseId, withReusedConnection=False):
        def databaseCallMethode():
            return SpoolModel.get_or_none(databaseId)

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadSpool"
        )

    def loadSpoolTemplates(self, withReusedConnection=False):
        def databaseCallMethode():
            return SpoolModel.select().where(SpoolModel.isTemplate == True)

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadSpoolTemplates"
        )

    def loadAllSpoolsByQuery(self, tableQuery=None, withReusedConnection=False):
        def databaseCallMethode():
            if tableQuery == None:
                return SpoolModel.select().order_by(SpoolModel.created.desc())

            sortColumn = tableQuery["sortColumn"]
            sortOrder = tableQuery["sortOrder"]
            filterName = tableQuery["filterName"]

            if (
                "selectedPageSize" in tableQuery
                and StringUtils.to_native_str(tableQuery["selectedPageSize"]) == "all"
            ):
                myQuery = SpoolModel.select()
            else:
                offset = int(tableQuery["from"])
                limit = int(tableQuery["to"])
                myQuery = SpoolModel.select().offset(offset).limit(limit)

            if "materialFilter" in tableQuery:
                materialFilter = tableQuery["materialFilter"]
                vendorFilter = tableQuery["vendorFilter"]
                colorFilter = tableQuery["colorFilter"]

                # materialFilter
                # u'ABS,PLA'
                # u''
                # u'all'
                materialFilter = StringUtils.to_native_str(materialFilter)
                if materialFilter != "all":
                    if StringUtils.isEmpty(colorFilter):
                        myQuery = myQuery.where((SpoolModel.material == ""))
                    else:
                        allMaterials = materialFilter.split(",")
                        myQuery = myQuery.where(SpoolModel.material.in_(allMaterials))
                        # for material in allMaterials:
                        # 	myQuery = myQuery.orwhere((SpoolModel.material == material))
                # vendorFilter
                # u'MatterMost,TheFactory'
                # u''
                # u'all'
                vendorFilter = StringUtils.to_native_str(vendorFilter)
                if vendorFilter != "all":
                    if StringUtils.isEmpty(vendorFilter):
                        myQuery = myQuery.where((SpoolModel.vendor == ""))
                    else:
                        allVendors = vendorFilter.split(",")
                        myQuery = myQuery.where(SpoolModel.vendor.in_(allVendors))
                        # for vendor in allVendors:
                        # 	myQuery = myQuery.orwhere((SpoolModel.vendor == vendor))
                # colorFilter
                # u'#ff0000;red,#ff0000;keinRot,#ff0000;deinRot,#ff0000;meinRot,#ffff00;yellow'
                # u''
                # u'all'
                colorFilter = StringUtils.to_native_str(colorFilter)
                if colorFilter != "all" and StringUtils.isNotEmpty(colorFilter):
                    allColorObjects = colorFilter.split(",")
                    allColors = []
                    allColorNames = []
                    for colorObject in allColorObjects:
                        colorCodeColorName = colorObject.split(";")
                        color = colorCodeColorName[0]
                        colorName = colorCodeColorName[1]
                        allColors.append(color)
                        allColorNames.append(colorName)
                    myQuery = myQuery.where(SpoolModel.color.in_(allColors))
                    myQuery = myQuery.where(SpoolModel.colorName.in_(allColorNames))

                    #
                    # 	myQuery = myQuery.orwhere(  (SpoolModel.color == color) & (SpoolModel.colorName == colorName) )
                pass

            # mySqlText = myQuery.sql()

            if "onlyTemplates" in filterName:
                myQuery = myQuery.where((SpoolModel.isTemplate == True))
            else:
                if filterName == "hideEmptySpools":
                    myQuery = myQuery.where(
                        (SpoolModel.remainingWeight > 0)
                        | (SpoolModel.remainingWeight == None)
                    )
                if filterName == "hideInactiveSpools":
                    myQuery = myQuery.where((SpoolModel.isActive == True))
                if filterName == "hideEmptySpools,hideInactiveSpools":
                    myQuery = myQuery.where(
                        (
                            (SpoolModel.remainingWeight > 0)
                            | (SpoolModel.remainingWeight == None)
                        )
                        & (SpoolModel.isActive == True)
                    )

            if "displayName" == sortColumn:
                if "desc" == sortOrder:
                    myQuery = myQuery.order_by(fn.Lower(SpoolModel.displayName).desc())
                else:
                    myQuery = myQuery.order_by(fn.Lower(SpoolModel.displayName).asc())
            if "lastUse" == sortColumn:
                if "desc" == sortOrder:
                    myQuery = myQuery.order_by(SpoolModel.lastUse.desc())
                else:
                    myQuery = myQuery.order_by(SpoolModel.lastUse.asc())
            if "firstUse" == sortColumn:
                if "desc" == sortOrder:
                    myQuery = myQuery.order_by(SpoolModel.firstUse.desc())
                else:
                    myQuery = myQuery.order_by(SpoolModel.firstUse.asc())
            if "remaining" == sortColumn:
                if "desc" == sortOrder:
                    myQuery = myQuery.order_by(SpoolModel.remainingWeight.desc())
                else:
                    myQuery = myQuery.order_by(SpoolModel.remainingWeight.asc())
            if "material" == sortColumn:
                if "desc" == sortOrder:
                    myQuery = myQuery.order_by(SpoolModel.material.desc())
                else:
                    myQuery = myQuery.order_by(SpoolModel.material.asc())
            return myQuery

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadAllSpoolsByQuery"
        )

    def saveSpool(self, spoolModel, withReusedConnection=False):
        def databaseCallMethode():
            with self._database.atomic() as transaction:  # Opens new transaction.
                try:
                    databaseId = spoolModel.databaseId
                    if databaseId != None:
                        versionFromUI = None
                        # we need to update and we need to make sure nobody else modify the data
                        currentSpoolModel = self.loadSpool(
                            databaseId, withReusedConnection
                        )
                        if currentSpoolModel == None:
                            self._passMessageToClient(
                                "error",
                                "DatabaseManager",
                                "Could not update the Spool, because it is already deleted!",
                            )
                            return
                        else:
                            versionFromUI = (
                                spoolModel.version if spoolModel.version != None else 1
                            )
                            versionFromDatabase = (
                                currentSpoolModel.version
                                if currentSpoolModel.version != None
                                else 1
                            )
                            if versionFromUI != versionFromDatabase:
                                self._passMessageToClient(
                                    "error",
                                    "DatabaseManager",
                                    "Could not update the Spool, because someone already modified the spool. Do a manuel reload!",
                                )
                                return
                            # okay fits, increate version
                        newVersion = versionFromUI + 1
                        spoolModel.version = newVersion

                    # Not needed any more, we have multi-temlates
                    # if (spoolModel.isTemplate == True):
                    # 	#  remove template flag from last templateSpool
                    # 	SpoolModel.update({SpoolModel.isTemplate: False}).where(SpoolModel.isTemplate == True).execute()

                    spoolModel.save()
                    databaseId = spoolModel.get_id()
                    # do expicit commit
                    transaction.commit()
                except Exception as e:
                    # Because this block of code is wrapped with "atomic", a
                    # new transaction will begin automatically after the call
                    # to rollback().
                    transaction.rollback()
                    self._logger.exception("Could not insert Spool into database")

                    self._passMessageToClient(
                        "error",
                        "DatabaseManager",
                        "Could not insert the spool into the database. See OctoPrint.log for details!",
                    )
                pass

            return databaseId

        # always recalculate the remaing weight (total - used)
        totalWeight = spoolModel.totalWeight
        usedWeight = spoolModel.usedWeight
        if totalWeight != None:
            if usedWeight == None:
                usedWeight = 0.0
            remainingWeight = Transformer.calculateRemainingWeight(
                usedWeight, totalWeight
            )
            spoolModel.remainingWeight = remainingWeight

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "saveSpool"
        )

    def countSpoolsByQuery(self, withReusedConnection=False):
        def databaseCallMethode():
            myQuery = SpoolModel.select()
            return myQuery.count()

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "countSpoolsByQuery"
        )

    def loadCatalogVendors(self, withReusedConnection=False):
        def databaseCallMethode():
            result = set()
            result.add("")
            myQuery = SpoolModel.select(SpoolModel.vendor).distinct()
            for spool in myQuery:
                value = spool.vendor
                if value != None:
                    result.add(value)
            return result

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadCatalogVendors", set()
        )

    def loadCatalogMaterials(self, withReusedConnection=False):
        def databaseCallMethode():
            result = set()
            myQuery = SpoolModel.select(SpoolModel.material).distinct()
            for spool in myQuery:
                value = spool.material
                if value != None:
                    result.add(value)
            return result

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadCatalogMaterials", set()
        )

    def loadCatalogLabels(self, tableQuery, withReusedConnection=False):
        def databaseCallMethode():
            result = set()
            myQuery = SpoolModel.select(SpoolModel.labels).distinct()
            for spool in myQuery:
                value = spool.labels
                if value != None:
                    spoolLabels = json.loads(value)
                    for singleLabel in spoolLabels:
                        result.add(singleLabel)
            return result

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadCatalogLabels", set()
        )

    def loadCatalogColors(self, withReusedConnection=False):
        def databaseCallMethode():
            result = []
            myQuery = SpoolModel.select(
                SpoolModel.color, SpoolModel.colorName
            ).distinct()
            for spool in myQuery:
                if spool.color != None and spool.colorName:
                    colorInfo = {
                        "colorId": spool.color + ";" + spool.colorName,
                        "color": spool.color,
                        "colorName": spool.colorName,
                    }
                    result.append(colorInfo)
            return result

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "loadCatalogColors", set()
        )

    def deleteSpool(self, databaseId, withReusedConnection=False):
        def databaseCallMethode():
            with self._database.atomic() as transaction:  # Opens new transaction.
                try:
                    # first delete relations
                    # n = FilamentModel.delete().where(FilamentModel.printJob == databaseId).execute()
                    # n = TemperatureModel.delete().where(TemperatureModel.printJob == databaseId).execute()

                    deleteResult = SpoolModel.delete_by_id(databaseId)
                    if deleteResult == 0:
                        return None
                    return databaseId
                    pass
                except Exception as e:
                    # Because this block of code is wrapped with "atomic", a
                    # new transaction will begin automatically after the call
                    # to rollback().
                    transaction.rollback()
                    self._logger.exception(
                        "Could not delete spool from database:" + str(e)
                    )

                    self._passMessageToClient(
                        "Spool-DatabaseManager",
                        "Could not delete the spool ('"
                        + str(databaseId)
                        + "') from the database. See OctoPrint.log for details!",
                    )
                    return None
                pass

        return self._handleReusableConnection(
            databaseCallMethode, withReusedConnection, "deleteSpool"
        )
