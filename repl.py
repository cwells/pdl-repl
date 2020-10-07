#!/bin/env python

import json
import os
import re

import click
import pyperclip
import yaml
from box import Box
from pygments.lexers import JsonLexer
from pygments import highlight, lexers, formatters

import modes

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

#
# commands
#
def command_set(text):
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


def command_mode(text):
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
# repl
#
@click.command()
@click.option('--config', '-c', callback=read_config, default=CONFIG_FILE, help="path to config file")
def repl(config):
    result = ''
    sessions = {
        'sql': modes.sql.prompt_session(config.repl.search, CONFIG_DIR),
        'es': modes.es.prompt_session(config.repl.search, CONFIG_DIR),
        'enrich': modes.enrich.prompt_session(CONFIG_DIR),
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
                mode = command_mode(text)
            except ParseError as e:
                print("Invalid mode command")
            except ValueError as e:
                print(f"Invalid mode '{e}'. Valid values are [sql, es, enrich]")
            else:
                config.repl.mode = mode
            continue

        if text.lower().startswith("set "):
            try:
                var, val = command_set(text)
            except ParseError as e:
                print("Invalid set command")
            else:
                print(var, val)
                config.repl.search[var] = val
            continue

        response = getattr(modes, config.repl.mode).query(
            api_key = config.api_key,
            query = text,
            size = config.repl.search.size,
            offset = config.repl.search.offset
        )

        result = json.dumps(
            response.json(),
            indent = 2 if config.repl.search.pretty else None
        )

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
