#!/usr/bin/env python
"""Django's command-line utility. DJANGO_ENV selects the settings (default: dev)."""

import sys

from config.env import configure_settings_module


def main():
    configure_settings_module(default="dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
