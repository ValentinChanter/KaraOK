<p align="center">
  <a href="https://github.com/ValentinChanter/KaraOK">
    <img src="https://i.imgur.com/put6YuI.png" height="96">
    <h3 align="center">KaraOK</h3>
  </a>
</p>

<p align="center">Make your own karaoke for any song</p>

<br/>

## Introduction

This app allows you to transform any song, even those not available in standard karaoke libraries, into a karaoke-style video featuring instrumental music and synchronized, real-time lyrics.

## How It Works

The website is made with [Next.js](https://nextjs.org/) for the frontend, [Flask](https://flask.palletsprojects.com/en/3.0.x/) for the backend, and [Tailwind CSS](https://tailwindcss.com/) for styling.

Audio separation uses deep neural networks with [audio-separator](https://pypi.org/project/audio-separator/) and vocals are converted to real-time lyrics with [whisper-timestamped](https://github.com/linto-ai/whisper-timestamped).

## Requirements

This app was tested with Node v20.14.0 and Python 3.10.12, with and without Nvidia GPU.

## Installation

1. Clone this repo and access it

	```bash
	git clone https://github.com/ValentinChanter/KaraOK
	cd KaraOK
	```
2. If you don't have it already, install FFmpeg on your OS:

- [Windows](https://www.gyan.dev/ffmpeg/builds/)
- Ubuntu/Debian

	```bash
	apt-get update
	apt-get install -y ffmpeg
	```
- MacOS

	```bash
	brew update
	brew install ffmpeg
	```
3. Install node dependencies

	```bash
	npm install
	# or
	yarn
	# or
	pnpm install
	```
4. (Optional) Create and switch to your virtual environment if needed

	```bash
	python -m venv /path/to/new/virtual/environment
	source /path/to/new/virtual/environment/bin/activate
	# or
	conda create --name <my-env>
	conda activate <my-env>
	```
5. Install python dependencies

	```bash
	pip install -r requirements.txt
	```

## Usage

1. Run the development server. If you created a venv don't forget to activate it

	```bash
	npm run dev
	# or
	yarn dev
	# or
	pnpm dev
	```

2. Open [http://localhost:3000](http://localhost:3000) with your browser to see the app. The Flask server will be running on [http://127.0.0.1:5328](http://127.0.0.1:5328).

## Troubleshooting

### Audio separation/lyrics generation takes too much time

Unfortunately, if the computer hosting the api part of the app doesn't have hardware acceleration, the audio separation and vocals to lyrics part will take way more time.

Besides, the first time a model is used both for audio separation and lyrics generation, it will take a long time because it will need to download the model(s) before processing.

### Hardware acceleration is available but unused

Please check out the Installation section of [audio-separator](https://pypi.org/project/audio-separator/) to properly configure python dependencies. If you're using `conda`, make sure you're using the command for the virtual environment instead of a command or alias executing for your base.

### `sh: 1: python: not found` error on Ubuntu

I solved this by installing `python-is-python3`.