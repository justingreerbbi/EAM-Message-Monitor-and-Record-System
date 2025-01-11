import time
import pyaudio
from rtlsdr import RtlSdr
import numpy as np
from scipy import signal
import soundfile as sf
import datetime

# Configuration
FM_BANDWIDTH = 200000  # Bandwidth for FM signals in Hz
SAMPLE_RATE = 2400000  # Sample rate of the SDR in Hz
DECIMATION = 10  # Decimation factor to reduce the sample rate after filtering
FREQUENCY_EAS = 162.4e6  # Example frequency for NOAA Weather Radio where EAS might be broadcast in MHz
GAIN = 'auto'  # Gain setting for the SDR
SQUELCH_THRESHOLD = 4.0  # Squelch threshold for silence
AUDIO_THRESHOLD = 0.02  # Threshold to trigger recording (adjust based on your environment)
CHUNK = 1024  # Size of chunks for streaming audio

# Initialize the SDR
sdr = RtlSdr()
sdr.sample_rate = SAMPLE_RATE
sdr.center_freq = FREQUENCY_EAS
sdr.gain = GAIN

# Design a filter for FM demodulation
taps = signal.firwin(101, FM_BANDWIDTH/(SAMPLE_RATE/2), window=('kaiser', 8))
decimated_rate = SAMPLE_RATE // DECIMATION

# Function to demodulate FM
def fm_demodulate(samples):
    samples = samples - np.mean(samples)
    phase = np.unwrap(np.angle(samples))
    return np.diff(phase) * (SAMPLE_RATE / (2 * np.pi))

# Initialize PyAudio for audio playback
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=decimated_rate,
                output=True)

# Main loop to monitor, record, and stream EAS messages
recording = False
while True:
    try:
        # Read samples from SDR
        samples = sdr.read_samples(256 * 1024)
        
        # Demodulate FM
        demodulated = fm_demodulate(samples)
        
        # Apply filter and decimation
        filtered = signal.lfilter(taps, 1.0, demodulated)
        decimated = filtered[::DECIMATION]
        
        # Check for signal strength for squelch and recording
        signal_power = np.mean(np.abs(decimated))
        
        # Apply squelch - only process audio if above squelch threshold
        if signal_power > SQUELCH_THRESHOLD:
            # Stream audio live
            audio_data = decimated.astype(np.float32)
            stream.write(audio_data.tobytes())
            
            # Check if we should start recording
            if signal_power > AUDIO_THRESHOLD and not recording:
                recording = True
                start_time = datetime.datetime.now()
                print(f"Recording started at {start_time}")
            
            if recording:
                if not 'recording_data' in locals():
                    recording_data = []
                recording_data.extend(decimated)

        else:
            # Stop recording if below threshold
            if recording:
                recording = False
                now = datetime.datetime.now()
                filename = f"eas_{start_time.strftime('%Y%m%d_%H%M%S')}_{FREQUENCY_EAS/1e6:.2f}MHz.wav"
                sf.write(filename, np.array(recording_data), decimated_rate, subtype='PCM_16')
                print(f"Emergency Alert recorded from {start_time} to {now}. File saved as {filename}")
                del recording_data  # Clear the buffer after saving
            
            # Squelch: Stream silence
            silence = np.zeros(CHUNK, dtype=np.float32)
            stream.write(silence.tobytes())
        
        time.sleep(0.01)  # Small delay to not overload the system

    except KeyboardInterrupt:
        print("Stopping the script...")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
        break

# Cleanup
stream.stop_stream()
stream.close()
p.terminate()
sdr.close()