#!/usr/bin/env python3

from anki.storage import Collection
from collections import deque
from typing import NamedTuple, Iterable
import anki
import argparse
import enum
import io
import logging
import os
import sys
import toml  # Note: change to tomllib in python 3.11


if os.name == 'nt':
    print('''This program does not work on windows\n
          I\'ve heard linux is the best os, you could use that\n
          Exiting...''')
    sys.exit(1)

ANKI_DECK_NAME = 'Wunderbar'
XDG_DATA_DIR = os.environ.get('XDG_DATA_HOME') or os.environ['HOME'] + '/.local/share'
ANKI_HOME = os.path.join(XDG_DATA_DIR, 'Anki2')
ANKI_REL_COLLECTION_PATH = 'User 1/collection.anki2'


class Model(enum.Enum):
    basic = "Basic"
    reversed = "Basic (and reversed card)"
    reversed_optional = "Basic (optional reversed card)"
    type = "Basic (type in the answer)"
    cloze = "Cloze"


class Card(NamedTuple):
    front: str
    back: str
    model: Model
    uid: str
    tags: deque[str]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add argparse arguments to parser."""
    parser.description = "org containing toml anki cards"

    parser.add_argument(
        '-F', '--file',
        type=argparse.FileType('r', encoding='utf-8'),
        required=True,
        help='File to parse'
    )

    parser.add_argument(
        '-b', '--base',
        type=arg_is_dir,
        default=ANKI_HOME,
        help='File to parse'
    )

    parser.add_argument(
        '-d', '--deck',
        type=str,
        default=ANKI_DECK_NAME,
        help='Name of deck you want to modify'
    )

    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Name of deck you want to modify'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="Increase logging verbosity"
    )

    return None


def arg_is_dir(path: str) -> str:
    """Function used to verify argparse directory type."""
    if os.path.isdir(path):
        return path

    raise argparse.ArgumentTypeError(f'`{path}` is not a valid directory')


def configure_logger(verbose: int = 0) -> None:
    """Set logging verbosity."""
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
    """
    Select Anki deck.

    Creates a new deck if one does not already exist.

    Parameters
    ----------
    col: anki.storage.Collection
    deck_name: str
        The Anki deck you want to open.

    Returns
    -------
    Optional[None]
        Failed to create new deck.
    Optional[anki.decks.DeckDict]
        Anki deck with `deck_name`.
    """
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
    """
    extract toml from orgmode file.

    This function looks for a pattern begning with ``#+begin_src toml``,
    that ends in ``#+end_src``.

    Parameters
    ----------
    file: io.TextIOWrapper
        Readable org file with Toml.

    Returns
    -------
    Option[str]
        Toml parsed form file. Is empty if file does not contain toml.
    Option[None]
        Toml parsed form file. Is empty if file does not contain toml.
    """
    if not fp.readable():
        logging.error(f'Unable to read file: {fp.name}\nExiting...')
        io.FileIO.readable
        return None

    rv = ""
    in_toml = False
    for line in fp:
        if in_toml:
            if '#+end_src' == line.strip():
                in_toml = False
                continue
            rv += line.strip() + '\n'

        if '#+begin_src toml' == line.strip():
            in_toml = True

    return rv


def read_uids(fp: io.TextIOWrapper) -> dict[str, bool] | None:
    """
    Read unique ids from file.

    The file should only contain 1 column.

    Parameters
    ----------
    file: io.TextIOWrapper
        Readable file.

    Returns
    -------
    Option[dict[str, bool]]
        A directory where the keys are the unique ids, and values are booleans.
    Option[None]
        File is not readable.
    """
    if not fp.readable():
        logging.error(f'Unable to read file: {fp.name}')
        return None

    uids = dict()
    for line in fp:
        uids[line.strip()] = True

    return uids


def write_uids(fp: io.TextIOWrapper, cards: Iterable[Card]) -> bool:
    """
    Write card uids to file.

    Parameters
    ----------
    fp : io.TextIOWrapper
        File in append mode.
    cards : Iterable[Card]
        Cards that are written to file

    Returns
    -------
    bool
        False if file is unwritable, else True.
    """
    if not fp.writable():
        logging.error(f'Unable to write to file: {fp.name}')
        return False

    if fp.mode != 'a':
        logging.error(f'Opened file with wrong mode `{fp.mode}. Should be `a`')
        return False

    for card in cards:
        fp.write(card.uid + '\n')

    return True


def parse_toml(text: str) -> deque[Card] | None:
    try:
        raw_dict = toml.loads(text)
    except toml.TomlDecodeError as err:
        logging.error(f'Unable to parse toml: {err}')
        return None

    rt_cards: deque[Card] = deque()
    for key, value in raw_dict.items():
        try:
            c_type = Model[key]
        except KeyError:
            logging.error(f'`{key}` is not a valid card type')
            return None

        for ikey, ivalue in value.items():
            try:
                rt_cards.append(Card(
                    model=c_type,
                    uid=ikey,
                    tags=ivalue.get('tags') or deque(),
                    front=ivalue['front'],
                    back=ivalue['back']))
            except (KeyError, TypeError):
                logging.error(f'Invalid card: {ivalue}')
                return None
    return rt_cards


def filter_out_nonuid(cards: Iterable[Card], uids: dict[str, bool]) -> deque[Card]:
    rt: deque[Card] = deque()
    for card in cards:
        if card.uid in uids:
            logging.info(f'Discarding `{card.uid}`')
            continue
        rt.append(card)

    return rt


def create_note(col: Collection, card: Card) -> anki.notes.Note | None:
    # model = col.models.get(NotetypeId(card.type.value))
    # model_manager = anki.models.ModelManager(col)
    model = col.models.by_name(card.model.value)
    if model is None:
        logging.error(f'Failed to get card model `{card.model.value}`')
        return None

    note = col.new_note(model)

    note.fields[0] = card.front
    note.fields[1] = card.back
    note.tags = list(card.tags)

    if card.model == Model.reversed_optional:
        note.fields[2] = "yes"

    return note


def display_adjustments(col: Collection,
                        args: argparse.Namespace,
                        notes: Iterable[anki.notes.Note]
                        ) -> None:
    print('----- New cards -----')
    for note in notes:
        n_type = note.note_type()
        if n_type is not None:
            print(f'Type : {n_type.get("name")}')
        print(f'Front: {note.fields[0]}')
        print(f'Back : {note.fields[1]}')
        print(f'Tags : {note.tags}')
        print('')

    print(f'Base: {args.base}')
    print(f'Rel collection: {ANKI_REL_COLLECTION_PATH}')
    print('')
    return None


def ensure_file(path: str) -> None:
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    if not os.path.isfile(path):
        os.mknod(path)

    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    configure_logger(args.verbose)

    # https://www.juliensobczak.com/write/2020/12/26/anki-scripting-for-non-programmers.html
    logging.debug(f'Anki base dir: {args.base}')
    logging.debug(f'Anki collection file: {os.path.join(args.base, ANKI_REL_COLLECTION_PATH)}')
    logging.debug(f'File: {args.file.name}')

    try:
        col = Collection(os.path.join(args.base, ANKI_REL_COLLECTION_PATH))
    except anki.errors.DBError:
        logging.error('An Anki instance is already running')
        sys.exit(1)

    # Select deck
    deck = ensure_deck(col, args.deck)
    if deck is None:
        logging.error(f'Unable to create a new deck called {args.deck}\nExiting...')
        sys.exit(1)

    logging.info('Extracting toml from org mode')
    rt = org_extract_toml(args.file)
    if rt is None:
        sys.exit(1)

    logging.info('Parsing cards')
    cards = parse_toml(rt)

    if cards is None:
        sys.exit(1)
    if len(cards) == 0:
        print(f'`{args.file.name}` does not contain any cards')
        return None

    col.decks.select(deck['id'])

    # get uids
    uid_path = os.path.join(XDG_DATA_DIR, 'wunderbar/uids.log')
    logging.info(f'Reading uids `{uid_path}`')
    ensure_file(uid_path)
    with open(uid_path, 'r', encoding='utf-8') as fp:
        uid_dict = read_uids(fp)
        if uid_dict is None:
            sys.exit(1)

    cards = filter_out_nonuid(cards, uid_dict)
    if len(cards) == 0:
        print(f'`{args.file.name}` does not contain any unique cards')
        return None

    # Create a new card
    logging.info('Creating cards')
    notes: deque[anki.notes.Note] = deque(maxlen=len(cards))
    for i, card in enumerate(cards):
        note = create_note(col, card)
        if note is None:
            sys.exit(1)
        col.add_note(note, deck['id'])
        notes.append(note)

    if args.force is False:
        display_adjustments(col, args, notes)
        if input('Are you sure you want to write changes? [y/n] ') != 'y':
            print('Exiting...')
            sys.exit(0)

    logging.info(f'Writing uids to `{uid_path}`')
    ensure_file(uid_path)
    with open(uid_path, 'a', encoding='utf-8') as fp:
        if not write_uids(fp, cards):
            sys.exit(1)

    logging.info('Saving cards')
    col.save()

    return None


if __name__ == "__main__":
    main()
