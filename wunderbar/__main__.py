#!/usr/bin/env python3

import argparse
import logging
import os
import io
import sys
import enum
from anki.storage import Collection
from anki.models import NotetypeId
from typing import NamedTuple, TypedDict
import anki
import toml


if os.name == 'nt':
    print('This program does not work on windows\nExiting...')
    sys.exit(1)

ANKI_DECK_NAME = 'Test'
XDG_DATA_DIR = os.environ.get('XDG_DATA_HOME') or os.environ['HOME'] + '/.local/share'
ANKI_HOME = os.path.join(XDG_DATA_DIR, 'Anki2')
ANKI_REL_COLLECTION_PATH = 'User 1/collection.anki2'


# class AType(enum.Enum):
#     BASIC = 1680374475390
#     REVERSED = 1680374475391
#     REVERSED_OPT = 1680374475392
#     TYPE_ANSWER = 1680374475393
#     CLOZE = 1680374475394


# class TomlType(enum.Enum):
#     BASIC = 'basic'
#     REVERSED = 'reverse'
#     REVERSED_OPT = 'reverse_optional'
#     TYPE_ANSWER = 'typing'
#     CLOZE = 'cloze'


class Models(enum.Enum):
    basic = "Basic"
    reversed = "Basic (and reversed card)"
    reversed_optional = "Basic (optional reversed card)"
    type = "Basic (type in the answer)"
    cloze = "Cloze"


class Card(NamedTuple):
    front: str
    back: str
    type: AType


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.description = "to import anki cards"

    parser.add_argument(
        '-F', '--file',
        type=argparse.FileType('r', encoding='utf-8'),
        default='./examples/cloze.org',
        help='File to parse'
    )

    parser.add_argument(
        '-b', '--base',
        type=arg_is_dir,
        default=ANKI_HOME,
        help='File to parse'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="Increase logging verbosity"
    )

    return None


def arg_is_dir(path: str) -> str:
    if os.path.isdir(path):
        return path

    raise argparse.ArgumentTypeError(f'`{path}` is not a valid directory')


def configure_logger(verbose: int = 0) -> None:
    root_logger = logging.root

    match verbose:
        case 0:
            level = logging.WARNING
        case 1:
            level = logging.INFO
        case 2:
            level = logging.DEBUG
        case _:
            level = logging.DEBUG
            logging.warning("Max verbosity is 3")

    root_logger.setLevel(level)
    return None


def ensure_deck(col: Collection, deck_name: str) -> anki.decks.DeckDict | None:
    '''
    Select anki deck.
    Creates a new deck if one does not already exist.

    Returns None if creating a new deck fails
    '''
    deck = col.decks.by_name(deck_name)
    if deck is None:
        logging.info(f'Unable to get deck: {deck_name}\nAttempting to create a new deck')

        deck = col.decks.new_deck()
        deck.name = deck_name
        col.decks.add_deck(deck)

        deck = col.decks.by_name(deck_name)
        if deck is None:
            return None

        logging.info(f'Successfully created deck: {deck_name}')

    return deck


def org_extract_toml(fp: io.TextIOWrapper) -> str | None:
    if not fp.readable():
        logging.error(f'Unable to read file: {fp.name}\nExiting...')
        return None

    rv = ""
    in_toml = False
    for line in fp:
        if in_toml:
            if '#+end_src' in line:
                in_toml = False
                continue
            rv += line.strip() + '\n'

        if '#+begin_src toml' in line:
            in_toml = True

    return rv


def parse_toml(text: str) -> list[Card] | None:
    try:
        raw_dict = toml.loads(text)
    except toml.TomlDecodeError as err:
        logging.error(f'Unable to parse toml: {err}')
        return None

    rt_cards: list[Card] = []
    for key, value in raw_dict.items():
        match key:
            case TomlType.CLOZE.value:
                c_type = AType.CLOZE
            case TomlType.BASIC.value:
                c_type = AType.BASIC
            case TomlType.REVERSED.value:
                c_type = AType.REVERSED
            case TomlType.REVERSED_OPT.value:
                c_type = AType.REVERSED_OPT
            case _:
                logging.error(f'`{key}` is not a valid card type\nExiting...')
                return None

        for ikey, ivalue in value.items():
            try:
                rt_cards.append(Card(
                    type=c_type,
                    front=ivalue['front'],
                    back=ivalue['back']))
            except (KeyError, TypeError):
                logging.error(f'Invalid card: {ivalue}')
                return None
    return rt_cards


def create_note(col: Collection, card: Card) -> anki.notes.Note | None:
    # model = col.models.get(NotetypeId(card.type.value))
    model_manager = anki.models.ModelManager(col)
    model = col.models.by_name('basic')
    if model is None:
        logging.error('Failed to get card model')
        return None

    note = col.new_note(model)

    note.fields[0] = card.front
    note.fields[1] = card.back

    if card.type == AType.REVERSED_OPT:
        note.fields[2] = "yes"

    return note


def main() -> None:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    configure_logger(args.verbose)

    # https://www.juliensobczak.com/write/2020/12/26/anki-scripting-for-non-programmers.html
    logging.debug(args.base)
    logging.debug(os.path.join(args.base, ANKI_REL_COLLECTION_PATH))
    try:
        col = Collection(os.path.join(args.base, ANKI_REL_COLLECTION_PATH))
    except anki.errors.DBError:
        logging.error('An Anki instance is already running')
        sys.exit(1)

    # Select deck
    deck = ensure_deck(col, ANKI_DECK_NAME)
    if deck is None:
        logging.error(f'Unable to create a new deck called {ANKI_DECK_NAME}\nExiting...')
        sys.exit(1)

    logging.info('Extracting toml from org mode')
    rt = org_extract_toml(args.file)
    if rt is None:
        return None

    logging.info('Parsing cards')
    cards = parse_toml(rt)
    if cards is None:
        sys.exit(1)

    col.decks.select(deck['id'])

    # Create a new card
    logging.info('Creating cards')
    for card in cards:
        note = create_note(col, card)
        if note is None:
            return None
        col.add_note(note, deck['id'])

    # TODO: verify cards with user (on flag)
    logging.info('Saving cards')
    # col.save()

    return None


if __name__ == "__main__":
    main()
