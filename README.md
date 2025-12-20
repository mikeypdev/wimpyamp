# WimPyAmp

> Important: This is _not_ Winamp! If you want to use a reference implementation of Winamp, use [Webamp](https://webamp.org/). It's amazing and runs in the browser. It even support visualizers.

## Overview

WimPyAmp is a desktop music player designed for playing your local music collection, including hi-res lossless files. It’s compatible with Winamp skins for a really fun retro-pixel UI, and it looks suprisingly great on modern desktops. There are [thousands](https://skins.webamp.org/) of custom skins available that (should) work with WimPyAmp. You can even make your own!

![WimPyAmp screenshot - default skin: base-2.91.wsz](./WimPyAmp.png)

WimPyAmp assumes that you have your music collection and playlists reasonably organized on your file system or network share, so it doesn’t try to create some kind of library. It trusts you. And desktop search works pretty well these days, so searching your collection is straightforward.

## Using WimPyAmp

![WimPyAmp screenshot - skin: Expensive Hi-Fi 1.2.wsz](./WimPyAmp-3.png)

The app pretty much works like you might remember from Winamp (if you're old enough to remember). The “eject” button in the main window let’s you choose and load a single track. If you open the Playlist window, you’ll find options to load playlist files or add entire directories to the playlist (useful for albums). You can also select a track in your file system and choose “Open With...” WimPyAmp.

Click the “V” button in the main window clutterbar to toggle between visualizer types (spectrum analyzer, waveform, none).

WimPyAmp also has support for Album Art. Click "I" in the main window clutter bar, and an Album Art window will appear. It should show art from either the current track's metadata or an image in the same directory like `folder.jpg`. If there isn’t any art available, you’ll see a placeholder image (it was generated using Gemini Nano Banana - notice the watermark in the lower right corner of the image).

To load a new skin or reload the default skin, either choose the Settings menu, or click “O” in the main window clutter bar.

Releases are available for Mac on Intel and Apple Silicon. WimPyAmp also works on Linux and Windows (see Developer Notes below).

Note that Linux users will usually need to hold down the Super key (CMD/WIN) while using the mouse to move the app windows, as they have a frameless UI design. Snapping and docking is not supported on Linux for similar reasons.

## Features and Bugs

![WimPyAmp screenshot - skin: Mac OS X Winamp Skin.zip](./WimPyAmp-2.png)

Want other features? Found a bug? Open an Issue!

Q: Does WimPyAmp support streaming services like Spotify? Is that planned?
A: Nope

Q: Will it play CDs or SACDs?
A: You have a CD/DVD drive? Wow. I’ll keep it in mind.

## Developer Notes

### Python

This was developed on an Intel Mac using Python 3.13, as well an Apple Silicon Mac using Python 3.14. The core audio library is the amazing librosa, and UI is PySide6 (Python QT).

Intel Mac support is fading away, so pay attention to supported libraries if you are on an old Mac.

### Makefile

There's a Makefile in the project that should handle everything for Mac and Linux users. After cloning the repo, just run `make setup` to install dependencies and create the venv, then run `make run`.

Type `make help` to see other options, like linting or making an app bundle or binary.

Windows users can either install WSL to use the Makefile, or use Powershell scripts in the `winscripts/` directory and tools in Visual Studio Code. Don’t forget to install Python via the MS Store.

### AI Coding Agents

This project was entirely coded by AI agents, mostly Gemini and Qwen, using spec-driven development (*not* “vibe-coding”). It's really just a framework for some excellent Python libraries, including librosa, mutagen, Pillow, and others, connected to a PySide6 UI that renders bitmaps from Winamp skin archives.

The specs are in the `docs/` directory, along with some original Winamp skinning guidelines. If you add a feature, you must create a spec first. Let the AI help you, and force the AI to review it before implementation.

There is an `AGENT-lite.md` file that attempts to provide low-capability agents with instructions to avoid doing dumb things. It kinda works, sometimes.

### Thanks

Special thanks to the Webamp project, which archived key documents for the Winamp skin specification, as well as provided a reference implementation for the mini-visualizer.

And thanks to the thousands of people who created really cool Winamp skins 25 years ago.

## License

WimPyApp is open-source, licensed under the MIT license. I've included licenses for the various libraries in the `licenses/` directory.

*WimPyAmp is not associated with Winamp, Webamp, Nullsoft, or Justin Frankel in any way. No source code from Winamp was used or referenced in this project. All rights belong to their respective owners.*

Copyright (c) 2025, Mike Perry
