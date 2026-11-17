#!/usr/bin/env python3
"""Executable wrapper for `python -m ozon_client` / the `ozon` console script."""
from .cli import app


def main():
    app()


if __name__ == "__main__":
    main()
