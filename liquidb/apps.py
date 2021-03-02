from django.apps import AppConfig

from .management.consts import SELF_NAME


class LiquidbDjangoConfig(AppConfig):
    name = SELF_NAME
