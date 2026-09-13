"""Browser-side stand-in for the `agentics` package.

The static build only needs the slice of the Agentics API that
`EnergyDataLoader` touches: loading records out of a CSV, holding them as
states, and the async reduce used for filtering. Everything else is unused by
`app.py`, so it is deliberately not implemented.
"""

from __future__ import annotations

import csv


class AG:
    """Minimal container of typed states."""

    def __init__(self, atype=None, states=None, **kwargs):
        self.atype = atype
        self.states = list(states or [])

    @classmethod
    def from_csv(cls, path, atype=None, **kwargs):
        with open(path, newline="", encoding="utf-8") as handle:
            rows = [
                atype(
                    **{
                        key: (value if value != "" else None)
                        for key, value in row.items()
                    }
                )
                for row in csv.DictReader(handle)
            ]
        return cls(atype=atype, states=rows)

    def __iter__(self):
        return iter(self.states)

    def __len__(self):
        return len(self.states)

    def __getitem__(self, index):
        return self.states[index]

    async def areduce(self, fn):
        return await fn(self.states)
