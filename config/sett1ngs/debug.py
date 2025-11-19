from .base import *

if deploy == "True":
    DATA_UPLOAD_MAX_NUMBER_FIELDS = env("MAX_NUMBER_FIELDS")

