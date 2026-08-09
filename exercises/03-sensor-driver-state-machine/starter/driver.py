#!/usr/bin/env python3
"""Runnable starter.  Replace TODO results with a stateful implementation."""

from __future__ import annotations


class SensorDriver:
    def __init__(self, bus, *, use_dma=False):
        self.bus = bus
        self.use_dma = use_dma
        self.state = "UNBOUND"
        self.generation = 0

    def initialize(self, config, *, now=0):
        # TODO: reset, wait for readiness, probe identity, then configure.
        return {"status": "TODO"}

    def start_sample(self, *, now, deadline):
        # TODO: allocate a generation and establish one terminal-result owner.
        self.generation += 1
        return self.generation

    def poll(self, *, now):
        return "TODO"

    def on_data_ready(self, generation, *, now):
        # TODO: W1C acknowledgement, deadline, stale generation and optional DMA.
        return "TODO"

    def on_dma_complete(self, generation, *, now):
        return "TODO"

    def cancel(self, generation, *, now):
        return "TODO"

    def suspend(self, *, now):
        self.state = "SUSPENDED"
        return self.state

    def resume(self):
        self.state = "UNBOUND"
        return "REINITIALIZE"

    def result(self, generation):
        return None

    def dma_buffer(self, generation):
        return None

    def snapshot(self):
        return {"state": self.state, "generation": self.generation}
