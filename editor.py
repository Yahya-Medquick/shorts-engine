import ffmpeg
import os
import random
from PIL import Image, ImageDraw, ImageFont

def create_thumbnail(video_path, text, output_path):
    """Generates a high-quality thumbnail from a video frame."""
    try:
        # Extract a frame from the middle of the video
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        ffmpeg.input(video_path, ss=duration/2).output('frame.jpg', vframes=1).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        img = Image.open('frame.jpg')
        draw = ImageDraw.Draw(img)
        
        # Look for the font in the root folder
        try:
            font = ImageFont.truetype("bold_font.ttf", 150)
        except:
            font = ImageFont.load_default()

        # Position and styling
        x, y = 100, 400
        # Draw text shadow/outline for readability
        draw.text((x-5, y), text, font=font, fill="black")
        draw.text((x+5, y), text, font=font, fill="black")
        # Draw main text
        draw.text((x, y), text, font=font, fill="yellow")
        
        img.save(output_path)
        print(f"✅ Thumbnail created at {output_path}")
    except Exception as e:
        print(f"⚠️ Thumbnail failed: {e}")

def process_video(input_path, output_path, music_path, hook_path):
    """Processes, merges, and enhances the video for Shorts."""
    
    # 1. Prepare Hook Segment (Force to 1080x1920)
    hook_v = (
        ffmpeg.input(hook_path).video
        .filter('scale', 1080, 1920, force_original_aspect_ratio='decrease')
        .filter('pad', 1080, 1920, '(ow-iw)/2', '(oh-ih)/2')
    )
    hook_a = ffmpeg.input(hook_path).audio

    # 2. Prepare Main Video (Scale + Pad + Unsharp filter for quality)
    video_stream = (
        ffmpeg.input(input_path).video
        .filter('scale', 1080, 1920, force_original_aspect_ratio='decrease')
        .filter('pad', 1080, 1920, '(ow-iw)/2', '(oh-ih)/2')
        .filter('unsharp', luma_msize_x=7, luma_msize_y=7, luma_amount=0.8)
    )
    audio_stream = ffmpeg.input(input_path).audio

    # 3. Audio Mixing
    # Clean noise from voice and normalize volume
    voice = audio_stream.filter('afftdn', nr=12).filter('loudnorm')
    # Background music at 15% volume
    bg_music = ffmpeg.input(music_path).audio.filter('volume', 0.15)
    # Mix voice and music
    final_audio = ffmpeg.filter([voice, bg_music], 'amix', duration='first')

    # 4. Concatenate (Glue) Hook + Main Segment
    # This requires both segments to have identical resolutions and aspect ratios
    joined = ffmpeg.concat(hook_v, hook_a, video_stream, final_audio, v=1, a=1).node

    # 5. Export/Render
    print("🎬 Starting FFmpeg render...")
    out = ffmpeg.output(
        joined[0], joined[1], 
        output_path, 
        vcodec='libx264', 
        acodec='aac', 
        crf=23, 
        preset='fast'
    )
    out.run(overwrite_output=True)
    print(f"✅ Video rendered at {output_path}")

    # 6. Final Touch: Thumbnail
    titles = ["WAIT FOR IT!", "DID YOU KNOW?", "MIND BLOWING!", "SECRET HACK"]
    create_thumbnail(output_path, random.choice(titles), "thumbnail.jpg")

if __name__ == "__main__":
    # Ensure mandatory files exist before starting
    required_files = ['raw_input.mp4', 'bg_music.mp3', 'hook.mp4', 'bold_font.ttf']
    missing = [f for f in required_files if not os.path.exists(f)]
    
    if missing:
        print(f"❌ Error: Missing files: {', '.join(missing)}")
        print(f"Current Directory Contents: {os.listdir('.')}")
        exit(1)

    try:
        process_video('raw_input.mp4', 'final_short.mp4', 'bg_music.mp3', 'hook.mp4')
        print("🚀 Pipeline Finished Successfully!")
    except Exception as e:
        print(f"❌ Pipeline Failed: {e}")
        exit(1)
