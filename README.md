# Yoga Session AI Agent

An AI-powered yoga instructor that converts text-based yoga session descriptions into spoken audio with proper timing and pauses. The agent uses Google's Gemini TTS API to generate natural-sounding speech with various voice options.

## Features

- **Text-to-Speech Conversion**: Converts yoga session descriptions to natural speech using Gemini TTS
- **Timed Holds**: Automatically handles pause instructions like `<hold 1 minute>`
- **Voice Selection**: Choose from 30+ different voices (Aoede, Kore, Puck, etc.)
- **Asynchronous Processing**: Pre-processes upcoming segments during holds and audio playback
- **Configurable Buffer**: Adjustable number of segments to process ahead of time

## Setup

### Prerequisites

1. **Google Cloud Project**: You need a Google Cloud project with billing enabled
2. **API Key**: Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/)
3. **Python 3.7+**: Make sure you have Python installed
4. **FFmpeg**: Required for audio playback

### Installation

1. **Install FFmpeg** (macOS):
   ```bash
   brew install ffmpeg
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Enable Google APIs**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the "Generative Language API" for your project
   - Create an API key in "APIs & Services" → "Credentials"

4. **Set up API key**:
   Add to your `~/.bashrc` or `~/.zshrc`:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
   Then reload: `source ~/.bashrc` or `source ~/.zshrc`

## Usage

### Basic Usage
```bash
python yoga_agent.py <session_file.txt>
```

### With Custom Buffer Size
```bash
python yoga_agent.py <session_file.txt> <buffer_size>
```

Example:
```bash
python yoga_agent.py yin_1.txt 3
```

## Session Document Format

Create a text file describing your yoga session. The agent will read this aloud and pause at specified intervals.

### Basic Structure
```
Welcome to your yoga session. Let's begin with some breathing.

Take a deep breath in and slowly exhale.

<hold 30 seconds>

Now move into mountain pose. Stand tall with feet hip-width apart.

<hold 1 minute>

Transition to forward fold. Let your arms hang heavy.

<hold 45 seconds>

Great work! This completes our session.
```

### Hold Instructions

Use the following format for pauses:

- `<hold X seconds>` - Hold for X seconds
- `<hold X second>` - Hold for X seconds (singular)
- `<hold X minutes>` - Hold for X minutes  
- `<hold X minute>` - Hold for X minutes (singular)

Examples:
- `<hold 30 seconds>`
- `<hold 1 minute>`
- `<hold 2 minutes>`
- `<hold 45 seconds>`

### Tips for Writing Sessions

1. **Keep segments concise**: Each narration block should be 1-3 sentences
2. **Use descriptive language**: Help practitioners visualize the poses
3. **Include breathing cues**: Remind students to breathe naturally
4. **Vary hold times**: Mix shorter and longer holds as appropriate
5. **Add transitions**: Guide smoothly between poses

### Example Session Structure

```
# Opening (30-60 seconds of speech)
Welcome and intention setting

<hold 30 seconds>

# Warm-up (multiple short segments)
Gentle movement instructions

<hold 1 minute>

# Main poses (longer holds)
Detailed pose instructions with alignment cues

<hold 2 minutes>

# Transitions
Movement between poses

<hold 45 seconds>

# Closing
Final relaxation and closing thoughts
```

## Voice Options

The agent supports 30+ different voices. Popular choices include:

- **Aoede** - Breezy, natural
- **Kore** - Firm, clear
- **Puck** - Upbeat, energetic
- **Charon** - Informative, steady
- **Fenrir** - Excitable, dynamic

To use a different voice, modify the `voice` parameter in the `gemini_tts()` function.

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure `GEMINI_API_KEY` is set in your environment
2. **Permission Denied**: Enable the Generative Language API in Google Cloud Console
3. **Audio Playback Issues**: Ensure FFmpeg is installed and in your PATH
4. **Import Errors**: Install required packages: `pip install -r requirements.txt`

### Supported Audio Formats

- **Output**: WAV files (24kHz, 16-bit, mono)
- **Playback**: Any format supported by FFmpeg

## Advanced Configuration

### Buffer Size
The buffer size determines how many segments are pre-processed:
- **Default**: 2 segments
- **Larger values**: Smoother playback, more memory usage
- **Smaller values**: Lower memory usage, potential delays

### Custom Voices
See the [Gemini TTS documentation](https://ai.google.dev/gemini-api/docs/speech-generation#voice-options) for the complete list of available voices.

## File Structure

```
yoga/
├── yoga_agent.py          # Main script
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── sessions/             # Yoga session files
    ├── test_session.txt  # Basic example session
    └── yin_1.txt         # Example yin yoga session
```

## License

This project is for educational and personal use. Please respect Google's API usage policies and terms of service.
