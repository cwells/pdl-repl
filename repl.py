#!/bin/env python

import json
import os
import re
from urllib.parse import parse_qs

import click
import pyperclip
import requests
import yaml
from box import Box
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from pygments.lexers import JsonLexer
from pygments.lexers.sql import SqlLexer
from pygments import highlight, lexers, formatters

PDL_VERSION = "v5"
PDL_ENRICH_URL = f"https://api.peopledatalabs.com/{PDL_VERSION}/person/enrich"
PDL_SEARCH_URL = f"https://api.peopledatalabs.com/{PDL_VERSION}/person/search"

PROMPT_STYLE = Style.from_dict({
    "completion-menu.completion": "bg:#008888 #ffffff",
    "completion-menu.completion.current": "bg:#00aaaa #000000",
    "scrollbar.background": "bg:#88aaaa",
    "scrollbar.button": "bg:#222222",
})

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pdl-repl")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.yaml")

os.makedirs(CONFIG_DIR, exist_ok=True)


class ParseError(Exception): pass


#
# help
#
def help():
    strings = [
        "mode [sql|es|enrich]\n\tchange REPL mode",
        "set [size|offset|pretty] <value>\n\tchange settings",
        "copy\n\tcopy last result to clipboard",
    ]
    return "\n".join(strings)


#
# prompts
#
def toolbar_factory(settings):
    def toolbar():
        status = "  ".join([ f"{k}={v}" for k, v in settings.items() ])
        return HTML(
            f'<style fg="blue" bg="white">{status:^40}</style>'
            '      '
            'Press [Alt+Enter] to evaluate an expression or [Ctrl+d] to exit.'
        )
    return toolbar


def prompt_continuation(width, line_number, is_soft_wrap):
    return '.' * width


def enrich_prompt_session():
    return PromptSession(
        history = FileHistory(os.path.join(CONFIG_DIR, "enrich.history")),
        multiline = True,
        prompt_continuation = prompt_continuation,
    )


def es_prompt_session(settings):
    return PromptSession(
        lexer = PygmentsLexer(JsonLexer),
        style = PROMPT_STYLE,
        history = FileHistory(os.path.join(CONFIG_DIR, "es.history")),
        multiline = True,
        prompt_continuation = prompt_continuation,
        bottom_toolbar = toolbar_factory(settings)
    )


def sql_prompt_session(settings):
    command_completer = WordCompleter("""
            mode sql es enrich copy
        """.split(),
        ignore_case = True
    )
    return PromptSession(
        lexer = PygmentsLexer(SqlLexer),
        completer = command_completer,
        style = PROMPT_STYLE,
        history = FileHistory(os.path.join(CONFIG_DIR, "sql.history")),
        multiline = True,
        prompt_continuation = prompt_continuation,
        bottom_toolbar = toolbar_factory(settings)
    )


#
# configuration
#
def read_config(ctx, param, value):
    '''read configuration file
    '''
    defaults = Box(repl = {
        'mode': 'sql',
        'search': { 'size': 1, 'offset': 0, 'pretty': True }
    })
    try:
        with open(value, 'rb') as config:
            defaults.merge_update(**yaml.load(config, Loader=yaml.FullLoader))
    except Exception as e:
        print(f"No config file found at {value}, aborting.")
        raise SystemExit(1)

    return defaults


def parse_set(text):
    '''set command allows changing configuration on the fly
    '''
    def str2bool(s):
        return s.lower() == 'true'

    typemap = {
        'pretty': str2bool,
        'size': int,
        'offset': int,
    }
    match = re.match(r'set\s+(?P<var>[a-zA-Z]+)\s+(?P<val>.+)', text)
    if match:
        var = match.groupdict()['var']
        val = match.groupdict()['val']
        return var, typemap.get(var, str)(val)

    raise ParseError


def parse_mode(text):
    '''allow changing mode of repl
    available modes are:
    - es: ElasticSearch query
    - sql: SQL query
    - enrich: URL query string
    '''
    try:
        _, mode = text.split()
    except:
        raise ParseError

    if mode in ['es', 'sql', 'enrich']:
        return mode

    raise ValueError(mode)


#
# queries
#
def enrich_query(api_key, qs):
    '''parses URL query string and calls the enrichment API
    '''
    query = parse_qs(qs)
    params = { 'api_key': api_key, **query }
    response = requests.get(PDL_ENRICH_URL, params=params)

    if response.status_code == requests.codes.ok:
        return response

    return "Invalid query."


def sql_query(api_key, sql, size=1, offset=0):
    '''ElasticSearch SQL query
    '''
    headers = {
        'Content-Type': 'application/json',
        'X-api-key': api_key
    }
    params = { 'sql': sql, 'size': size, 'from': offset, 'pretty': True }
    response = requests.get(PDL_SEARCH_URL, headers=headers, params=params)
    if response.status_code == requests.codes.ok:
        return response

    return "Invalid SQL query."


def es_query(api_key, query, size=1, offset=0):
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


#
# repl
#
@click.command()
@click.option('--config', '-c', callback=read_config, default=CONFIG_FILE, help="path to config file")
def repl(config):
    result = ''
    sessions = {
        'sql': sql_prompt_session(config.repl.search),
        'es': es_prompt_session(config.repl.search),
        'enrich': enrich_prompt_session(),
    }

    while True:
        try:
            text = sessions[config.repl.mode].prompt(f"{config.repl.mode}> ").strip()
        except KeyboardInterrupt:
            continue  # Control-C pressed. Try again.
        except EOFError:
            break  # Control-D pressed.

        if not text:
            continue

        if text.lower() == "help":
            print(help())
            continue

        if text.lower() == "copy":
            if result:
                pyperclip.copy(result)
            else:
                print("No data to copy.")
            continue

        if text.lower().startswith("mode "):
            try:
                mode = parse_mode(text)
            except ParseError as e:
                print("Invalid mode command")
            except ValueError as e:
                print(f"Invalid mode '{e}'. Valid values are [sql, es, enrich]")
            else:
                config.repl.mode = mode
            continue

        if text.lower().startswith("set "):
            try:
                var, val = parse_set(text)
            except ParseError as e:
                print("Invalid set command")
            else:
                print(var, val)
                config.repl.search[var] = val
            continue

        if config.repl.mode == 'sql':
            response = sql_query(
                api_key = config.api_key,
                sql = text,
                size = config.repl.search.size,
                offset = config.repl.search.offset
            )
        elif config.repl.mode == 'es':
            response = es_query(
                api_key = config.api_key,
                query = text,
                size = config.repl.search.size,
                offset = config.repl.search.offset
            )
        elif config.repl.mode == 'enrich':
            response = enrich_query(
                api_key = config.api_key,
                qs = text,
            )

        result = json.dumps(
            response.json(),
            indent = 2 if config.repl.search.pretty else None)
        print(
            highlight(
                result,
                lexers.JsonLexer(),
                formatters.TerminalFormatter()
            )
        )

    print("Exiting.")


#
# entrypoint
#
if __name__ == '__main__':
    repl()
