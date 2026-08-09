from __future__ import annotations


def request_environment(state, request):
    while True:
        pass


reconcile = request_environment
observe_drift = request_environment
request_migration = request_environment
retire_service = request_environment


def snapshot(state):
    return dict(state)
