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

def find_default_mkv():
    # Try current directory first
    mkv_files = glob.glob('*.mkv')
    if mkv_files:
        return mkv_files[0]
        
    # Try parent directory
    parent_mkv_files = glob.glob(os.path.join('..', '*.mkv'))
    if parent_mkv_files:
        return parent_mkv_files[0]
        
    return None

def parse_mkv_time_and_camera(mkv_filename):
    """ Extract the camera ID and absolute start datetime from the MKV filename. """
    parts = mkv_filename.split('_')
    if len(parts) >= 5:
        camera_id = parts[0]
        date_str = parts[1]
        time_str = parts[2]
        us_str = parts[3]
        dt_str = f"{date_str} {time_str} {us_str}"
        start_time = datetime.datetime.strptime(dt_str, "%Y%m%d %H%M%S %f")
        return camera_id, start_time
    else:
        raise ValueError(f"Could not parse camera ID and time from MKV filename: {mkv_filename}")

def load_overlapping_ff_frames(camera_id, mkv_start_time, mkv_duration_seconds, search_dir, explicit_ff_dir=None):
    """
    Search for FF files matching the camera ID and overlapping with the MKV video's time span.
    Reconstructs the frames and returns a list of (absolute_frame_time, frame_image) tuples.
    """
    mkv_end_time = mkv_start_time + datetime.timedelta(seconds=mkv_duration_seconds)
    
    if explicit_ff_dir:
        # If user explicitly provided a path, look for FF files directly in that directory and its subdirectories
        ff_files = glob.glob(os.path.join(explicit_ff_dir, '**', 'FF*.fits'), recursive=True) + \
                   glob.glob(os.path.join(explicit_ff_dir, '**', 'FF*.bin'), recursive=True)
    else:
        # Default behavior: Locate the cameraID directory -> CapturedFiles
        camera_dir = os.path.join(search_dir, camera_id)
        captured_files_dir = os.path.join(camera_dir, 'CapturedFiles')
        
        if not os.path.isdir(captured_files_dir):
            print(f"Warning: CapturedFiles directory not found: {captured_files_dir}")
            return []
            
        # FF files are in subdirectories of CapturedFiles: cameraID_YYYYMMDD_HHmmss_xxxxxx
        ff_files = glob.glob(os.path.join(captured_files_dir, f'{camera_id}_*', 'FF*.fits')) + \
                   glob.glob(os.path.join(captured_files_dir, f'{camera_id}_*', 'FF*.bin'))
               
    print(f"Found {len(ff_files)} potential FF files to check for timestamp overlap.")
    reconstructed_frames = []
    
    for ff_path in sorted(ff_files):
        # 1. Parse time
        ff_filename = os.path.basename(ff_path)
        try:
            ff_start_time = filenameToDatetime(ff_filename)
        except Exception:
            continue
            
        # 2. Check overlap. FF files are 256 frames at ~25fps (roughly 10 seconds)
        ff_end_time = ff_start_time + datetime.timedelta(seconds=11) 
        
        if ff_start_time > mkv_end_time or ff_end_time < mkv_start_time:
            continue
            
        print(f"Loading overlapping FF file: {ff_filename}")
            
        # 3. Read and reconstruct the FF file
        ff = readFF(os.path.dirname(os.path.abspath(ff_path)), ff_filename)
        if ff is None:
            continue
            
        nframes = ff.nframes if ff.nframes > 0 else 256
        ff_fps = ff.fps if hasattr(ff, 'fps') and ff.fps > 0 else 25.0
        
        if ff.array is not None:
            ff.maxpixel = ff.array[0]
            ff.maxframe = ff.array[1]
            ff.avepixel = ff.array[2]
            
        # Apply Gaussian filter
        sigma = 5.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        smoothed_maxpixel = ndimage.gaussian_filter(ff.maxpixel.astype(float), sigma=sigma)
        ff.maxpixel = np.clip(smoothed_maxpixel, 0, 255).astype(np.uint8)
        
        # Determine base time
        if hasattr(ff, 'starttime') and ff.starttime:
            # If starttime is a properly loaded string header (like from a FITS DATE-OBS)
            if isinstance(ff.starttime, str):
                try:
                     # Some FITS DATE-OBS might not be perfect. Fallback to filename time.
                     pass 
                except:
                     pass
                     
        for i in range(nframes):
            frame = ff.avepixel.copy()
            indices = np.where(ff.maxframe == i)
            frame[indices] = ff.maxpixel[indices]
            
            # The absolute time for this specific FF frame
            frame_abs_time = ff_start_time + datetime.timedelta(seconds=i / ff_fps)
            
            # Convert to BGR for drawing later
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            reconstructed_frames.append((frame_abs_time, bgr_frame))
            
    # Sort the globally reconstructed list of frames chronologically
    reconstructed_frames.sort(key=lambda x: x[0])
    return reconstructed_frames
    
