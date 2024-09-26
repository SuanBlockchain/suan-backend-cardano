import os
import pathlib
from configparser import ConfigParser
from typing import List, Union

from pydantic import AnyHttpUrl, EmailStr
from pydantic_settings import BaseSettings

# Project Directories
ROOT = pathlib.Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Class representing some settings for FastAPI"""
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(self, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # SQLALCHEMY_DATABASE_URI: Optional[str] = "sqlite:///example.db"
    FIRST_SUPERUSER: EmailStr = "admin@recipeapi.com"  # type: ignore

    class Config:
        """Class to define case_sensitive variable"""
        case_sensitive = True


settings = Settings()


def config(
    config_path: str = f"{ROOT}/credentials.local.ini", section: str = ""
) -> dict:
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(config_path)

    # get section
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            os.environ[param[0]] = param[1]
            db[param[0]] = param[1]
    else:
        raise Exception(
            f"Section {section} not found in the config_path file"
        )

    return db
