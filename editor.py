import ffmpeg
import os
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont

# 1. Cloudinary Configuration with explicit error check
CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
API_KEY = os.environ.get('CLOUDINARY_API_KEY')
API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

if not all([CLOUD_NAME, API_KEY, API_SECRET]):
    print("❌ ERROR: Cloudinary Secrets are missing in GitHub!")
    exit(1)

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET,
    secure=True
)

def create_thumbnail(video_path, text, output_path):
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        # Added -update 1 to fix the 'image sequence' error from your logs
        (
            ffmpeg
            .input(video_path, ss=duration/2)
            .output('frame.jpg', vframes=1, **{'update': 1})
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        img = Image.open('frame.jpg')
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("bold_font.ttf", 150)
        except: font = ImageFont.load_default()
        draw.text((100, 400), text, font=font, fill="yellow")
        img.save(output_path)
    except Exception as e: 
        print(f"⚠️ Thumbnail warning: {e}")

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
    
    print("🚀 Uploading to Cloudinary...")
    try:
        response = cloudinary.uploader.upload_large(
            'final_short.mp4',
            resource_type="video",
            public_id="latest_short_video",
            overwrite=True,
            chunk_size=6000000 # 6MB chunks for better stability
        )
        download_url = response.get('secure_url')
        print(f"✅ FINAL_LINK: {download_url}")
        
        # Write to a file that GitHub Actions can read
        with open("link.txt", "w") as f:
            f.write(download_url)
            
    except Exception as e:
        print(f"❌ Cloudinary Error: {e}")
        exit(1)