def get_nearest_ff_frame(ff_frames, target_time):
    """ Find the FF frame whose timestamp is closest to the given absolute target time """
    if not ff_frames:
        return None, None
        
    # Find absolute difference between target time and all FF frame times
    # This could be optimized via binary search for large arrays, but iterating is fine for 30 seconds of video.
    min_diff = None
    best_frame = None
    best_idx = 0
    best_time = None
    
    for idx, (frame_time, frame_img) in enumerate(ff_frames):
        diff = abs((frame_time - target_time).total_seconds())
        if min_diff is None or diff < min_diff:
            min_diff = diff
            best_frame = frame_img
            best_idx = idx
            best_time = frame_time
            
        # Since it's sorted chronologically, we can break early if difference starts increasing
        if min_diff is not None and diff > min_diff:
            break
            
    # Optional constraint: Only return if the closest frame is within 1s.
    if min_diff is not None and min_diff < 1.0:
         return best_frame, best_idx, best_time
    return None, None, None

def main():
    parser = argparse.ArgumentParser(description="Synchronized MKV and FF Video Player")
    parser.add_argument("video_path", nargs="?", help="Path to the MKV video file")
    parser.add_argument("--ff-dir", type=str, help="Optional explicit path to the directory containing FF files")
    parser.add_argument("--full-size", action="store_true", help="Display the videos at native 100% resolution (default is 50% scale)")
    parser.add_argument("--fps", type=float, default=25.0, help="Frame rate of the video (default: 25.0)")
    
    if '-h' in sys.argv or '--help' in sys.argv:
        parser.print_help()
        sys.exit(0)
        
    args = parser.parse_args()

    video_path = args.video_path
    if not video_path:
        video_path = find_default_mkv()
        
    if not video_path or not os.path.exists(video_path):
        print("Error: Could not find an MKV file.")
        print(f"Usage: python sync_player.py [path_to_video.mkv] [--full-size]")
        sys.exit(1)
        
    print(f"Playing MKV video: {video_path}")
    
    try:
        camera_id, start_time = parse_mkv_time_and_camera(os.path.basename(video_path))
        print(f"Extracted MKV properties -> Camera: {camera_id}, Start Time: {start_time}")
    except Exception as e:
        print(f"Error parsing MKV filename: {e}")
        sys.exit(1)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        sys.exit(1)
        
    # Get MKV properties
    fps = args.fps
    mkv_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    mkv_duration_seconds = mkv_total_frames / fps
    delay = int(1000 / fps) # milliseconds per frame
    print(f"MKV Total frames: {mkv_total_frames}, FPS (playback): {fps:.2f}, Duration: {mkv_duration_seconds:.2f}s")
    
    # Calculate default path 4 levels up to scan for `camera_id` FF files if not overridden
    abs_mkv_dir = os.path.abspath(os.path.dirname(video_path))
    search_dir = os.path.abspath(os.path.join(abs_mkv_dir, '..', '..', '..', '..'))
    
    if args.ff_dir:
        print(f"Searching for FF files in explicitly provided directory: '{args.ff_dir}'...")
    else:
        print(f"Searching for FF files in default directory '{os.path.join(search_dir, camera_id)}'...")
    
    ff_frames = load_overlapping_ff_frames(camera_id, start_time, mkv_duration_seconds, search_dir, explicit_ff_dir=args.ff_dir)
    print(f"Loaded {len(ff_frames)} overlapping FF frames.")

    if not args.full_size:
        print("Displaying at half size (default). Use --full-size for native resolution.")
    print("Controls:")
    print("  Click on a window to focus it. Controls apply to the focused window (MKV or FF).")
    print("  Spacebar : Pause/Resume focused video")
    print("  Left/Right or < / > : Step backward/forward 1 frame (when paused)")
    print("  s : Synchronize FF time to match MKV time")
    print("  R or 0 : Restart video from beginning")
    print("  Q or Esc : Quit both")

    mkv_paused = True
    ff_paused = True
    sync_mode = False
    
    current_frame_idx = 0
    mkv_filename = os.path.basename(video_path)
    mkv_window_name = f"Synchronized MKV Player: {mkv_filename}"
    ff_window_name = "Synchronized FF Player"
    
    # Initialize separate absolute time trackers
    mkv_current_abs_time = start_time
    ff_current_abs_time = start_time
    
    # Setup focus tracking
    setattr(main, 'active_window', mkv_window_name)

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN or event == cv2.EVENT_MOUSEMOVE:
            setattr(main, 'active_window', param)

    cv2.namedWindow(mkv_window_name)
    cv2.namedWindow(ff_window_name)
    cv2.setMouseCallback(mkv_window_name, mouse_callback, param=mkv_window_name)
    cv2.setMouseCallback(ff_window_name, mouse_callback, param=ff_window_name)
    
    # Read the first MKV frame
    ret, mkv_frame = cap.read()
    if not ret:
        print("Error: Could not read the MKV first frame.")
        cap.release()
        sys.exit(1)
        
    while True:
        # ---- Render MKV Frame ----
        mkv_display_frame = mkv_frame.copy()
        
        if not args.full_size:
            mkv_display_frame = cv2.resize(mkv_display_frame, (0, 0), fx=0.5, fy=0.5)
            
        text = f"Frame: {current_frame_idx}"
        cv2.putText(mkv_display_frame, text, (10, mkv_display_frame.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        elapsed_seconds = current_frame_idx / fps
        mins = int(elapsed_seconds // 60)
        secs = int(elapsed_seconds % 60)
        micros = int((elapsed_seconds - int(elapsed_seconds)) * 1_000_000)
        time_text = f"{mins:02d}:{secs:02d}.{micros:06d}"
        
        text_size, _ = cv2.getTextSize(time_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        x_pos = mkv_display_frame.shape[1] - text_size[0] - 10
        cv2.putText(mkv_display_frame, time_text, (x_pos, mkv_display_frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        # Absolute time in upper right
        current_abs_time = start_time + datetime.timedelta(seconds=float(elapsed_seconds))
        abs_time_text = current_abs_time.strftime("%Y%m%d %H:%M:%S.%f")
        text_size, _ = cv2.getTextSize(abs_time_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        x_pos = mkv_display_frame.shape[1] - text_size[0] - 10
        cv2.putText(mkv_display_frame, abs_time_text, (x_pos, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        if mkv_paused:
            cv2.putText(mkv_display_frame, "PAUSED", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                        
        if sync_mode:
            cv2.putText(mkv_display_frame, "SYNC", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow(mkv_window_name, mkv_display_frame)
        
        # ---- Render FF Frame ----
        # Render the FF frame that is closest to `ff_current_abs_time`
        matched_ff_frame, ff_frame_idx, actual_ff_time = get_nearest_ff_frame(ff_frames, ff_current_abs_time)
        
        if matched_ff_frame is not None:
             ff_display_frame = matched_ff_frame.copy()
             if not args.full_size:
                 ff_display_frame = cv2.resize(ff_display_frame, (0, 0), fx=0.5, fy=0.5)
                 
             if actual_ff_time is not None and start_time is not None:
                 if sync_mode:
                     time_diff_ms = (actual_ff_time - current_abs_time).total_seconds() * 1000
                     ff_time_text = f"Diff: {time_diff_ms:+.3f} ms"
                 else:
                     ff_elapsed = (actual_ff_time - start_time).total_seconds()
                     ff_mins = int(ff_elapsed // 60)
                     ff_secs = int(ff_elapsed % 60)
                     ff_micros = int((ff_elapsed - int(ff_elapsed)) * 1_000_000)
                     ff_time_text = f"{ff_mins:02d}:{ff_secs:02d}.{ff_micros:06d}"
                 ff_abs_text = actual_ff_time.strftime("%Y%m%d %H:%M:%S.%f")
             else:
                 ff_time_text = "00:00.000000"
                 ff_abs_text = "Unknown"
                 
             # Inherit UI overlays for consistency
             cv2.putText(ff_display_frame, f"Frame: {ff_frame_idx}", (10, ff_display_frame.shape[0] - 20), 
                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
             
             text_size, _ = cv2.getTextSize(ff_time_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
             x_pos = ff_display_frame.shape[1] - text_size[0] - 10
             cv2.putText(ff_display_frame, ff_time_text, (x_pos, ff_display_frame.shape[0] - 20),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                         
             text_size, _ = cv2.getTextSize(ff_abs_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
             x_pos = ff_display_frame.shape[1] - text_size[0] - 10
             cv2.putText(ff_display_frame, ff_abs_text, (x_pos, 30),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                         
             if sync_mode:
                 # When in sync mode, display the MKV master time directly below the FF interpolated time
                 mkv_abs_text = f"MKV {current_abs_time.strftime('%H:%M:%S.%f')}"
                 mkv_text_size, _ = cv2.getTextSize(mkv_abs_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                 mkv_x_pos = ff_display_frame.shape[1] - mkv_text_size[0] - 10
                 cv2.putText(ff_display_frame, mkv_abs_text, (mkv_x_pos, 60),
                             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
                             
             if ff_paused:
                  cv2.putText(ff_display_frame, "PAUSED", (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)           
             if sync_mode:
                  cv2.putText(ff_display_frame, "SYNC", (10, 60), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
             
             cv2.imshow(ff_window_name, ff_display_frame)

        # ---- Event Polling ----
        # Wait for key press. Delay to prevent UI locking.
        # We loop 50ms unless BOTH are unpaused.
        wait_time = delay if (not mkv_paused or not ff_paused) else 50
        key = cv2.waitKeyEx(wait_time)
        
        # Figure out which window has GUI focus (OpenCV lacks great support, but getWindowProperty works usually)
        mkv_focused = False
        ff_focused = False
        try:
            mkv_focused = cv2.getWindowProperty(mkv_window_name, cv2.WND_PROP_VISIBLE) > 0 and \
                          cv2.getWindowProperty(mkv_window_name, cv2.WND_PROP_AUTOSIZE) >= 0
            # Usually the last clicked window is considered active, but there's no native "focused" property 
            # We assume MKV is default if unsure. We will apply commands to BOTH if we can't tell, or selectively if we can.
            # actually cv2 doesn't have a reliable cross-platform "focus" concept for waitKey. 
            # We will use modifiers: spacebar/arrows applies to MKV. shift+spacebar/arrows applies to FF.
            # BUT the prompt asked for "individual". A better way is mouse clicking -> we can set a callback to track focus.
        except Exception:
            pass

        # Check for Escape or Q (Global quit)
        if key == 27 or key == ord('q') or key == ord('Q'):
            break
            
        # Synchronization key 's' (Toggle sync mode to link controls without snapping time)
        elif key == ord('s') or key == ord('S'):
            sync_mode = not sync_mode
            if sync_mode:
                ff_paused = mkv_paused
                print("Linked playback controls.")
            else:
                print("Unlinked controls.")
            
        # Due to OpenCV focus limitations, we use a simpler approach:
        # Standard keys (space, a, d) control MKV.
        # Shifted keys/alternate (Enter/m, j, l) or similar control FF? The prompt says "individually".
        # Since cv2 doesn't easily expose which window is active to keyboard inputs robustly across OSes
        # Let's use a mouse callback to track the active window.
        
        # (Handling Mouse focus state logic injected during init)
        
        active_window = getattr(main, 'active_window', mkv_window_name)

        if sync_mode:
            if key == 32: # Spacebar
                mkv_paused = not mkv_paused
                ff_paused = mkv_paused
            elif key in (65361, 2424832, 2, 63234, ord('a'), ord('A'), ord(','), ord('<')): 
                if mkv_paused and current_frame_idx > 0:
                    current_frame_idx -= 1
                    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
                    ret, mkv_frame = cap.read()
                    ff_current_abs_time -= datetime.timedelta(seconds=1.0/fps)
            elif key in (65363, 2555904, 3, 63235, ord('d'), ord('D'), ord('.'), ord('>')): 
                if mkv_paused and current_frame_idx < mkv_total_frames - 1:
                    current_frame_idx += 1
                    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
                    ret, mkv_frame = cap.read()
                    ff_current_abs_time += datetime.timedelta(seconds=1.0/fps)
            elif key in (ord('r'), ord('R'), ord('0')):
                current_frame_idx = 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, mkv_frame = cap.read()
                ff_current_abs_time = start_time

        elif active_window == mkv_window_name:
            if key == 32: # Spacebar
                mkv_paused = not mkv_paused
            elif key in (65361, 2424832, 2, 63234, ord('a'), ord('A'), ord(','), ord('<')): 
                if mkv_paused and current_frame_idx > 0:
                    current_frame_idx -= 1
                    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
                    ret, mkv_frame = cap.read()
            elif key in (65363, 2555904, 3, 63235, ord('d'), ord('D'), ord('.'), ord('>')): 
                if mkv_paused and current_frame_idx < mkv_total_frames - 1:
                    current_frame_idx += 1
                    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
                    ret, mkv_frame = cap.read()
            elif key in (ord('r'), ord('R'), ord('0')):
                current_frame_idx = 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, mkv_frame = cap.read()
                
        elif active_window == ff_window_name:
            if key == 32: # Spacebar
                ff_paused = not ff_paused
            elif key in (65361, 2424832, 2, 63234, ord('a'), ord('A'), ord(','), ord('<')): 
                if ff_paused:
                    # Step FF back exactly 1 frame relative to its own FPS
                    ff_current_abs_time -= datetime.timedelta(seconds=1.0/fps)
            elif key in (65363, 2555904, 3, 63235, ord('d'), ord('D'), ord('.'), ord('>')): 
                if ff_paused:
                    # Step FF forward exactly 1 frame relative to its own FPS
                    ff_current_abs_time += datetime.timedelta(seconds=1.0/fps)
            elif key in (ord('r'), ord('R'), ord('0')):
                ff_current_abs_time = start_time

        # Normal playback advance
        if not mkv_paused and key == -1:
            ret, next_frame = cap.read()
            if ret:
                mkv_frame = next_frame
                current_frame_idx += 1
            else:
                mkv_paused = True
                
        if not ff_paused and key == -1:
            if ff_current_abs_time is not None:
                ff_current_abs_time += datetime.timedelta(seconds=1.0/fps)
            
        mkv_current_abs_time = start_time + datetime.timedelta(seconds=float(current_frame_idx / fps))
        current_abs_time = mkv_current_abs_time

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
