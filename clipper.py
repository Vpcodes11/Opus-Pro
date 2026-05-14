"""Video clipping and caption burning with FFmpeg"""
import subprocess
import os
import json
from config import TARGET_WIDTH, TARGET_HEIGHT, CAPTION_STYLES, DEFAULT_CAPTION_STYLE, PRESETS


def get_video_info(video_path):
    """Get video width, height, and duration"""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-show_entries', 'stream=width,height,codec_type',
        '-show_entries', 'format=duration',
        '-of', 'json', video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    width, height = 1920, 1080
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video':
            width = int(stream.get('width', 1920))
            height = int(stream.get('height', 1080))
            break

    duration = float(data.get('format', {}).get('duration', 0))
    return width, height, duration


def generate_thumbnail(video_path, start_time, output_path):
    """Generate a thumbnail from the video at the given timestamp"""
    cmd = [
        'ffmpeg', '-ss', str(start_time + 2),
        '-i', video_path,
        '-vframes', '1',
        '-vf', f'scale=360:-2',
        '-q:v', '4',
        '-y', output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def format_ass_time(seconds):
    """Convert seconds to ASS time format H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass_subtitles(words, clip_start, clip_end, output_path, caption_style=None):
    """
    Generate ASS subtitle file with word-by-word karaoke animation.
    Shows 3-5 words at a time with progressive highlight (TikTok style).
    """
    if caption_style is None:
        caption_style = DEFAULT_CAPTION_STYLE
    style = CAPTION_STYLES.get(caption_style, CAPTION_STYLES[DEFAULT_CAPTION_STYLE])

    # Filter words within this clip's time range
    clip_words = [
        w for w in words
        if w['start'] >= clip_start - 0.3 and w['end'] <= clip_end + 0.3
    ]

    if not clip_words:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("[Script Info]\nScriptType: v4.00+\n")
        return output_path

    tw, th = TARGET_WIDTH, TARGET_HEIGHT
    bold_flag = -1 if style['bold'] else 0

    ass_content = f"""[Script Info]
Title: Opus Pro Captions
ScriptType: v4.00+
PlayResX: {tw}
PlayResY: {th}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font']},{style['fontsize']},{style['primary_color']},{style['highlight_color']},{style['outline_color']},{style['back_color']},{bold_flag},0,0,0,100,100,0,0,1,{style['outline']},{style['shadow']},{style['alignment']},40,40,{style['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Group words into short bursts (2-3 words) for mobile readability
    groups = []
    current_group = []
    for word in clip_words:
        current_group.append(word)
        w_text = word['word'].strip()
        # End group if too many words or punctuation
        if len(current_group) >= 3 or (
            len(current_group) >= 1 and w_text and w_text[-1] in '.!?,;:'
        ):
            groups.append(current_group)
            current_group = []
    if current_group:
        groups.append(current_group)

    # Import power words from config
    from config import POWER_WORDS

    # Generate dialogue lines with karaoke timing
    for group in groups:
        if not group:
            continue

        group_start = group[0]['start'] - clip_start
        group_end = group[-1]['end'] - clip_start

        if group_start < 0:
            group_start = 0

        start_ts = format_ass_time(group_start)
        end_ts = format_ass_time(group_end + 0.4)

        # Build karaoke text
        karaoke_parts = []
        
        for word in group:
            duration_cs = int((word['end'] - word['start']) * 100)
            if duration_cs < 8:
                duration_cs = 8
                
            raw_word = word['word'].strip()
            clean_word = raw_word.lower().strip('.,!?:;"()')
            
            # Aesthetic Casing Logic:
            # - POWER_WORDS -> ALL CAPS + Secondary Color (via \k)
            # - Regular Words -> lowercase for that clean "modern" look
            # - Long words (> 7 chars) -> Sentence Case
            
            if clean_word in POWER_WORDS:
                display_word = raw_word.upper()
                # Optional: Force a specific color for power words even before they are highlighted
                # part = f"{{\\k{duration_cs}}}{{\\c{style['highlight_color']}}}{display_word}{{\\c{style['primary_color']}}} "
                part = f"{{\\k{duration_cs}}}{display_word} "
            elif len(clean_word) > 7:
                display_word = raw_word.capitalize()
                part = f"{{\\k{duration_cs}}}{display_word} "
            else:
                display_word = raw_word.lower()
                part = f"{{\\k{duration_cs}}}{display_word} "
                
            karaoke_parts.append(part)

        text = "".join(karaoke_parts).strip()
        
        # Apply high-end animations: fade + scale-up + subtle position shift
        # \t is the transform tag in ASS. (0,80) means from time 0 to 80ms.
        animation = (
            f"{{\\an{style['alignment']}"
            f"\\fad(60,60)"
            f"\\t(0,100,\\fscx110\\fscy110)"
            f"\\t(100,200,\\fscx100\\fscy100)}}"
        )
        
        ass_content += f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{animation}{text}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    return output_path


def create_clip(video_path, clip_info, words, output_path, clip_index,
                progress_callback=None, caption_style=None, preset="tiktok"):
    """
    Create a single clip with burned-in captions.
    Supports multiple output formats/presets.
    """
    start = clip_info['start_time']
    end = clip_info['end_time']
    duration = end - start

    preset_config = PRESETS.get(preset, PRESETS['tiktok'])
    tw = preset_config['width']
    th = preset_config['height']

    if progress_callback:
        progress_callback(
            f"Creating clip {clip_index + 1}: {clip_info['title']}...",
            72 + clip_index * 4
        )

    # Generate ASS subtitles for this clip
    work_dir = os.path.dirname(output_path)
    ass_path = os.path.join(work_dir, f"subs_{clip_index}.ass")
    generate_ass_subtitles(words, start, end, ass_path, caption_style)

    # Step 2: Intelligent Cropping (Face Tracking)
    from face_processor import tracker
    src_w, src_h, _ = get_video_info(video_path)
    
    # Find the best horizontal center for the 9:16 crop
    try:
        center_x = tracker.find_best_crop_x(video_path, start, end, tw, th)
    except Exception:
        center_x = src_w / 2

    # Calculate crop width for 9:16
    crop_w = int(src_h * (tw / th))
    if crop_w > src_w:
        crop_w = src_w
    
    x_offset = int(center_x - (crop_w / 2))
    # Ensure crop stays within video bounds
    x_offset = max(0, min(x_offset, src_w - crop_w))

    # Escape path for FFmpeg filter (Windows paths need special handling)
    ass_escaped = ass_path.replace('\\', '/').replace(':', '\\:')

    # Progress bar parameters
    pb_h = 12
    pb_color = "0xFFFF00" # Yellow in FFmpeg format (actually depends on filter)
    
    # Step 3: Punch Zoom Logic (Pulse on Power Words)
    from config import POWER_WORDS
    zoom_expr = "1.0"
    for word in words:
        if word['start'] >= start and word['end'] <= end:
            clean_word = word['word'].lower().strip('.,!?:;"()')
            if clean_word in POWER_WORDS:
                # Zoom in 10% during power words
                w_start = word['start'] - start
                w_end = word['end'] - start
                zoom_expr = f"if(between(it,{w_start:.2f},{w_end:.2f}),1.1,{zoom_expr})"

    # Final filter construction
    zoom_filter = f"zoompan=z='{zoom_expr}':d=1:s={tw}x{th}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

    if preset in ("tiktok", "youtube_shorts") and src_w > src_h:
        # Landscape source → vertical output: blurred bg + tracked center + punch zoom
        filter_complex = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},boxblur=25:5[bg];"
            f"[0:v]crop={crop_w}:{src_h}:{x_offset}:0,scale={tw}:{th},{zoom_filter}[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[vid];"
            f"[vid]ass='{ass_escaped}'[with_subs];"
            f"[with_subs]drawbox=y=ih-{pb_h}:w=iw*t/{duration}:h={pb_h}:color=yellow@0.8:t=fill[out]"
        )
    elif preset == "square":
        # Square crop with face tracking + punch zoom
        sq_w = min(src_w, src_h)
        sq_x = int(center_x - (sq_w / 2))
        sq_x = max(0, min(sq_x, src_w - sq_w))
        
        filter_complex = (
            f"[0:v]crop={sq_w}:{sq_w}:{sq_x}:0,scale={tw}:{th},{zoom_filter}[vid];"
            f"[vid]ass='{ass_escaped}'[with_subs];"
            f"[with_subs]drawbox=y=ih-{pb_h}:w=iw*t/{duration}:h={pb_h}:color=yellow@0.8:t=fill[out]"
        )
    else:
        # Standard landscape or matching aspect
        filter_complex = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:black,{zoom_filter}[vid];"
            f"[vid]ass='{ass_escaped}'[with_subs];"
            f"[with_subs]drawbox=y=ih-{pb_h}:w=iw*t/{duration}:h={pb_h}:color=yellow@0.8:t=fill[out]"
        )

    cmd = [
        'ffmpeg',
        '-ss', str(start),
        '-i', video_path,
        '-t', str(duration),
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        '-y',
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg clip creation failed: {result.stderr[-500:]}")

    if progress_callback:
        progress_callback(
            f"Clip {clip_index + 1} created!",
            72 + (clip_index + 1) * 4
        )

    return output_path
