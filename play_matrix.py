#!/usr/bin/env python3
import os
import subprocess
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

# ── CONFIGURATION ──
MEDIA_DIR    = "/home/pi/matrix_media"
VIDEO_FRAME_DELAY = None  # Managed by ffmpeg frame rate

# Matrix settings (adjust for your panel):
options = RGBMatrixOptions()
options.rows             = 64
options.cols             = 64
options.chain_length     = 1
options.parallel         = 1
options.hardware_mapping = "adafruit-hat"  # or your specific mapping

# Initialize the matrix
matrix = RGBMatrix(options=options)


def play_mp4(video_path):
    """
    Play an MP4 video by streaming raw RGB frames via ffmpeg in a loop.
    """
    frame_w  = options.cols * options.chain_length
    frame_h  = options.rows * options.parallel
    frame_sz = frame_w * frame_h * 3  # RGB24

    # ffmpeg command: read video, scale to matrix size, output raw RGB24
    ffmpeg_cmd = [
        "ffmpeg",
        "-stream_loop", "-1",             # loop indefinitely
        "-i", video_path,
        "-vf", f"scale={frame_w}:{frame_h}",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-loglevel", "quiet",
        "-"
    ]

    p = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE)
    try:
        while True:
            raw_frame = p.stdout.read(frame_sz)
            if len(raw_frame) < frame_sz:
                break
            img = Image.frombuffer(
                "RGB",
                (frame_w, frame_h),
                raw_frame,
                "raw",
                "RGB",
                0,
                1
            )
            matrix.SetImage(img)
    except KeyboardInterrupt:
        p.kill()
    finally:
        p.stdout.close()
        p.wait()


def main():
    # Collect only MP4 files
    mp4_files = sorted([
        os.path.join(MEDIA_DIR, f)
        for f in os.listdir(MEDIA_DIR)
        if f.lower().endswith('.mp4')
    ])

    if not mp4_files:
        print(f"No MP4 files found in {MEDIA_DIR}")
        return

    # Loop through videos indefinitely
    while True:
        for video_path in mp4_files:
            play_mp4(video_path)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Video playback script error: {e}")
