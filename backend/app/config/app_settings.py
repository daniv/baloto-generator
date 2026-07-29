"""
Define validated configuration models for the backend application.

The module centralizes application metadata, lottery-specific limits, database
connection settings, console configuration, and environment-driven values. It
uses Pydantic settings models to validate defaults, load values from environment
files, and reject insecure database credentials before the application starts.
"""

import calendar
from datetime import date
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    PostgresDsn,
    SecretStr,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console


class BalotoModel(BaseModel):
    """
    Store validated domain limits and defaults for supported lottery games.

    The model centralizes number ranges, jackpot thresholds, and other immutable
    configuration values used by Baloto, Revancha, and MiLoto schemas. Keeping
    these rules in one validated object prevents domain constraints from being
    duplicated across models, API handlers, and tests.
    """

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    miloto_first_id: Annotated[int, Field(ge=1, description="The first miloto game id. default 1")] = 1
    miloto_first_date: Annotated[date, Field(description="The date for the first miloto game")] = date(2023, 10, 23)
    miloto_min_jackpot: Annotated[
        int, Field(description="The minimum miloto game jackpot prize. default $120M COP")
    ] = 120_000_000  #  COP
    miloto_weekdays: list[Annotated[int, Field(min_length=1, max_length=4)]] = [
        calendar.MONDAY,
        calendar.TUESDAY,
        calendar.THURSDAY,
        calendar.FRIDAY,
    ]
    miloto_min_hits_prize: Annotated[int, Field(description="The miloto minimum prize (2 hits) default = $4K COP")] = (
        4_000
    )
    miloto_max_num: Annotated[int, Field(description="The miloto game max number. default = 39")] = 39

    baloto_min_jackpot: Annotated[
        int, Field(description="The minimum baloto game jackpot prize. default $2000M COP")
    ] = 2_000_000_000  #  COP
    baloto_min_hits_prize: Annotated[
        int, Field(description="The baloto minimum prize (balota hit) default = $6K COP")
    ] = 6_000
    revancha_min_hits_prize: Annotated[
        int, Field(description="The miloto revancha prize (1 balota) default = $3K COP")
    ] = 3000
    baloto_first_id: Annotated[int, Field(description="The first baloto game id. default 2082")] = 2082
    baloto_first_date: Annotated[date, Field(description="The date for the first baloto game")] = date(2021, 5, 5)
    baloto_max_num: Annotated[int, Field(description="The baloto-revanch game max number. default = 43")] = 43
    balota_max_num: Annotated[int, Field(description="The baloto-revanch balota max number. default = 16")] = 16
    baloto_weekdays: list[Annotated[int, Field(min_length=1, max_length=4)]] = [
        calendar.MONDAY,
        calendar.WEDNESDAY,
        calendar.SATURDAY,
    ]

    miloto_baseurl: HttpUrl = HttpUrl("https://www.baloto.com/miloto/resultados-miloto")
    baloto_baseurl: HttpUrl = HttpUrl("https://www.baloto.com/resultados-baloto")
    revancha_baseurl: HttpUrl = HttpUrl("https://www.baloto.com/resultados-revancha")


class DatabaseSettings(BaseSettings):
    """
    Load and validate PostgreSQL connection settings from the environment.

    The model owns database credentials, host information, connection options,
    and the derived connection URL used by SQLAlchemy. It also validates the
    configured password so the insecure default value cannot reach application
    startup.
    """

    model_config = SettingsConfigDict(
        validate_default=True, case_sensitive=False, env_file="../.env", env_file_encoding="utf-8"
    )

    db_user: str = "postgres"
    db_password: SecretStr = Field(default_factory=lambda: SecretStr("CHANGE_ME"))
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "baloto_co"
    db_name_test: str = "test"

    @computed_field
    @property
    def pg_dsn(self) -> PostgresDsn:
        """
        The async database connection string used by the SQLAlchemy engine.

        :return: A validated Postgres DSN using the asyncpg driver.
        """
        secret_value = self.db_password.get_secret_value()
        return PostgresDsn(
            f"postgresql+asyncpg://{self.db_user}:{secret_value}@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @model_validator(mode="after")
    def verify_db_password_is_changed(self) -> Self:
        """
        Reject the insecure default database password during validation.

        :return: The validated database settings instance.
        :raises ValueError: If the configured database password is still ``CHANGE_ME``.
        """
        if self.db_password.get_secret_value() == "CHANGE_ME":
            err_msg = "Security Alert: You must override the default DB password!"
            raise ValueError(err_msg)
        return self


class ApplicationSettings(BaseSettings):
    """
    Store public metadata used to describe the backend application.

    The model provides the application title, version, and human-readable
    description consumed when creating the FastAPI instance and generating
    its OpenAPI documentation.
    """

    title: str = "Generador Baloto"
    version: str = "0.1.0"
    description: str = "API for lottery combination generation and historical statistics"


class Settings(BaseSettings):
    """
    Aggregate validated configuration required by the backend application.

    The model combines database settings, lottery rules, application metadata,
    and Rich console instances into a single settings object imported by the
    API, persistence, and schema layers.
    """

    model_config = SettingsConfigDict(validate_default=True)

    db_settings: DatabaseSettings = Field(default_factory=DatabaseSettings)
    console: Console = Console(color_system="truecolor", force_terminal=True)
    error_console: Console = Console(color_system="256", force_terminal=True, stderr=True)
    baloto_settings: BalotoModel = Field(default_factory=BalotoModel)
    app_settings: ApplicationSettings = Field(default_factory=ApplicationSettings)

    app_name: str = "Awesome API"
    items_per_user: int = 50


settings = Settings()
