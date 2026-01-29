import ffmpeg
import os
import random
from PIL import Image, ImageDraw, ImageFont

def create_thumbnail(video_path, text, output_path):
    # Extract a frame from the middle of the video
    probe = ffmpeg.probe(video_path)
    duration = float(probe['format']['duration'])
    ffmpeg.input(video_path, ss=duration/2).output('frame.jpg', vframes=1).run(overwrite_output=True)
    
    # Draw text on it
    img = Image.open('frame.jpg')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("assets/bold_font.ttf", 150)
    except:
        font = ImageFont.load_default() # Fallback

    # Draw Text with Outline for visibility
    x, y = 100, 400
    # Outline
    draw.text((x-5, y), text, font=font, fill="black")
    draw.text((x+5, y), text, font=font, fill="black")
    # Main Text
    draw.text((x, y), text, font=font, fill="yellow")
    
    img.save(output_path)

def process_video(input_path, output_path, music_path, hook_path):
    # 1. Video Processing
    video_stream = ffmpeg.input(input_path).video.filter('unsharp', luma_msize_x=7, luma_msize_y=7, luma_amount=0.8).filter('scale', 1080, 1920)
    audio_stream = ffmpeg.input(input_path).audio

    # 2. Audio Processing
    voice = audio_stream.filter('afftdn', nr=12).filter('loudnorm')
    bg_music = ffmpeg.input(music_path).audio.filter('volume', 0.15)
    final_audio = ffmpeg.filter([voice, bg_music], 'amix', duration='first')

    # 3. Merge Hook + Main
    hook_v = ffmpeg.input(hook_path).video
    hook_a = ffmpeg.input(hook_path).audio
    joined = ffmpeg.concat(hook_v, hook_a, video_stream, final_audio, v=1, a=1).node

    # 4. Render Video
    out = ffmpeg.output(joined[0], joined[1], output_path, vcodec='libx264', crf=23, preset='fast')
    out.run(overwrite_output=True)

    # 5. Generate Thumbnail
    titles = ["WAIT FOR IT!", "DID YOU KNOW?", "MIND BLOWING!", "SECRET HACK"]
    create_thumbnail(output_path, random.choice(titles), "thumbnail.jpg")

if __name__ == "__main__":
    # Ensure assets exist
    if not os.path.exists('bg_music.mp3'):
        print("Error: Missing bg_music.mp3")
        exit(1)
        
    process_video('raw_input.mp4', 'final_short.mp4', 'assets/bg_music.mp3', 'assets/hook.mp4')
