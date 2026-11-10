# Lifecycle hook listener

`v1/hooks.py` is the small listener that images built by MicroVM Studio run inside a MicroVM. It answers the
platform's lifecycle hooks on 127.0.0.1, and mounts a workspace's `/workspace` storage while the MicroVM starts.

An image build downloads it from
`https://fabiodouek.github.io/microvm-studio/hooks/v1/hooks.py` and checks its SHA-256, which the app pins.

A published version is never edited. A change is published as a new directory (`v2`, `v3`, …), and the app that
uses it pins the new checksum.
