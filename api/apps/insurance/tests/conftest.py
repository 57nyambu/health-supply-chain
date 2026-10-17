"""Markers of the payer suites (INSURANCE.md §10): ``pytest -m payers`` runs the contract
suite against every adapter fake; ``pytest -m sha`` the SHA paths."""


def pytest_configure(config):
    config.addinivalue_line("markers", "payers: payer gateway contract suite (every adapter fake)")
    config.addinivalue_line("markers", "sha: SHA through the HIE")
