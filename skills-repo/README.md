Skills repo (example)
======================

This repository is a small, shareable collection of "skills" (MD documents) that agents or humans can reference from any workspace.

Structure
---------
- `skills/` — contains skill documents organized by topic.

Usage
-----
1. Clone this repo somewhere centralized (for example, into `%USERPROFILE%\\.skills`).
2. From any workspace, run the provided installer script `scripts/install_skills.ps1` to either copy or symlink the `skills/` directory into the current workspace's `.agents/skills` path.

Publishing
----------
To publish and share, push this folder to a remote git repository and pass the remote URL to the installer script.
