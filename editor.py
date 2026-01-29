import ffmpeg
import os
import json
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont

# 1. Cloudinary Configuration
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

def create_thumbnail(video_path, text, output_path):
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        ffmpeg.input(video_path, ss=duration/2).output('frame.jpg', vframes=1).run(overwrite_output=True)
        img = Image.open('frame.jpg')
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("bold_font.ttf", 150)
        except: font = ImageFont.load_default()
        draw.text((100, 400), text, font=font, fill="yellow")
        img.save(output_path)
    except Exception as e: print(f"Thumbnail error: {e}")

def process_video(input_path, output_path, music_path, hook_path):
    print("🎬 Starting FFmpeg Engine...")
    h_v = ffmpeg.input(hook_path).video.filter('scale', 1080, 1920, force_original_aspect_ratio='decrease').filter('pad', 1080, 1920, '(ow-iw)/2', '(oh-ih)/2')
    h_a = ffmpeg.input(hook_path).audio
    v_v = ffmpeg.input(input_path).video.filter('scale', 1080, 1920, force_original_aspect_ratio='decrease').filter('pad', 1080, 1920, '(ow-iw)/2', '(oh-ih)/2')
    v_a = ffmpeg.input(input_path).audio
    
    voice = v_a.filter('afftdn', nr=12).filter('loudnorm')
    bg = ffmpeg.input(music_path).audio.filter('volume', 0.15)
    mixed_a = ffmpeg.filter([voice, bg], 'amix', duration='first')
    
    joined = ffmpeg.concat(h_v, h_a, v_v, mixed_a, v=1, a=1).node
    ffmpeg.output(joined[0], joined[1], output_path, vcodec='libx264', crf=23, preset='fast').run(overwrite_output=True)
    create_thumbnail(output_path, "READY!", "thumbnail.jpg")

if __name__ == "__main__":
    process_video('raw_input.mp4', 'final_short.mp4', 'bg_music.mp3', 'hook.mp4')
    
    print("🚀 Uploading high-quality video to Cloudinary...")
    # upload_large handles big files in 20MB chunks automatically
    response = cloudinary.uploader.upload_large(
        'final_short.mp4',
        resource_type="video",
        public_id="latest_short_video",
        overwrite=True,
        chunk_size=20000000 
    )
    
    # Store the URL for the frontend/email
    download_url = response.get('secure_url')
    print(f"✅ FINAL_LINK: {download_url}")
    
    with open("download_link.txt", "w") as f:
        f.write(download_url)
