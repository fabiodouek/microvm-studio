# MicroVM Studio privacy policy

*Last updated: 8 November 2026*

MicroVM Studio is a Mac app for working in AWS Lambda MicroVMs. This policy covers the app in both its editions:
the direct download and the Mac App Store edition.

## What we collect

**Nothing.** The app has no analytics, no crash reporting, no accounts and no servers of its own. Nothing you do
in it is sent to its author.

## Where your data goes

The app talks only to the services you connect it to, and only to do what you ask:

- **Amazon Web Services:** your MicroVMs, IAM roles, EFS file systems, the starter image, and anything else you
  create through the app. These calls use your own AWS credentials, from your `~/.aws` configuration.
- **GitHub:** only when you add GitHub access to a workspace. The app uses it to sign in, list your repositories,
  and give your MicroVMs a token for the repos you chose.
- **Anthropic:** only when you sign Claude Code in, through Claude Code's own sign-in.
- **Software updates** (direct download only): the app checks the update feed on GitHub Pages. That request
  carries the app's version and your macOS version, as every update check does. The Mac App Store edition is
  updated by the App Store.

What these services do with your data is covered by their own privacy policies.

## What stays on your Mac

- **Secrets and tokens** you save (GitHub tokens, Claude Code tokens and API keys) are kept in your Mac's Keychain.
  They're sent only to the MicroVMs of workspaces that use them.
- **Workspaces and settings** are kept in the app's own folder on your Mac.

## Your MicroVMs

Everything inside a MicroVM runs in your AWS account, under your control. That includes files, repos, credentials
copied in, and anything Claude Code does.

## Children

The app is a developer tool and isn't directed at children.

## Changes

If this policy changes, the new version will be published here with a new date.

## Contact

Questions: [open an issue](https://github.com/fabiodouek/microvm-studio/issues).
