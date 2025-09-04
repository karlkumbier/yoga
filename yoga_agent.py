import os
import time
from tempfile import NamedTemporaryFile
import subprocess
from concurrent.futures import ThreadPoolExecutor
from google import genai
from google.genai import types
import wave
import json
import re
import argparse

# Get Gemini API key from environment variable (set in bashrc)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")

INSTRUCTOR_VOICE = "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words"

# Configure the genai client
client = genai.Client(api_key=GEMINI_API_KEY)


def parse_time_string(time_str):
    """
    Parse a time string into seconds.
    Supports formats like: "5 seconds", "2 minutes", "1 minute", "30 seconds"
    Returns the number of seconds as an integer.
    """
    if isinstance(time_str, (int, float)):
        return int(time_str)  # Already numeric
    
    if not isinstance(time_str, str):
        return 0
    
    # Extract number and unit using regex
    match = re.match(r'(\d+)\s*(second|seconds|minute|minutes)', time_str.lower().strip())
    if not match:
        # Try to extract just a number if no unit is specified
        number_match = re.match(r'(\d+)', time_str.strip())
        if number_match:
            return int(number_match.group(1))  # Assume seconds if no unit
        return 0
    
    number = int(match.group(1))
    unit = match.group(2)
    
    if 'minute' in unit:
        return number * 60
    else:  # seconds
        return number


def parse_session(file_path):
    """
    Loads the session from a JSON file containing a list of statement dictionaries.
    Each statement should have keys: voice, text, time.
    Returns a list of (type, content, voice, time) tuples.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        statements = json.load(f)
    
    segments = []
    for statement in statements:
        voice = statement.get('voice', INSTRUCTOR_VOICE)
        text = statement.get('text', '')
        time_str = statement.get('time', 0)
        time_duration = parse_time_string(time_str)
        
        if text.strip():  # If there's text content, it's a narration segment
            segments.append(('narration', text, voice, time_duration))
        else:  # If text is empty, it's a pause/hold segment
            segments.append(('hold', time_duration, voice, time_duration))
    
    return segments

def gemini_tts(text, voice="Callirrhoe", save_path=None):
    """
    Sends text to Gemini TTS API and returns path to audio file.
    Available voices: Aoede, Callirrhoe, Puck, Charon, Fenrir, etc.
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

def process_narration_segment(text, voice_style=INSTRUCTOR_VOICE, save_path=None):
    """
    Process a narration segment by calling the TTS API.
    voice_style: The style instruction for how to speak the text
    save_path: If provided, save the audio file to this path
    Returns the audio file path.
    """
    # Use the voice_style parameter as the instruction prefix
    styled_text = f"{voice_style}: '{text}'"
    return gemini_tts(styled_text, save_path=save_path)

def play_audio_file(audio_file, delete_after=True):
    """
    Play an audio file using ffplay.
    Args:
        audio_file: Path to the audio file
        delete_after: Whether to delete the file after playing (default: True)
    """
    subprocess.run(['ffplay', '-autoexit', '-nodisp', '-loglevel', 'quiet', audio_file], check=True)
    if delete_after:
        os.remove(audio_file)

def process_completed_futures_and_submit_next(future_to_index, processed_segments, narration_segments, next_to_process, executor, output_dir=None):
    """
    Helper function to process completed futures and submit next segment for processing.
    Returns updated next_to_process value.
    """
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
        # next_seg format: ('narration', text, voice, time_duration)
        
        # Generate save path if output_dir is specified
        save_path = None
        if output_dir:
            save_path = os.path.join(output_dir, f"seg_{next_seg_idx}.wav")
        
        future = executor.submit(process_narration_segment, next_seg[1], next_seg[2], save_path)
        future_to_index[future] = next_seg_idx
        next_to_process += 1
    
    return next_to_process

def run_yoga_session(file_path, buffer_size=2, output_dir=None):
    """
    Run the yoga session with asynchronous processing.
    buffer_size: Number of segments to process ahead of playback.
    output_dir: If provided, save audio files to this directory as seg_0.wav, seg_1.wav, etc.
    """
    segments = parse_session(file_path)
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Thread pool for API calls
    executor = ThreadPoolExecutor(max_workers=3)
    
    # Submit initial batch of narration segments for processing
    future_to_index = {}
    narration_segments = [
        (i, seg) for i, seg in enumerate(segments) if seg[0] == 'narration'
    ]
    
    # Start processing first buffer_size segments
    for i, (seg_idx, seg) in enumerate(narration_segments[:buffer_size]):
        if i < len(narration_segments):
            # seg format: ('narration', text, voice, time_duration)
            save_path = None
            if output_dir:
                save_path = os.path.join(output_dir, f"seg_{seg_idx}.wav")
            future = executor.submit(process_narration_segment, seg[1], seg[2], save_path)
            future_to_index[future] = seg_idx
    
    processed_segments = {}
    next_to_process = buffer_size
    
    # Main playback loop
    for seg_idx, segment in enumerate(segments):
        seg_type, content, voice, _ = segment  # _ for unused time_duration
        
        if seg_type == 'narration':
            print(f'Narrating ({voice}): {content}')
            
            # Wait for this segment to be processed
            while seg_idx not in processed_segments:
                next_to_process = process_completed_futures_and_submit_next(
                    future_to_index, processed_segments, narration_segments, next_to_process, executor, output_dir
                )
                
                if seg_idx not in processed_segments:
                    time.sleep(0.1)  # Small delay before checking again
            
            # Play the processed segment
            audio_file = processed_segments.pop(seg_idx)
            if audio_file:
                # Don't delete files if they were saved to output_dir
                delete_after = output_dir is None
                play_audio_file(audio_file, delete_after)
        
        elif seg_type == 'hold':
            print(f'Holding for {content} seconds...')
            
            # Continue processing during hold
            hold_start = time.time()
            while time.time() - hold_start < content:
                next_to_process = process_completed_futures_and_submit_next(
                    future_to_index, processed_segments, narration_segments, next_to_process, executor, output_dir
                )
                time.sleep(0.1)  # Check every 100ms
    
    # Clean up
    executor.shutdown(wait=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='AI-powered yoga instructor that converts JSON session files to spoken audio with timing.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python yoga_agent.py session.json
  python yoga_agent.py session.json --buffer-size 3
  python yoga_agent.py session.json --output-dir ./audio_files
  python yoga_agent.py session.json --buffer-size 4 --output-dir ./session_audio
        """
    )
    
    parser.add_argument(
        'session_file',
        help='JSON file containing list of statement dictionaries with voice, text, and time keys'
    )
    
    parser.add_argument(
        '--buffer-size', '-b',
        type=int,
        default=2,
        help='Number of segments to process ahead of playback (default: 2)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Directory to save audio files as seg_0.wav, seg_1.wav, etc. If not specified, temporary files are used and deleted after playback'
    )
    
    args = parser.parse_args()
    
    if args.output_dir:
        print(f'Starting yoga session with buffer size: {args.buffer_size}, saving audio to: {args.output_dir}')
    else:
        print(f'Starting yoga session with buffer size: {args.buffer_size}')
    
    run_yoga_session(args.session_file, args.buffer_size, args.output_dir)