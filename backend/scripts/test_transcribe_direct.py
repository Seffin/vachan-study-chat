"""
Generate a real WAV file with a tone, then test the transcribe endpoint.
This verifies the backend pipeline independently of the browser's MediaRecorder.
"""
import sys, os, struct, wave, io, asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import math

def generate_wav_bytes(duration_seconds=2, sample_rate=16000, frequency=440):
    """Generate a WAV file in memory with a simple sine wave tone."""
    buf = io.BytesIO()
    num_samples = int(sample_rate * duration_seconds)
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for i in range(num_samples):
            sample = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wf.writeframes(struct.pack('<h', sample))
    return buf.getvalue()


async def test_with_tone():
    """Test 1: Send a pure tone (should return [NO_SPEECH] or empty)."""
    from services.ai_generation import transcribe_audio
    
    wav_data = generate_wav_bytes(duration_seconds=2)
    print(f"Test 1 - Pure tone: Sending {len(wav_data)} bytes ({len(wav_data)/1024:.1f} KB) of audio/wav")
    
    result = await transcribe_audio(wav_data, "audio/wav")
    print(f"Test 1 - Result: '{result}'")
    print(f"Test 1 - {'PASS (no speech detected)' if not result else 'Result returned (may be hallucination)'}")
    print()


async def test_with_speech_simulation():
    """Test 2: Send a text-to-speech generated phrase via Google TTS (if available)."""
    # Use a simple approach: just test that the endpoint accepts and processes audio
    from services.ai_generation import transcribe_audio
    
    # Generate a longer tone with varying frequency (simulating speech-like modulation)
    buf = io.BytesIO()
    sample_rate = 16000
    duration = 3
    num_samples = sample_rate * duration
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(num_samples):
            t = i / sample_rate
            # Modulated signal to simulate speech-like patterns
            freq = 200 + 100 * math.sin(2 * math.pi * 3 * t)
            sample = int(16000 * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack('<h', sample))
    
    modulated_data = buf.getvalue()
    print(f"Test 2 - Modulated tone: Sending {len(modulated_data)} bytes ({len(modulated_data)/1024:.1f} KB)")
    
    result = await transcribe_audio(modulated_data, "audio/wav")
    print(f"Test 2 - Result: '{result}'")
    print()


async def main():
    print("=" * 60)
    print("Backend Transcription Pipeline Test")
    print("=" * 60)
    print()
    
    try:
        await test_with_tone()
    except Exception as e:
        print(f"Test 1 FAILED with error: {e}")
    
    try:
        await test_with_speech_simulation()
    except Exception as e:
        print(f"Test 2 FAILED with error: {e}")
    
    print("=" * 60)
    print("Tests complete.")


asyncio.run(main())
