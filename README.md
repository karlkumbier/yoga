# Yoga Session AI Agent

An AI-powered yoga instructor that converts JSON-based yoga session descriptions into spoken audio with proper timing and pauses. The agent uses Google's Gemini TTS API to generate natural-sounding speech with various voice options.

## Features

- **Text-to-Speech Conversion**: Converts yoga session descriptions to natural speech using Gemini TTS
- **Structured Sessions**: Uses JSON format for precise control of voice, text, and timing
- **Voice Selection**: Choose from 30+ different voices (Aoede, Kore, Puck, etc.) per statement
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
python yoga_agent.py <session_file.json>
```

### With Custom Buffer Size
```bash
python yoga_agent.py <session_file.json> <buffer_size>
```

Example:
```bash
python yoga_agent.py sessions/example_session.json 3
```

## Session Document Format

Create a JSON file describing your yoga session. The agent will read statements aloud and pause at specified intervals.

### JSON Structure

Each session is a JSON array of statement objects. Each statement must have these keys:

- **`voice`**: Voice style instruction (e.g., "Speak as a yoga instructor...") or empty string for pauses
- **`text`**: The words to speak, or empty string for pauses
- **`time`**: Duration in seconds for the statement

The `voice` field contains instructions for how the text should be spoken, not the name of a specific voice. The system uses a default voice (Algieba) but applies the style instructions from this field.

### Basic Example
```json
[
    {
        "voice": "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words",
        "text": "Welcome to your yoga session. Let's begin with some breathing.",
        "time": 5
    },
    {
        "voice": "Speak as a yoga instructor running a relaxing session. Use a calm, encouraging tone with clear guidance", 
        "text": "Take a deep breath in and slowly exhale.",
        "time": 4
    },
    {
        "voice": "",
        "text": "",
        "time": 30
    },
    {
        "voice": "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words",
        "text": "Now move into mountain pose. Stand tall with feet hip-width apart.",
        "time": 6
    }
]
```

### Pause/Hold Statements

To create pauses between spoken instructions, use empty text:

```json
{
    "voice": "",
    "text": "",
    "time": 120
}
```

This creates a 2-minute pause without any speech.

### Tips for Writing Sessions

1. **Keep segments concise**: Each text block should be 1-3 sentences
2. **Use descriptive language**: Help practitioners visualize the poses
3. **Include breathing cues**: Remind students to breathe naturally
4. **Vary hold times**: Mix shorter and longer pauses as appropriate
5. **Add transitions**: Guide smoothly between poses
6. **Customize voice styles**: You can use different voice instructions for variety or emphasis

### Example Session Structure

```json
[
    {
        "voice": "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words",
        "text": "Welcome to today's yin yoga session. Find your comfortable seated position.",
        "time": 5
    },
    {
        "voice": "",
        "text": "",
        "time": 30
    },
    {
        "voice": "Speak as a yoga instructor running a relaxing session. Use a calm, encouraging tone with clear guidance",
        "text": "Begin to fold forward from your hips, letting your spine round naturally.",
        "time": 7
    },
    {
        "voice": "",
        "text": "",
        "time": 180
    },
    {
        "voice": "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words",
        "text": "Slowly begin to roll up, vertebra by vertebra.",
        "time": 5
    }
]
```

## Voice Style Options

The `voice` field in your JSON statements contains instructions for how the text should be spoken. You can customize these instructions to create different moods or emphasis. Some examples:

- **Default gentle style**: "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words"
- **Encouraging guidance**: "Speak as a yoga instructor running a relaxing session. Use a calm, encouraging tone with clear guidance" 
- **Meditative style**: "Speak as a yoga instructor in a meditative session. Use a very slow, peaceful voice with long pauses between words"
- **Energizing style**: "Speak as a yoga instructor leading an energizing session. Use a warm, motivating tone with gentle enthusiasm"

## Voice Options

The system uses Google's Gemini TTS with the Algieba voice by default. However, you can control the speaking style through the `voice` field in your JSON statements, which contains instructions for tone, pace, and emphasis.

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
├── yoga_agent.py              # Main script
├── requirements.txt           # Python dependencies
├── README.md                 # This file
└── sessions/                 # Yoga session files
    ├── example_session.json  # Basic example session (JSON format)
    ├── test_session.txt      # Legacy text format (deprecated)
    └── yin_1.txt             # Legacy yin yoga session (deprecated)
```

## License

This project is for educational and personal use. Please respect Google's API usage policies and terms of service.
