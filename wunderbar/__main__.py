#!/usr/bin/env python3

import argparse
import logging
import anki.importing as ai



def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.description = "A cli tool to import anki cards"

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="Increase logging verbosity"
    )

    return None


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
            logging.info("Max verbosity is 3")

    root_logger.setLevel(level)
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    configure_logger(args.verbose)
    return None


if __name__ == "__main__":
    main()
