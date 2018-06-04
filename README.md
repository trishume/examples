# Tristan's Talon User Folder

Based on the Talon examples repo, with extra scripts and modifications by Tristan.

## Main Modifications:

- RPC server to receive identifiers from an editor (in this case Sublime with [SublimeTalon](https://github.com/trishume/SublimeTalon)) and use them for a `dent` command that allows easy and accurate entry of identifiers from the current file and project.
- Python bindings to the [Linuxtrack](https://github.com/uglyDwarf/linuxtrack) API. For anyone finding this via Google, the bindings are in separate files that don't depend on Talon.
