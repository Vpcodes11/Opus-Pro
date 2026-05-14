# Opus Pro — AI Podcast to Viral Clips ⚡

Opus Pro (Open Source) is a high-performance alternative to commercial clipping tools. It uses AI to automatically identify the most viral moments from long-form podcasts and transforms them into 9:16 vertical clips with animated, karaoke-style captions.

![Opus Pro Preview](https://via.placeholder.com/1200x600/09090b/f4f4f5?text=Opus+Pro+—+AI+Viral+Clipper)

## ✨ Features

- **🎯 AI Viral Detection**: Uses LLaMA-3 (via Groq) to analyze transcripts and find high-retention "hooks".
- **🎬 Professional Rendering**: Automated FFmpeg pipeline for 9:16 vertical cropping with blurred backgrounds.
- **🎤 Animated Captions**: Word-by-word karaoke highlighting (TikTok style) with premium typography.
- **🌐 Universal Support**: Import videos via local upload or URLs (YouTube, Twitch, X/Twitter, etc.).
- **⚡ Ultra Fast**: Powered by Groq's lightning-fast inference for transcription and analysis.
- **💎 Premium UI**: Modern, glassmorphic dark-mode interface with real-time WebSocket progress tracking.

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **FFmpeg**: Must be installed and available in your PATH.
- **Groq API Key**: Get one for free at [console.groq.com](https://console.groq.com).
- **Recommended Fonts**: For the best aesthetic results, install these fonts:
    - [The Bold Font](https://www.dafont.com/the-bold-font.font) (Used for Viral style)
    - [Montserrat](https://fonts.google.com/specimen/Montserrat) (Used for Bold Impact)
    - [Outfit](https://fonts.google.com/specimen/Outfit) (Used for Neon Pulse)
    - [Komika Axis](https://www.dafont.com/komika-axis.font) (Used for Karaoke)
    - [Inter](https://fonts.google.com/specimen/Inter) (Used for TikTok/Minimal)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Vpcodes11/Opus-Pro.git
   cd Opus-Pro
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

### Running the App

```bash
python -m uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## 🛠️ Technology Stack

- **Backend**: FastAPI, Uvicorn, FFmpeg
- **AI Brain**: OpenAI API (compatible), Groq LLaMA-3, Whisper
- **Frontend**: Vanilla JS, HTML5, CSS3 (Glassmorphism)
- **Downloader**: yt-dlp

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).
