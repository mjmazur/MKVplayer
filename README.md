# MKV Video Player

A simple Python-based MKV video player built with OpenCV. It provides basic playback functionality with essential controls meant for frame-by-frame analysis.

## Features

- **Automated Loading:** Automatically finds and loads the first `.mkv` file in the current or parent directory if no explicit file path is provided.
- **Playback Control:** Predicts and plays the video at its native framerate.
- **Frame Navigation:** Accurately seek backward and forward one frame at a time.
- **On-Screen Display:** Displays the current frame count and pause status dynamically on the video.
- **Scaling Display:** Optionally scale the playback window to 50% of the native video resolution.

## Installation

Ensure you have Python installed. The only external dependency is `opencv-python`.

```bash
# Optional: Setup a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the player script from the directory containing your MKV video:

```bash
# Play the default MKV video in the current/parent directory
python mkv_player.py

# Play a specific video file
python mkv_player.py path/to/your_video.mkv

# Play at 50% scale
python mkv_player.py --half-size
```

### Controls

- **Spacebar**: Toggle Play / Pause
- **Right Arrow**: Step forward one frame (when paused)
- **Left Arrow**: Step backward one frame (when paused)
- **R or 0**: Restart video from the beginning
- **Q or Esc**: Quit the player
