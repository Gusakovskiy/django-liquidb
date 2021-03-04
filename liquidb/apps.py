from django.apps import AppConfig

from liquidb.consts import SELF_NAME


class LiquidbDjangoConfig(AppConfig):
    name = SELF_NAME
