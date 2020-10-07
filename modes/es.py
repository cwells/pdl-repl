import os

import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import JsonLexer

from .common import (PDL_SEARCH_URL, PROMPT_STYLE, prompt_continuation, toolbar_factory)


def prompt_session(settings, config_dir):
    return PromptSession(
        lexer = PygmentsLexer(JsonLexer),
        style = PROMPT_STYLE,
        history = FileHistory(os.path.join(config_dir, "es.history")),
        multiline = True,
        prompt_continuation = prompt_continuation,
        bottom_toolbar = toolbar_factory(settings)
    )


def query(api_key, query, size=1, offset=0):
    '''ElasticSearch query
    '''
    headers = {
        'Content-Type': 'application/json',
        'X-api-key': api_key
    }
    params = { 'query': query, 'size': size, 'from': offset, 'pretty': True }
    response = requests.get(PDL_SEARCH_URL, headers=headers, params=params)
    if response.status_code == requests.codes.ok:
        return response

    return "Invalid ES query."
