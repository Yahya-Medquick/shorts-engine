import ffmpeg
import os
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import time
import sys

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

def check_video_duration(video_path):
    """Check if video is at least 15 seconds"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    cap.release()
    return duration

def enhance_video(input_path, output_path):
    """Apply basic video enhancements"""
    print("🎬 Enhancing video quality...")
    
    # Get video info
    probe = ffmpeg.probe(input_path)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    
    if not video_stream:
        raise Exception("No video stream found")
    
    # Apply enhancements
    (
        ffmpeg
        .input(input_path)
        .filter('eq', brightness=0.05, contrast=1.1, saturation=1.2)
        .filter('unsharp', luma_msize_x=5, luma_msize_y=5, luma_amount=1.0)
        .output('enhanced.mp4', vcodec='libx264', crf=20, preset='medium')
        .run(overwrite_output=True, quiet=True)
    )
    return 'enhanced.mp4'

def create_thumbnail(video_path, text, output_path):
    """Create professional thumbnail"""
    try:
        # Extract frame from 25% of video for better thumbnail
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        ss_time = duration * 0.25  # Get frame at 25% mark
        
        # Extract frame
        (
            ffmpeg
            .input(video_path, ss=ss_time)
            .output('thumbnail_frame.jpg', vframes=1)
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        
        # Process thumbnail
        img = Image.open('thumbnail_frame.jpg')
        
        # Resize to YouTube thumbnail size
        img = img.resize((1280, 720), Image.Resampling.LANCZOS)
        
        # Add gradient overlay
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Add gradient from bottom
        for i in range(200):
            alpha = int(150 * (1 - i/200))
            draw.rectangle([0, img.height-i, img.width, img.height-i+1], 
                          fill=(0, 0, 0, alpha))
        
        # Add text
        try:
            font = ImageFont.truetype("bold_font.ttf", 80)
        except:
            font = ImageFont.load_default()
        
        # Text with shadow effect
        draw.text((50, img.height-200), "PRO", font=font, fill=(255, 215, 0, 255))
        draw.text((180, img.height-200), "VIDEO", font=font, fill=(255, 255, 255, 255))
        
        # Composite and save
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        img.convert('RGB').save(output_path, quality=95)
        
        print(f"✅ Thumbnail created: {output_path}")
        
    except Exception as e:
        print(f"⚠️ Using fallback thumbnail: {e}")
        # Create simple thumbnail
        img = Image.new('RGB', (1280, 720), color=(41, 128, 185))
        draw = ImageDraw.Draw(img)
        draw.text((100, 300), "PRO VIDEO READY", fill=(255, 255, 255), font=font)
        img.save(output_path)

def process_video(input_path, output_path, music_path, hook_path):
    """Main video processing function"""
    print("🚀 Starting professional video processing...")
    
    # Check video duration
    duration = check_video_duration(input_path)
    print(f"📊 Original duration: {duration:.2f} seconds")
    
    if duration < 15:
        print("⚠️ Video is shorter than 15 seconds, adding slow-motion effect")
        # Slow down short videos
        (
            ffmpeg
            .input(input_path)
            .filter('setpts', '2.0*PTS')
            .output('slow_input.mp4')
            .run(overwrite_output=True)
        )
        input_path = 'slow_input.mp4'
    
    # Enhance video quality
    enhanced_path = enhance_video(input_path, 'enhanced.mp4')
    
    print("🎵 Adding audio processing...")
    
    # Hook segment processing
    h_v = ffmpeg.input(hook_path).video.filter('scale', 1080, 1920, 
                                              force_original_aspect_ratio='increase').filter('crop', 1080, 1920)
    h_a = ffmpeg.input(hook_path).audio
    
    # Main video processing
    v_v = ffmpeg.input(enhanced_path).video.filter('scale', 1080, 1920,
                                                  force_original_aspect_ratio='increase').filter('crop', 1080, 1920)
    v_a = ffmpeg.input(enhanced_path).audio
    
    # Advanced audio processing
    voice = v_a.filter('afftdn', nr=10).filter('loudnorm', I=-16, TP=-1.5, LRA=11)
    bg = ffmpeg.input(music_path).audio.filter('volume', 0.12)
    
    # Mix audio with fade
    mixed_a = ffmpeg.filter([voice, bg], 'amix', duration='longest', dropout_transition=1000)
    
    # Join segments with transition
    joined = ffmpeg.concat(
        h_v, h_a,
        v_v, mixed_a,
        v=1, a=1
    ).node
    
    # Final render with optimal settings
    ffmpeg.output(
        joined[0], joined[1],
        output_path,
        vcodec='libx264',
        crf=21,  # Slightly better quality
        preset='medium',
        acodec='aac',
        audio_bitrate='192k',
        movflags='+faststart',  # For web playback
        **{'pix_fmt': 'yuv420p'}
    ).run(overwrite_output=True)
    
    print(f"✅ Video processing complete: {output_path}")
    
    # Create thumbnail
    create_thumbnail(output_path, "PRO EDITION", "thumbnail.jpg")

def upload_to_cloudinary(file_path, resource_type="video"):
    """Upload file to Cloudinary with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"📤 Uploading to Cloudinary (attempt {attempt + 1}/{max_retries})...")
            
            # Generate unique ID
            timestamp = int(time.time())
            unique_id = f"professional_video_{timestamp}"
            
            upload_params = {
                "resource_type": resource_type,
                "public_id": unique_id,
                "overwrite": True,
                "invalidate": True,
            }
            
            if resource_type == "video":
                upload_params.update({
                    "format": "mp4",
                    "quality": "auto",
                    "fetch_format": "auto"
                })
            
            response = cloudinary.uploader.upload(
                file_path,
                **upload_params
            )
            
            download_url = response.get('secure_url')
            print(f"✅ Upload successful!")
            return download_url
            
        except Exception as e:
            print(f"⚠️ Upload attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

if __name__ == "__main__":
    try:
        # Step 1: Process video
        process_video('raw_input.mp4', 'final_short.mp4', 'bg_music.mp3', 'hook.mp4')
        
        # Step 2: Upload video to Cloudinary
        print("🚀 Uploading processed video...")
        video_url = upload_to_cloudinary('final_short.mp4', "video")
        
        # Step 3: Upload thumbnail
        print("🖼️ Uploading thumbnail...")
        thumbnail_url = upload_to_cloudinary('thumbnail.jpg', "image")
        
        # Create combined results file
        results = f"""Video URL: {video_url}
Thumbnail URL: {thumbnail_url}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}
Processing: Complete"""

        with open("link.txt", "w") as f:
            f.write(video_url)
        
        with open("results.txt", "w") as f:
            f.write(results)
        
        print(f"\n🎉 PROCESSING COMPLETE!")
        print(f"📹 Video: {video_url}")
        print(f"🖼️ Thumbnail: {thumbnail_url}")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        sys.exit(1)
