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
# prompts
#
def enrich_prompt_session():
    return PromptSession(
        history = FileHistory(os.path.join(CONFIG_DIR, "enrich.history")),
        multiline = True
    )


def es_prompt_session():
    return PromptSession(
        lexer = PygmentsLexer(JsonLexer),
        style = PROMPT_STYLE,
        history = FileHistory(os.path.join(CONFIG_DIR, "es.history")),
        multiline = True
    )


def sql_prompt_session():
    sql_completer = WordCompleter("""
        abort action add after all alter analyze and as
        asc attach autoincrement before begin between by
        cascade case cast check collate column commit
        conflict constraint create cross current_date
        current_time current_timestamp database default deferrable
        deferred delete desc detach distinct drop each else
        end escape except exclusive exists explain fail for
        foreign from full glob group having if ignore
        immediate in index indexed initially inner insert
        instead intersect into is isnull join key left
        like limit match natural no not notnull null of
        offset on or order outer plan pragma primary
        query raise recursive references regexp reindex
        release rename replace restrict right rollback row
        savepoint select set table temp temporary then to
        transaction trigger union unique update using vacuum
        values view virtual when where with without
        """.split(),
        ignore_case = True
    )
    return PromptSession(
        lexer = PygmentsLexer(SqlLexer),
        completer = sql_completer,
        style = PROMPT_STYLE,
        history = FileHistory(os.path.join(CONFIG_DIR, "sql.history")),
        multiline = True
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
    match = re.match(r'set\s+(?P<var>[a-zA-Z]+)\s*=\s*(?P<val>[0-9]+)', text)
    if match:
        var = match.groupdict()['var']
        val = match.groupdict()['val']
        return var, val

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
        return json.dumps(response.json(), indent=2)

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
        return json.dumps(response.json(), indent=2)

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
        return json.dumps(response.json(), indent=2)

    return "Invalid ES query."


#
# repl
#
@click.command()
@click.option('--config', '-c', callback=read_config, default=CONFIG_FILE, help="path to config file")
def repl(config):
    response = ''
    sessions = {
        'sql': sql_prompt_session(),
        'es': es_prompt_session(),
        'enrich': enrich_prompt_session(),
    }

    while True:
        try:
            text = sessions[config.repl.mode].prompt(f"{config.repl.mode}> ")
        except KeyboardInterrupt:
            continue  # Control-C pressed. Try again.
        except EOFError:
            break  # Control-D pressed.

        if not text.strip():
            continue

        if text.lower().strip() == "copy":
            if response:
                pyperclip.copy(response)
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
                config.repl.search[var] = val
            print(config.repl.search)
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

        print(
            highlight(
                response,
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
