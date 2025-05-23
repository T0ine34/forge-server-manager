import os
from abc import ABC

from config import JSONConfig
from gamuLogger import Logger

from ..database.database import Database

Logger.set_module("base_server")

BASE_PATH = __file__[:__file__.rfind('/')] # get the base path of the server

STATIC_PATH = f'{os.path.dirname(BASE_PATH)}/client'

class BaseServer(ABC):
    def __init__(self, config_path: str):
        """
        Initialize the BaseServer class.
        :param config_path: Path to the configuration file.
        """
        if hasattr(self, '_initalized'): # prevent multiple initalizations
            Logger.trace("BaseServer already initialized")
            return
        Logger.trace("Initializing BaseServer")
        self._initalized = True
        Logger.info(f"Using config path: {config_path}")
        self.config = JSONConfig(config_path)
        self.database = Database(self.config.get("database_path"))
