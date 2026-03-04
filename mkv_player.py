import cv2
import sys
import os
import glob
import argparse

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

def main():
    parser = argparse.ArgumentParser(description="MKV Video Player")
    parser.add_argument("video_path", nargs="?", help="Path to the MKV video file")
    parser.add_argument("--full-size", action="store_true", help="Display the video at its native 100% resolution (default is 50% scale)")
    parser.add_argument("--fps", type=float, default=25.0, help="Frame rate of the video (default: 25.0)")
    args = parser.parse_args()

    video_path = args.video_path
    if not video_path:
        video_path = find_default_mkv()
        
    if not video_path or not os.path.exists(video_path):
        print("Error: Could not find an MKV file.")
        print(f"Usage: python mkv_player.py [path_to_video.mkv] [--full-size]")
        sys.exit(1)
        
    print(f"Playing video: {video_path}")
    if not args.full_size:
        print("Displaying at half size (default). Use --full-size for native resolution.")
    print("Controls:")
    print("  Spacebar : Pause/Resume")
    print("  Left/Right : Step backward/forward 1 frame (when paused)")
    print("  R or 0 : Restart video from beginning")
    print("  Q or Esc : Quit")

    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        sys.exit(1)
        
    # Get video properties
    fps = args.fps
        
    delay = int(1000 / fps) # milliseconds per frame
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total frames: {total_frames}, FPS (playback): {fps:.2f}")

    paused = False
    current_frame_idx = 0
    window_name = "MKV Player"
    
    # Read the first frame
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read the first frame.")
        cap.release()
        sys.exit(1)
        
    while True:
        # Create a copy so we can cleanly draw the frame number
        display_frame = frame.copy()
        
        if not args.full_size:
            display_frame = cv2.resize(display_frame, (0, 0), fx=0.5, fy=0.5)
            
        # Add frame number text in lower left
        # cv2.putText(image, text, org(bottom-left), font, fontScale, color, thickness)
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
                    
        if paused:
            cv2.putText(display_frame, "PAUSED", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        cv2.imshow(window_name, display_frame)

        # Wait for key press
        wait_time = delay if not paused else 0
        key = cv2.waitKeyEx(wait_time)
        
        # Cross-platform keys can be tricky
        # Escape or Q
        if key == 27 or key == ord('q') or key == ord('Q'):
            break
            
        # Spacebar
        elif key == 32:
            paused = not paused
            
        # Left arrow
        elif key in (65361, 2424832, 2, ord('a'), ord('A')): 
            if paused and current_frame_idx > 0:
                current_frame_idx -= 1
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
                ret, frame = cap.read()
                if not ret: break
                
        # Right arrow
        elif key in (65363, 2555904, 3, ord('d'), ord('D')): 
            if paused and current_frame_idx < total_frames - 1:
                # To move forward one frame while paused, we just read the *next* one
                current_frame_idx += 1
                ret, frame = cap.read()
                if not ret:
                    # Reached end of file during frame step
                    current_frame_idx -= 1
                    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
                    ret, frame = cap.read()
                    
        # Restart video
        elif key in (ord('r'), ord('R'), ord('0')):
            current_frame_idx = 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret: break
                    
        # Normal playback advance
        if not paused and key == -1:
            ret, next_frame = cap.read()
            if ret:
                frame = next_frame
                current_frame_idx += 1
            else:
                # Pause at end of video
                paused = True

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
