import os

import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import SqlLexer

from .common import (PDL_SEARCH_URL, PROMPT_STYLE, prompt_continuation, toolbar_factory)


def prompt_session(settings, config_dir):
    command_completer = WordCompleter("""
            mode sql es enrich copy
        """.split(),
        ignore_case = True
    )
    return PromptSession(
        lexer = PygmentsLexer(SqlLexer),
        completer = command_completer,
        style = PROMPT_STYLE,
        history = FileHistory(os.path.join(config_dir, "sql.history")),
        multiline = True,
        prompt_continuation = prompt_continuation,
        bottom_toolbar = toolbar_factory(settings)
    )


def query(api_key, query, size=1, offset=0):
    '''ElasticSearch SQL query
    '''
    headers = {
        'Content-Type': 'application/json',
        'X-api-key': api_key
    }
    params = { 'sql': query, 'size': size, 'from': offset, 'pretty': True }
    response = requests.get(PDL_SEARCH_URL, headers=headers, params=params)
    if response.status_code == requests.codes.ok:
        return response

    return "Invalid SQL query."

