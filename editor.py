from talon.voice import Context, Key, Rep, Str, press
from talon import ctrl
import talon

import re
from collections import defaultdict

from . import editor_rpc

ctx = Context('editor', bundle='com.sublimetext.3')
editor = None
symbol_mapping = {}

def insert(s):
    Str(s)(None)

def type_symbol(m):
    name = str(m._words[1])
    symbols = symbol_mapping.get(name)
    if not symbols: return
    # print(name, " - ", symbols)
    # TODO disambiguate multiple answers?
    insert(symbols[0])

keymap = {
    'test identifiers': 'lol it works',
    'dent {editor.symbols}': type_symbol,
}
ctx.keymap(keymap)

def camel_case_split(identifier):
    return re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)

def get_words(symbol):
    parts = []
    for part in symbol.split('_'):
        for match in camel_case_split(part):
            part = match.group(0)
            parts.append(part.lower())

    return ' '.join(parts)

def update_symbols(symbols):
    global symbol_mapping
    # print("UPDATING", symbols)
    mapping = defaultdict(lambda: [])
    for symbol in symbols:
        if len(symbol) <= 1:
            continue
        mapping[get_words(symbol)].append(symbol)

    # print("UPDATING", mapping)
    symbol_mapping = dict(mapping)
    ctx.set_list('symbols', mapping.keys())


def on_event(client, cmd, msg):
    global editor
    editor = editor_rpc.active()
    # print("Got message", cmd, msg)

    if cmd == "update_symbols":
        update_symbols(msg['symbols'])

    # if not editor:
    #     ctx.unload()
    #     return

    # ctx.load()

editor_rpc.register(on_event)
