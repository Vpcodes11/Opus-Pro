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
Style: Default,{style['font']},{style['fontsize']},{style['primary_color']},{style['highlight_color']},{style['outline_color']},{style['back_color']},{bold_flag},0,0,0,100,100,0,0,1,{style['outline']},0,{style['alignment']},40,40,{style['margin_v']},1

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

        # Build karaoke text — \k creates punchy word jumps
        karaoke_parts = []
        for word in group:
            duration_cs = int((word['end'] - word['start']) * 100)
            if duration_cs < 8:
                duration_cs = 8
            # \k highlight effect
            karaoke_parts.append(f"{{\\k{duration_cs}}}{word['word']} ")

        text = "".join(karaoke_parts).strip()
        # Add subtle fade and zoom-in for each line
        ass_content += f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{{\\an{style['alignment']}\\fad(80,80)\\t(0,100,\\fscx105\\fscy105)\\t(100,200,\\fscx100\\fscy100)}}{text}\n"

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

    # Escape path for FFmpeg filter (Windows paths need special handling)
    ass_escaped = ass_path.replace('\\', '/').replace(':', '\\:')

    # Get source video dimensions
    src_w, src_h, _ = get_video_info(video_path)
    src_aspect = src_w / src_h
    target_aspect = tw / th

    if preset in ("tiktok", "youtube_shorts") and src_aspect > 1:
        # Landscape source → vertical output: blurred bg + sharp center
        filter_complex = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},boxblur=25:5[bg];"
            f"[0:v]scale={tw}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[vid];"
            f"[vid]ass='{ass_escaped}'[out]"
        )
    elif preset == "square":
        # Square crop with blurred background
        filter_complex = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},boxblur=20:4[bg];"
            f"[0:v]scale={tw}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[vid];"
            f"[vid]ass='{ass_escaped}'[out]"
        )
    else:
        # Landscape or matching aspect
        filter_complex = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:black[vid];"
            f"[vid]ass='{ass_escaped}'[out]"
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
