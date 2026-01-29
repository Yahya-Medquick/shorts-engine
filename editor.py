import ffmpeg
import os
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont

# 1. Cloudinary Configuration
# Ensure these names match your GitHub Secrets exactly
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
        # Added -update 1 to prevent image sequence errors
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
        print(f"⚠️ Thumbnail warning (ignoring): {e}")

def process_video(input_path, output_path, music_path, hook_path):
    print("🎬 Starting FFmpeg Engine...")
    # Hook segment
    h_v = ffmpeg.input(hook_path).video.filter('scale', 1080, 1920, force_original_aspect_ratio='decrease').filter('pad', 1080, 1920, '(ow-iw)/2', '(oh-ih)/2')
    h_a = ffmpeg.input(hook_path).audio
    
    # Main content segment
    v_v = ffmpeg.input(input_path).video.filter('scale', 1080, 1920, force_original_aspect_ratio='decrease').filter('pad', 1080, 1920, '(ow-iw)/2', '(oh-ih)/2')
    v_a = ffmpeg.input(input_path).audio
    
    # Audio processing
    voice = v_a.filter('afftdn', nr=12).filter('loudnorm')
    bg = ffmpeg.input(music_path).audio.filter('volume', 0.15)
    mixed_a = ffmpeg.filter([voice, bg], 'amix', duration='first')
    
    # Joining segments
    joined = ffmpeg.concat(h_v, h_a, v_v, mixed_a, v=1, a=1).node
    ffmpeg.output(joined[0], joined[1], output_path, vcodec='libx264', crf=23, preset='fast').run(overwrite_output=True)
    
    create_thumbnail(output_path, "READY!", "thumbnail.jpg")

if __name__ == "__main__":
    # Step 1: Run the editing logic
    process_video('raw_input.mp4', 'final_short.mp4', 'bg_music.mp3', 'hook.mp4')
    
    # Step 2: Upload to Cloudinary
    print("🚀 Uploading to Cloudinary (this may take a minute)...")
    try:
        # Simplified upload to avoid 'Invalid Signature' errors
        # We use a unique public_id based on a timestamp to avoid conflict
        import time
        unique_id = f"video_{int(time.time())}"
        
        response = cloudinary.uploader.upload_large(
            'final_short.mp4',
            resource_type="video",
            public_id=unique_id
        )
        
        download_url = response.get('secure_url')
        print(f"✅ SUCCESS! Final Link: {download_url}")
        
        # Save link for GitHub Actions to use
        with open("link.txt", "w") as f:
            f.write(download_url)
            
    except Exception as e:
        print(f"❌ Cloudinary Error: {e}")
        # Providing the raw error helps debug if secrets are still wrong
        exit(1)
