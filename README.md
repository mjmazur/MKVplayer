A simple Python-based MKV and FF video player built with OpenCV. It provides basic playback functionality with essential controls meant for frame-by-frame analysis.

This project includes three separate scripts:
- `mkv_player.py`: Plays standard MKV video files.
- `ff_player.py`: Plays astronomy FITS video formats compressed by the RMS framework.
- `sync_player.py`: Synchronizes the playback between an MKV video and its corresponding FF frames.

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

### 1. MKV Player (`mkv_player.py`)
Plays standard `.mkv` video files. If no file is specified, it will automatically search the current and parent directory for an MKV file to play.

**Examples:**
```bash
# Play the default MKV video in the current/parent directory
python mkv_player.py

# Play a specific MKV video file
python mkv_player.py path/to/your_video.mkv

# Play at native 100% resolution instead of the default 50% scale
python mkv_player.py --full-size

# Override the video framerate to 30.0 FPS
python mkv_player.py --fps 30.0
```

### 2. FF Player (`ff_player.py`)
Plays astronomy `.fits` or `.bin` video formats compressed by the RMS framework. It applies a 2D Gaussian filter (FWHM=5 pixels) to smooth the maximum array during reconstruction. If no file is specified, it automatically searches for one.

**Examples:**
```bash
# Play the default FF fits/bin file
python ff_player.py

# Play a specific FF fits file
python ff_player.py path/to/FF_file.fits

# Play at native 100% resolution with a custom FPS
python ff_player.py --full-size --fps 25.0
```

### 3. Synchronized Player (`sync_player.py`)
Opens two synchronized windows: one playing an MKV file and the other interpolating the overlapping FF data. 
**Note:** A path to the MKV video is *required*.

**Examples:**
```bash
# Play an MKV file and automatically search directories 4-levels up for corresponding FF frames
python sync_player.py path_to_video.mkv

# Play an MKV file and explicitly point the script to search a specific folder for FF frames
python sync_player.py path_to_video.mkv --ff-dir /path/to/ff/folder

# Play both windows at 100% native resolution
python sync_player.py path_to_video.mkv --full-size
```

### Controls

- **Hover Window**: Move your mouse over either the MKV or FF video player to give it keyboard focus
- **Spacebar**: Toggle Play / Pause on the **focused** window
- **Right Arrow or > / .**: Step forward one frame on the **focused** window (when paused)
- **Left Arrow or < / ,**: Step backward one frame on the **focused** window (when paused)
- **s**: Toggle Synchronization Mode (`sync_player.py` only). Activating this tightly binds the playback controls of both windows. Pausing, unpausing, and frame-stepping will affect both windows simultaneously, maintaining their relative time offset.
- **R or 0**: Restart video from the beginning
- **Q or Esc**: Quit the player
