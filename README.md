# The mews

[![CI](https://github.com/xyzzing/mews/actions/workflows/ci.yml/badge.svg)](https://github.com/xyzzing/mews/actions/workflows/ci.yml)

The falconry house where the birds live: the systems-integration rig and
front door of the flight-test program.

To install the product, start at
[minder](https://github.com/xyzzing/minder#readme) - its README carries
the try-it and install paths. This repo is orientation, not installation.

The family: [minder](https://github.com/xyzzing/minder) (the keeper/tower),
[cupola](https://github.com/xyzzing/cupola) (the furnace + watch-dome),
windtunnel (the tunnel, private),
[windroos](https://github.com/xyzzing/windroos) (the rose - repo-agent v0.4),
[valkenier](https://github.com/xyzzing/valkenier) (the falconer, private).

What lives here: contract-drift tripwires (every cross-repo schema pair
exercised producer-against-consumer), the full-loop shakedown (stub-mode
end-to-end), security event tripwires, nightly certification reports, and
the program's front door (map, naming law, methodology links).

Requirements and phases: [docs/PRD.md](docs/PRD.md). Status: pre-M0 - the
founding test is the sweep-run schema drift tripwire.
