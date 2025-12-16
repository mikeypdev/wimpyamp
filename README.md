# WimPyAmp

> Important: This is _not_ Winamp! If you want to use a reference implementation of Winamp, use [Webamp](https://webamp.org/). It's amazing and runs in the browser. It even support visualizers.

## Overview

WimPyAmp is a Python desktop music player app designed for playing local music files. It is compatible with Winamp skins for UI customization.

![WimPyAmp Screenshot](./WimPyAmp.png)

## Background

### Goals

1. Build a decent music player app solely for my local file music collection, which includes mp3s, lossless CD rips, and purchased hi-res audio tracks (and add nothing extra, like a music library, streaming support, integration with Apple Music, etc.)
2. Learn best-practices when using terminal-based AI coding agents, including gemini-cli, crush, qwen-code, and others

### UI Skinning

While working on the design for the music player, I remembered how much I liked using Winamp way back in the mp3 days, and I decided to take inspiration from its UI design. I then remembered that 1000's of skins were created for Winamp by countless users and fans, and saw that the Webamp project has a [massive archive](https://skins.webamp.org/) of them. So I decided to make the music player UI (hopefully) pixel-perfect compatible with most Winamp skins. Note again that this app is not Winamp, so feature parity and full skin functionality should not be expected.

### AI Coding Agents

This project was entirely coded by AI agents, mostly Gemini and Qwen. If you read the code, you'll see that it's really just a light framework for some excellent Python libraries, including librosa, mutagen, Pillow, and others, and connects them to a Python QT UI system that renders bitmaps from Winamp skin archives.

This project could not have been made without those awesome libraries or the Webamp project, which archived key documents for the Winamp skin specification, as well as provided a reference implementation for the mini-visualizer.

There is an `AGENT-lite.md` file that attempts to provide low-capability agents with instructions to avoid doing dumb things. It kinda works, sometimes.

## Using WimPyAmp

The app pretty much works like you might remember from Winamp (if you're old enough to remember). One difference is support for Album Art. Click "I" in the main window clutter bar, and an Album Art window will appear. It should show art from either the current track's metadata or an image in the same directory like `folder.jpg`. I generated a placeholder image using Gemini Nano Banana. You can see the Gemini watermark in the lower right corner of the image.

I built this on a Mac, and can confirm that it works with Intel macOS 12, and Apple Silicon macOS 26. It should also work on Linux and Windows, but I haven't tested it.

## Developing

There's a Makefile in the project that should handle everything for you. After cloning the repo, just run `make setup` to install dependencies and create the venv, then run `make run`.

Type `make help` to see other options, like linting or making an app bundle or binary.

I recommend sticking with AI coding agents for this project. Feel free to regenerate the `AGENTS.md` file to accommodate whatever agent you use.

## License

WimPyApp is open-source, licensed under the MIT license. I've included licenses for the various libraries in the `licenses/` directory.

*WimPyAmp is not associated with Winamp, Webamp, Nullsoft, or Justin Frankel in any way. No source code from Winamp was used or referenced in this project. All rights belong to their respective owners.*

Copyright (c) 2025, Mike Perry
