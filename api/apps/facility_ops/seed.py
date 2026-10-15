"""Seed step: legacy facility demo data (warehouses, stock, daily stats, alerts)."""

from django.core.management import call_command


def run(command):
    call_command("seed_facility_demo_data", stdout=command.stdout)
