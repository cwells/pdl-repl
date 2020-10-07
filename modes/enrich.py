import json
import os

import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from .common import (PDL_ENRICH_URL, PROMPT_STYLE, prompt_continuation, toolbar_factory)


def prompt_session(settings, config_dir):
    return PromptSession(
        history = FileHistory(os.path.join(config_dir, "enrich.history")),
        multiline = True,
        prompt_continuation = prompt_continuation,
        vi_mode = settings.editor == 'vi'
    )


def query(api_key, query, *args, **kw):
    '''calls enrichment API with JSON params
    '''
    params = { 'api_key': api_key, **json.loads(query) }
    response = requests.get(PDL_ENRICH_URL, params=params)

    if response.status_code == requests.codes.ok:
        return response

    return "Invalid query."
