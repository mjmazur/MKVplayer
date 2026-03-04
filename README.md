A simple Python-based MKV and FF video player built with OpenCV. It provides basic playback functionality with essential controls meant for frame-by-frame analysis.

This project includes two separate scripts:
- `mkv_player.py`: Plays standard MKV video files.
- `ff_player.py`: Plays astronomy FITS video formats compressed by the RMS framework.

## Features

- **Automated Loading:** Automatically finds and loads the first `.mkv` file in the current or parent directory if no explicit file path is provided.
- **Playback Control:** Predicts and plays the video at its native framerate.
- **Frame Navigation:** Accurately seek backward and forward one frame at a time.
- **On-Screen Display:** Displays the current frame count and pause status dynamically on the video.
- **Scaling Display:** The player defaults to 50% scale to fit large videos onto typical monitors, but can be scaled to its native resolution using `--full-size`.

## Installation

Ensure you have Python installed.

```bash
# Optional: Setup a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the player script from the directory containing your MKV or FF video:

```bash
# Play the default MKV video in the current/parent directory
python mkv_player.py

# Play a specific MKV video file
python mkv_player.py path/to/your_video.mkv

# Play the default FF video
python ff_player.py

# Play at native 100% resolution (default is 50%)
python mkv_player.py --full-size
python ff_player.py --full-size
```

### Controls

- **Spacebar**: Toggle Play / Pause
- **Right Arrow**: Step forward one frame (when paused)
- **Left Arrow**: Step backward one frame (when paused)
- **R or 0**: Restart video from the beginning
- **Q or Esc**: Quit the player
