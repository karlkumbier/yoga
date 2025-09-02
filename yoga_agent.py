import os
import time
from tempfile import NamedTemporaryFile
import subprocess
from concurrent.futures import ThreadPoolExecutor
from google import genai
from google.genai import types
import wave
import json

# Get Gemini API key from environment variable (set in bashrc)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")

INSTRUCTOR_VOICE = "Speak as a yoga instructor running a relaxing session. Use a soft, gentle voice just above a whisper and without strong emphasis on words"

# Configure the genai client
client = genai.Client(api_key=GEMINI_API_KEY)


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
        time_duration = statement.get('time', 0)
        
        if text.strip():  # If there's text content, it's a narration segment
            segments.append(('narration', text, voice, time_duration))
        else:  # If text is empty, it's a pause/hold segment
            segments.append(('hold', time_duration, voice, time_duration))
    
    return segments

def gemini_tts(text, voice="Algieba"):
    """
    Sends text to Gemini TTS API and returns path to audio file.
    Available voices: Aoede, Kore, Puck, Charon, Fenrir, etc.
    See: https://ai.google.dev/gemini-api/docs/speech-generation#voice-options
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
    
    # Create temporary file and save as WAV (Gemini returns PCM audio data)
    with NamedTemporaryFile(delete=False, suffix=".wav") as f:
        # Set up wave file parameters (from Gemini docs)
        with wave.open(f.name, "wb") as wf:
            wf.setnchannels(1)  # mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(24000)  # 24kHz
            wf.writeframes(audio_data)
        return f.name
    
def process_narration_segment(text, voice_style=INSTRUCTOR_VOICE):
    """
    Process a narration segment by calling the TTS API.
    voice_style: The style instruction for how to speak the text
    Returns the audio file path.
    """
    # Use the voice_style parameter as the instruction prefix
    styled_text = f"{voice_style}: '{text}'"
    return gemini_tts(styled_text)

def play_audio_file(audio_file):
    """
    Play an audio file using ffplay.
    """
    subprocess.run(['ffplay', '-autoexit', '-nodisp', '-loglevel', 'quiet', audio_file], check=True)
    os.remove(audio_file)

def process_completed_futures_and_submit_next(future_to_index, processed_segments, narration_segments, next_to_process, executor):
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
        future = executor.submit(process_narration_segment, next_seg[1], next_seg[2])
        future_to_index[future] = next_seg_idx
        next_to_process += 1
    
    return next_to_process

def run_yoga_session(file_path, buffer_size=2):
    """
    Run the yoga session with asynchronous processing.
    buffer_size: Number of segments to process ahead of playback.
    """
    segments = parse_session(file_path)
    
    # Thread pool for API calls
    executor = ThreadPoolExecutor(max_workers=3)
    
    # Submit initial batch of narration segments for processing
    future_to_index = {}
    narration_segments = [(i, seg) for i, seg in enumerate(segments) if seg[0] == 'narration']
    
    # Start processing first buffer_size segments
    for i, (seg_idx, seg) in enumerate(narration_segments[:buffer_size]):
        if i < len(narration_segments):
            # seg format: ('narration', text, voice, time_duration)
            future = executor.submit(process_narration_segment, seg[1], seg[2])
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
                    future_to_index, processed_segments, narration_segments, next_to_process, executor
                )
                
                if seg_idx not in processed_segments:
                    time.sleep(0.1)  # Small delay before checking again
            
            # Play the processed segment
            audio_file = processed_segments.pop(seg_idx)
            if audio_file:
                play_audio_file(audio_file)
        
        elif seg_type == 'hold':
            print(f'Holding for {content} seconds...')
            
            # Continue processing during hold
            hold_start = time.time()
            while time.time() - hold_start < content:
                next_to_process = process_completed_futures_and_submit_next(
                    future_to_index, processed_segments, narration_segments, next_to_process, executor
                )
                time.sleep(0.1)  # Check every 100ms
    
    # Clean up
    executor.shutdown(wait=True)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print('Usage: python yoga_agent.py <session_file.json> [buffer_size]')
        print('  session_file.json: JSON file containing list of statement dictionaries')
        print('  buffer_size: Number of segments to process ahead (default: 2)')
        exit(1)
    
    file_path = sys.argv[1]
    buffer_size = int(sys.argv[2]) if len(sys.argv) == 3 else 2
    
    print(f'Starting yoga session with buffer size: {buffer_size}')
    run_yoga_session(file_path, buffer_size)