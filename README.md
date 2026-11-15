# MicroVM Studio

A native Mac app for working in [AWS Lambda MicroVMs](https://aws.amazon.com/lambda/). It shows your MicroVMs and
opens terminals into them. It also keeps reusable **workspaces**, each with its repos, credentials and setup, so
every new MicroVM is ready to work in, Claude Code included.

**[Download the latest version](https://github.com/fabiodouek/microvm-studio/releases/latest)**

**[User guide](https://fabiodouek.github.io/microvm-studio/guide/)** with two narrated walkthroughs: a quick start, and a
workspace that keeps its files on Amazon EFS. The website is https://fabiodouek.github.io/microvm-studio/.

## Requirements

- macOS 15 or later, on Apple silicon or Intel.
- An AWS account that can run Lambda MicroVMs, with a profile in `~/.aws/config` (access keys or IAM Identity
  Center).

## What it does

- Lists your MicroVMs, opens terminals into them, and keeps sessions alive while you work.
- Launches MicroVMs from workspaces: your GitHub repos cloned, secrets from your Mac's Keychain, an AWS role, Claude Code signed in through Anthropic or Amazon Bedrock, and your own setup commands.
- Can keep `/workspace` on Amazon EFS, so your files outlive the MicroVM.
- Copies files in and out of a running MicroVM.
- Warns before MicroVMs reach their time limit, and shows what's running and what it costs.

## Costs

MicroVMs, EFS file systems and the network resources the app creates bill to **your** AWS account. The app shows
an estimate while MicroVMs run, and asks before creating anything that bills.

## Privacy

MicroVM Studio collects nothing and sends nothing to its author. See the [privacy policy](privacy.md).

## Licence

MicroVM Studio is free to use, and its source isn't public. Using it means accepting the
[licence agreement](eula.md), which says you're responsible for the charges in your AWS account and that the app
comes with no warranty. The App Store edition is covered by Apple's standard licence.

## Support

Report problems or ask questions in [Issues](https://github.com/fabiodouek/microvm-studio/issues).

---

MicroVM Studio is an independent project. It isn't affiliated with, endorsed by or sponsored by Amazon Web
Services or Anthropic. AWS, AWS Lambda and Amazon EFS are trademarks of Amazon.com, Inc. or its affiliates.

## About

Made by Fabio Douek. More from the author at [my2cents.ai](https://www.my2cents.ai/).

## This repository

It holds the app's releases, its update feeds and its website (GitHub Pages, from `main`). The user guide in
`guide/` is generated: `python3 tools/build_guide.py` builds it from `tools/guide/<version>/`, where `help.json` is
the app's own Help pages. The guide is versioned by the app's major version, starting at `v0`.
