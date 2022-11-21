from enum import Enum

from peewee import Database, DatabaseProxy, PostgresqlDatabase, SqliteDatabase

database_proxy = DatabaseProxy()


class DatabaseTypes(Enum):
    SQL_LITE = "sqllite"
    POSTGRESQL = "postgresql"


def init_database_instance(db_type: DatabaseTypes) -> Database:
    database = None

    if db_type.POSTGRESQL:
        database = PostgresqlDatabase()
    if db_type.SQL_LITE:
        database = SqliteDatabase()

    if database == None:
        raise ConnectionAbortedError("No known database defined")

    database_proxy.initialize(database)

    return database
