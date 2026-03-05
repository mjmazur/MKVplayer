import cv2
import sys
import os
import glob
import argparse
import numpy as np
import datetime
import scipy.ndimage as ndimage

# Add RMS to the path so we can import the FF format modules
sys.path.append(os.path.expanduser('~/source/RMS'))
from RMS.Formats.FFfile import read as readFF
from RMS.Formats.FFfile import reconstruct
from RMS.Formats.FFfile import filenameToDatetime

def find_default_ff():
    # Try current directory first
    ff_files = glob.glob('FF*.fits') + glob.glob('FF*.bin')
    if ff_files:
        return ff_files[0]
        
    # Try parent directory
    parent_ff_files = glob.glob(os.path.join('..', 'FF*.fits')) + glob.glob(os.path.join('..', 'FF*.bin'))
    if parent_ff_files:
        return parent_ff_files[0]
        
    return None

def main():
    parser = argparse.ArgumentParser(description="FF Video Player")
    parser.add_argument("video_path", nargs="?", help="Path to the FF fits/bin file")
    parser.add_argument("--full-size", action="store_true", help="Display the video at its native 100% resolution (default is 50% scale)")
    parser.add_argument("--fps", type=float, default=25.0, help="Frame rate of the video (default: 25.0)")
    args = parser.parse_args()

    video_path = args.video_path
    if not video_path:
        video_path = find_default_ff()
        
    if not video_path or not os.path.exists(video_path):
        print("Error: Could not find an FF file.")
        print(f"Usage: python ff_player.py [path_to_video.fits] [--full-size]")
        sys.exit(1)
        
    print(f"Reading FF file: {video_path}")
    
    try:
        start_time = filenameToDatetime(os.path.basename(video_path))
    except Exception as e:
        print(f"Warning: Could not parse time from filename: {e}")
        start_time = datetime.datetime.now()
    
    # Read the file
    try:
        ff = readFF(os.path.dirname(os.path.abspath(video_path)), os.path.basename(video_path))
    except Exception as e:
        print(f"Error reading FF file: {e}")
        sys.exit(1)
        
    if ff is None:
        print(f"Error: Could not parse FF file {video_path}")
        sys.exit(1)
        
    print(f"Reconstructing frames...")
    # Reconstruct the frames from the maxpixel and maxframe
    nframes = ff.nframes if ff.nframes > 0 else 256
    frames = np.zeros((nframes, ff.nrows, ff.ncols), np.uint8)
    
    if ff.array is not None:
        ff.maxpixel = ff.array[0]
        ff.maxframe = ff.array[1]
        ff.avepixel = ff.array[2]
        
    # Convolve maxpixel with a 2D Gaussian where FWHM = 5 pixels
    print(f"Applying Gaussian filter to maximum array (FWHM=5)...")
    sigma = 5.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    smoothed_maxpixel = ndimage.gaussian_filter(ff.maxpixel.astype(float), sigma=sigma)
    ff.maxpixel = np.clip(smoothed_maxpixel, 0, 255).astype(np.uint8)
        
    for i in range(nframes):
        # Start with the average pixel frame as the background
        frames[i] = ff.avepixel.copy()
        
        # Overlay the pixels where maxframe matches the current frame index
        indices = np.where(ff.maxframe == i)
        frames[i][indices] = ff.maxpixel[indices]
        
    print(f"Playing video: {video_path}")
    if not args.full_size:
        print("Displaying at half size (default). Use --full-size for native resolution.")
    print("Controls:")
    print("  Spacebar : Pause/Resume")
    print("  Left/Right or < / > : Step backward/forward 1 frame (when paused)")
    print("  R or 0 : Restart video from beginning")
    print("  Q or Esc : Quit")

    fps = args.fps
    delay = int(1000 / fps) # milliseconds per frame
    
    total_frames = frames.shape[0] # nframes is the first dimension
    print(f"Total frames: {total_frames}, FPS (playback): {fps:.2f}")

    paused = False
    current_frame_idx = 0
    window_name = "FF Player"
    
    while True:
        # Get frame from numpy array (reconstructed from memory)
        frame = frames[current_frame_idx].copy()
        
        # OpenCv expects BGR for colored text, so we convert grayscale to BGR
        display_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        if not args.full_size:
            display_frame = cv2.resize(display_frame, (0, 0), fx=0.5, fy=0.5)
            
        # Add frame number text in lower left
        text = f"Frame: {current_frame_idx}"
        cv2.putText(display_frame, text, (10, display_frame.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        # Add time elapsed in lower right
        elapsed_seconds = current_frame_idx / fps
        mins = int(elapsed_seconds // 60)
        secs = int(elapsed_seconds % 60)
        micros = int((elapsed_seconds - int(elapsed_seconds)) * 1_000_000)
        time_text = f"{mins:02d}:{secs:02d}.{micros:06d}"
        
        text_size, _ = cv2.getTextSize(time_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        x_pos = display_frame.shape[1] - text_size[0] - 10
        cv2.putText(display_frame, time_text, (x_pos, display_frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        # Add absolute time in upper right
        current_time = start_time + datetime.timedelta(seconds=elapsed_seconds)
        abs_time_text = current_time.strftime("%Y%m%d %H:%M:%S.%f")
        text_size, _ = cv2.getTextSize(abs_time_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        x_pos = display_frame.shape[1] - text_size[0] - 10
        cv2.putText(display_frame, abs_time_text, (x_pos, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        if paused:
            cv2.putText(display_frame, "PAUSED", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        cv2.imshow(window_name, display_frame)

        # Wait for key press. Delay to prevent UI locking.
        wait_time = delay if not paused else 50
        key = cv2.waitKeyEx(wait_time)
        
        # Escape or Q
        if key == 27 or key == ord('q') or key == ord('Q'):
            break
            
        # Spacebar
        elif key == 32:
            paused = not paused
            
        # Left arrow or comma (<)
        elif key in (65361, 2424832, 2, 63234, ord('a'), ord('A'), ord(','), ord('<')): 
            if paused and current_frame_idx > 0:
                current_frame_idx -= 1
                
        # Right arrow or period (>)
        elif key in (65363, 2555904, 3, 63235, ord('d'), ord('D'), ord('.'), ord('>')): 
            if paused and current_frame_idx < total_frames - 1:
                current_frame_idx += 1
                    
        # Restart video
        elif key in (ord('r'), ord('R'), ord('0')):
            current_frame_idx = 0
                    
        # Normal playback advance
        if not paused and key == -1:
            if current_frame_idx < total_frames - 1:
                current_frame_idx += 1
            else:
                paused = True

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
