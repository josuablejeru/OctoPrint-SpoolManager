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
