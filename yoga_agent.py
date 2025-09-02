import os
import re
import time
import requests
from tempfile import NamedTemporaryFile
import subprocess
import base64
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from google import genai
from google.genai import types
import wave

# Get Gemini API key from environment variable (set in bashrc)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")

# Configure the genai client
client = genai.Client(api_key=GEMINI_API_KEY)


# Regex to match <hold X minute(s)/second(s)>
HOLD_PATTERN = re.compile(r'<hold (\d+) (second|minute|minutes|seconds)>', re.IGNORECASE)

STYLE = "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words: "

def parse_session(text):
    """
    Splits the session into narration and hold segments.
    Returns a list of (type, content) tuples.
    """
    segments = []
    pos = 0
    for match in HOLD_PATTERN.finditer(text):
        start, end = match.span()
        if start > pos:
            segments.append(('narration', f"{STYLE}'{text[pos:start].strip()}'"))
        duration = int(match.group(1))
        unit = match.group(2).lower()
        if 'minute' in unit:
            seconds = duration * 60
        else:
            seconds = duration
        segments.append(('hold', seconds))
        pos = end
    if pos < len(text):
        segments.append(('narration', f"{STYLE}'{text[pos:].strip()}'"))
    return [seg for seg in segments if seg[1]]

def gemini_tts(text, voice="Algieba", save_path=None):
    """
    Sends text to Gemini TTS API and returns path to audio file.
    Available voices: Aoede, Kore, Puck, Charon, Fenrir, etc.
    See: https://ai.google.dev/gemini-api/docs/speech-generation#voice-options
    
    Args:
        text: Text to convert to speech
        voice: Voice name to use
        save_path: If provided, save to this path instead of temporary file
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    )
                )
            ),
        )
    )
    
    # Get the audio data
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    
    # Use provided path or create temporary file
    if save_path:
        file_path = save_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    else:
        with NamedTemporaryFile(delete=False, suffix=".wav") as f:
            file_path = f.name
    
    # Set up wave file parameters (from Gemini docs)
    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(1)  # mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(24000)  # 24kHz
        wf.writeframes(audio_data)
    return file_path
    
def process_narration_segment(text, voice="Aoede", save_path=None):
    """
    Process a narration segment by calling the TTS API.
    Returns the audio file path.
    
    Args:
        text: Text to convert to speech
        voice: Voice name to use
        save_path: If provided, save to this path instead of temporary file
    """
    return gemini_tts(text, voice, save_path)

def play_audio_file(audio_file, delete_after=True):
    """
    Play an audio file using ffplay.
    
    Args:
        audio_file: Path to audio file
        delete_after: Whether to delete the file after playing (for temp files)
    """
    subprocess.run(['ffplay', '-autoexit', '-nodisp', '-loglevel', 'quiet', audio_file], check=True)
    if delete_after:
        os.remove(audio_file)

def generate_session_audio(session_file, voice="Algieba"):
    """
    Generate and save all audio files for a session.
    
    Args:
        session_file: Path to the session text file (e.g., "sessions/yin_1.txt")
        voice: Voice to use for generation
    
    Returns:
        audio_dir: Directory where audio files were saved
    """
    # Extract session name from file path
    session_name = os.path.splitext(os.path.basename(session_file))[0]
    audio_dir = f"sessions/audio/{session_name}"
    
    # Parse the session
    with open(session_file, 'r', encoding='utf-8') as f:
        session_text = f.read()
    
    segments = parse_session(session_text)
    
    # Create audio directory
    os.makedirs(audio_dir, exist_ok=True)
    
    # Generate audio for each narration segment
    narration_count = 0
    segment_info = []
    
    for i, (seg_type, content) in enumerate(segments):
        if seg_type == 'narration':
            audio_file = f"{audio_dir}/segment_{narration_count:03d}.wav"
            print(f"Generating audio for segment {narration_count}: {content[:50]}...")
            process_narration_segment(content, voice, audio_file)
            segment_info.append(('narration', audio_file))
            narration_count += 1
        else:  # hold
            segment_info.append(('hold', content))
    
    # Save segment info for playback
    info_file = f"{audio_dir}/segments.txt"
    with open(info_file, 'w', encoding='utf-8') as f:
        for seg_type, content in segment_info:
            if seg_type == 'narration':
                f.write(f"narration:{content}\n")
            else:
                f.write(f"hold:{content}\n")
    
    print(f"Audio files saved to: {audio_dir}")
    return audio_dir

def play_session_audio(audio_dir):
    """
    Play a pre-generated audio session from the audio directory.
    
    Args:
        audio_dir: Directory containing the audio files and segments.txt
    """
    segments_file = f"{audio_dir}/segments.txt"
    
    if not os.path.exists(segments_file):
        raise FileNotFoundError(f"Segments file not found: {segments_file}")
    
    # Load segment information
    segments = []
    with open(segments_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('narration:'):
                audio_file = line[10:]  # Remove 'narration:' prefix
                segments.append(('narration', audio_file))
            elif line.startswith('hold:'):
                hold_time = float(line[5:])  # Remove 'hold:' prefix
                segments.append(('hold', hold_time))
    
    # Play the session
    for seg_type, content in segments:
        if seg_type == 'narration':
            print(f'Playing: {os.path.basename(content)}')
            play_audio_file(content, delete_after=False)  # Don't delete saved files
        elif seg_type == 'hold':
            print(f'Holding for {content} seconds...')
            time.sleep(content)

def run_yoga_session(file_path, buffer_size=2):
    """
    Run the yoga session with asynchronous processing.
    buffer_size: Number of segments to process ahead of playback.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        session_text = f.read()
    
    segments = parse_session(session_text)
    processed_queue = Queue()
    
    # Thread pool for API calls
    executor = ThreadPoolExecutor(max_workers=3)
    
    # Submit initial batch of narration segments for processing
    future_to_index = {}
    segment_index = 0
    narration_segments = [(i, seg) for i, seg in enumerate(segments) if seg[0] == 'narration']
    
    # Start processing first buffer_size segments
    for i, (seg_idx, seg) in enumerate(narration_segments[:buffer_size]):
        if i < len(narration_segments):
            future = executor.submit(process_narration_segment, seg[1])
            future_to_index[future] = seg_idx
    
    processed_segments = {}
    next_to_process = buffer_size
    
    # Main playback loop
    for seg_idx, (seg_type, content) in enumerate(segments):
        if seg_type == 'narration':
            print(f'Narrating: {content}')
            
            # Wait for this segment to be processed
            while seg_idx not in processed_segments:
                # Check for completed futures
                completed_futures = [f for f in future_to_index.keys() if f.done()]
                for future in completed_futures:
                    result_seg_idx = future_to_index.pop(future)
                    try:
                        audio_file = future.result()
                        processed_segments[result_seg_idx] = audio_file
                    except Exception as e:
                        print(f'Error processing segment {result_seg_idx}: {e}')
                        processed_segments[result_seg_idx] = None
                
                # Submit next segment for processing if available
                if next_to_process < len(narration_segments):
                    next_seg_idx, next_seg = narration_segments[next_to_process]
                    future = executor.submit(process_narration_segment, next_seg[1])
                    future_to_index[future] = next_seg_idx
                    next_to_process += 1
                
                if seg_idx not in processed_segments:
                    time.sleep(0.1)  # Small delay before checking again
            
            # Play the processed segment
            audio_file = processed_segments.pop(seg_idx)
            if audio_file:
                play_audio_file(audio_file, delete_after=True)  # Delete temp files
        
        elif seg_type == 'hold':
            print(f'Holding for {content} seconds...')
            
            # Continue processing during hold
            hold_start = time.time()
            while time.time() - hold_start < content:
                # Check for completed futures during hold
                completed_futures = [f for f in future_to_index.keys() if f.done()]
                for future in completed_futures:
                    result_seg_idx = future_to_index.pop(future)
                    try:
                        audio_file = future.result()
                        processed_segments[result_seg_idx] = audio_file
                    except Exception as e:
                        print(f'Error processing segment {result_seg_idx}: {e}')
                        processed_segments[result_seg_idx] = None
                
                # Submit next segment for processing if available
                if next_to_process < len(narration_segments):
                    next_seg_idx, next_seg = narration_segments[next_to_process]
                    future = executor.submit(process_narration_segment, next_seg[1])
                    future_to_index[future] = next_seg_idx
                    next_to_process += 1
                
                time.sleep(0.1)  # Check every 100ms
    
    # Clean up
    executor.shutdown(wait=True)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print('Usage:')
        print('  Auto mode:         python yoga_agent.py <session_file.txt> [buffer_size]')
        print('  Play existing:     python yoga_agent.py <audio_directory>')
        print('  Generate only:     python yoga_agent.py <session_file.txt> --generate-only [voice]')
        print('  Force regenerate:  python yoga_agent.py <session_file.txt> --regenerate [voice]')
        print('')
        print('Arguments:')
        print('  session_file.txt: Path to session text file (e.g., sessions/yin_1.txt)')
        print('  audio_directory:  Path to directory with pre-generated audio')
        print('  buffer_size:      Number of segments to process ahead (default: 2)')
        print('  voice:           Voice to use for generation (default: Algieba)')
        print('')
        print('Auto mode: Automatically uses existing audio if available, otherwise generates it')
        exit(1)
    
    input_path = sys.argv[1]
    
    # Check if input is a directory (pre-generated audio) or text file
    if os.path.isdir(input_path):
        # Play pre-generated audio session
        print(f'Playing pre-generated session from: {input_path}')
        play_session_audio(input_path)
    
    elif input_path.endswith('.txt'):
        # Extract session name and check for existing audio
        session_name = os.path.splitext(os.path.basename(input_path))[0]
        audio_dir = f"sessions/audio/{session_name}"
        
        # Handle special flags
        if len(sys.argv) >= 3 and sys.argv[2] == '--generate-only':
            # Generate audio files only
            voice = sys.argv[3] if len(sys.argv) >= 4 else "Algieba"
            print(f'Generating audio for session: {input_path} with voice: {voice}')
            audio_dir = generate_session_audio(input_path, voice)
            print(f'Audio generation complete. To play: python yoga_agent.py {audio_dir}')
        
        elif len(sys.argv) >= 3 and sys.argv[2] == '--regenerate':
            # Force regeneration of audio files
            voice = sys.argv[3] if len(sys.argv) >= 4 else "Algieba"
            print(f'Regenerating audio for session: {input_path} with voice: {voice}')
            # Remove existing audio directory if it exists
            if os.path.exists(audio_dir):
                import shutil
                shutil.rmtree(audio_dir)
            audio_dir = generate_session_audio(input_path, voice)
            print('Playing generated session...')
            play_session_audio(audio_dir)
        
        else:
            # Auto mode - check if audio exists, otherwise generate
            buffer_size = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2].isdigit() else 2
            
            if os.path.exists(audio_dir) and os.path.exists(f"{audio_dir}/segments.txt"):
                # Pre-generated audio exists, use it
                print(f'Found existing audio for {session_name}, playing...')
                play_session_audio(audio_dir)
            else:
                # No existing audio, generate it first
                print(f'No existing audio found for {session_name}, generating...')
                audio_dir = generate_session_audio(input_path)
                print('Playing generated session...')
                play_session_audio(audio_dir)
    
    else:
        print(f'Error: Invalid input path. Must be a .txt file or audio directory.')
        exit(1)
