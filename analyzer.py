"""Viral clip detection — supports OpenAI GPT and Groq LLaMA"""
import json
from openai import OpenAI

# Provider configs for LLM
LLM_PROVIDERS = {
    'openai': {
        'base_url': None,
        'model': 'gpt-4o-mini',
    },
    'groq': {
        'base_url': 'https://api.groq.com/openai/v1',
        'model': 'llama-3.1-8b-instant', # More stable rate limits than 70b
    }
}

SYSTEM_PROMPT = """You are a world-class Viral Content Strategist and Video Editor for high-profile podcasts (Joe Rogan, Diary of a CEO, Alex Hormozi style).

Your task is to analyze the podcast transcript and extract the absolute BEST moments that will explode on social media (TikTok, Reels, Shorts).

CRITICAL DIRECTIVES:
1. THE HOOK IS EVERYTHING: Prioritize moments that start with a "Pattern Interrupt" — a shocking statement, a deep question, a counter-intuitive fact, or high-emotion energy.
2. RETENTION FOCUSED: Clips should maintain high tension or high value throughout. No "dead air" or slow build-ups.
3. COMPLETENESS: A clip must be a self-contained story or point. It must have a setup, a middle (climax/insight), and a satisfying resolution or "loopable" ending.
4. AGGRESSIVE SELECTION: Do not pick boring segments. If only 3 moments are truly viral, only pick 3. If the whole thing is gold, pick up to 8.

SELECTION CRITERIA:
- CONTROVERSY: Hot takes that people will argue about in the comments.
- EMOTION: Moments of raw vulnerability, extreme joy, or intense passion.
- VALUE: "Aha!" moments where the listener learns something life-changing in 60 seconds.
- HUMOR: Genuine laugh-out-loud moments or sharp wit.
- CLIFFHANGERS: Moments that make people want to watch the full episode.

OUTPUT REQUIREMENTS:
- Duration: 30-75 seconds is the "sweet spot" for virality.
- Timing: Ensure start_time and end_time are extremely precise based on the transcript.
- JSON: Return ONLY valid JSON in the specified format.

JSON FORMAT:
{
    "clips": [
        {
            "title": "CATCHY VIRAL TITLE",
            "hook_caption": "RETENTION HOOK (Text that would be the first thing people see)",
            "start_time": 00.0,
            "end_time": 00.0,
            "virality_score": 9.8,
            "reason": "Why this specific moment will trigger the algorithm",
            "category": "hot_take",
            "hashtags": ["#viral", "#podcast", "#hook"]
        }
    ]
}"""


def analyze_transcript(transcript_data, api_key, progress_callback=None, provider='groq'):
    """Send transcript to LLM to find viral-worthy moments"""
    config = LLM_PROVIDERS.get(provider, LLM_PROVIDERS['groq'])

    kwargs = {'api_key': api_key}
    if config['base_url']:
        kwargs['base_url'] = config['base_url']
    client = OpenAI(**kwargs)

    if progress_callback:
        progress_callback("Analyzing transcript for viral moments...", 58)

    # Group segments into chunks to avoid token limits
    MAX_WORDS_PER_CHUNK = 1000  # approx 1300 tokens
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for seg in transcript_data['segments']:
        words_in_seg = len(seg.get('text', '').split())
        if current_word_count + words_in_seg > MAX_WORDS_PER_CHUNK and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [seg]
            current_word_count = words_in_seg
        else:
            current_chunk.append(seg)
            current_word_count += words_in_seg
            
    if current_chunk:
        chunks.append(current_chunk)

    all_clips = []
    total_chunks = len(chunks)
    
    if progress_callback:
        progress_callback(f"AI is finding viral moments across {total_chunks} parts...", 60)
        
    for i, chunk in enumerate(chunks):
        segments_text = "\n".join([
            f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}"
            for seg in chunk
        ])
        
        user_prompt = f"""Here is a section of the podcast transcript with timestamps:

{segments_text}

Identify the top 1-3 most viral-worthy moments in this section. Each clip should be 30-90 seconds.
Return ONLY valid JSON."""

        create_kwargs = {
            'model': config['model'],
            'messages': [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 1000,
            'response_format': {"type": "json_object"}
        }
        
        try:
            response = client.chat.completions.create(**create_kwargs)
            result = json.loads(response.choices[0].message.content)
            all_clips.extend(result.get('clips', []))
        except Exception as e:
            print(f"Error analyzing chunk {i+1}: {e}")
            
        if progress_callback:
            pct = 60 + int(((i + 1) / total_chunks) * 10)
            progress_callback(f"Analyzed part {i+1} of {total_chunks}...", pct)

    # Sort and take top ones
    all_clips.sort(key=lambda x: x.get('virality_score', 0), reverse=True)
    top_clips = all_clips[:8]

    if progress_callback:
        progress_callback(f"Found {len(top_clips)} viral moments!", 70)

    return top_clips
