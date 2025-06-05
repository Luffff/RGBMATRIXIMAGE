#!/usr/bin/env python3
import os
import time
import subprocess
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageSequence

# ── CONFIGURATION ──
MEDIA_DIR    = "/home/pi/matrix_media"
VIDEO_PATH   = None   # e.g. "/home/pi/matrix_media/video.mp4", or leave None if no video
IMAGE_DISPLAY_TIME = 3.0   # seconds per static image
APNG_FRAME_DELAY   = 0.1   # default delay (sec) between APNG frames

# Matrix settings (adjust for your panel):
options = RGBMatrixOptions()
options.rows             = 64
options.cols             = 64
options.chain_length     = 1
options.parallel         = 1
options.hardware_mapping = "adafruit-hat"  # or your specific mapping
# options.brightness   = 50   # if you want to dial down brightness

# Initialize the matrix
matrix = RGBMatrix(options=options)


def display_image(image_path):
    """
    If the file is a multi-frame PNG/GIF (i.e. img.is_animated==True),
    iterate through each frame (using PIL.ImageSequence), resize and display.
    Otherwise, treat it as a static image.
    """
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Failed to open {image_path}: {e}")
        return

    # If this is an animated image (e.g. APNG or GIF), step through frames:
    if getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1:
        # Loop through each frame once
        for frame in ImageSequence.Iterator(img):
            frame_rgb = frame.convert("RGB").resize((
                options.cols * options.chain_length,
                options.rows * options.parallel
            ))
            matrix.SetImage(frame_rgb)
            time.sleep(APNG_FRAME_DELAY)
        return

    # Otherwise, static image: convert, resize, display
    img_rgb = img.convert("RGB").resize((
        options.cols * options.chain_length,
        options.rows * options.parallel
    ))
    matrix.SetImage(img_rgb)


def play_video(video_path):
    """
    Play a video (MP4/AVI/etc.) by streaming raw RGB frames via ffmpeg.
    Make sure `ffmpeg` is installed (sudo apt install ffmpeg).
    """
    frame_w  = options.cols * options.chain_length
    frame_h  = options.rows * options.parallel
    frame_sz = frame_w * frame_h * 3  # RGB24

    ffmpeg_cmd = [
        "ffmpeg",
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
                break  # End of video
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
    # Optional: pull latest media from GitHub (if online)
    # If your Pi is offline, wrap this in try/except or just comment it out.
    try:
        os.chdir(MEDIA_DIR)
        subprocess.run(["git", "pull"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    except Exception:
        pass

    # If VIDEO_PATH is set and exists, play the video (then exit)
    if VIDEO_PATH and os.path.isfile(VIDEO_PATH):
        play_video(VIDEO_PATH)
        return

    # Otherwise, collect all image files in MEDIA_DIR
    image_extensions = (".png", ".jpg", ".jpeg", ".gif")
    image_files = sorted(
        os.path.join(MEDIA_DIR, f)
        for f in os.listdir(MEDIA_DIR)
        if f.lower().endswith(image_extensions)
    )

    if not image_files:
        print(f"No image files found in {MEDIA_DIR}")
        return

    # Loop forever: for each file, decide if it's animated (APNG/GIF) or static
    while True:
        for img_path in image_files:
            display_image(img_path)
            # If that file was static (single-frame), wait the full display time;
            # if it was animated, display_image() already iterated its frames once.
            try:
                # Re-open to check if it was animated
                test_img = Image.open(img_path)
                is_anim = getattr(test_img, "is_animated", False) or getattr(test_img, "n_frames", 1) > 1
                test_img.close()
                if not is_anim:
                    time.sleep(IMAGE_DISPLAY_TIME)
            except Exception:
                # If opening fails here, just pause for a moment
                time.sleep(IMAGE_DISPLAY_TIME)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Playback script error: {e}")
