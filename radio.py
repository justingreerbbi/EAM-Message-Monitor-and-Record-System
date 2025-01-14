import asyncio
import pyaudio
from rtlsdr import RtlSdr
from decoder import Decoder
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class Radio:

    # RTL-SDR settings
    SAMPLE_RATE = 1140000  	# Sample rate
    SAMPLE_SIZE = 51200  	# Samples to capture
    OFFSET = 250000  		# Offset to capture at
    GAIN = 'auto'

    # Audio settings
    AUDIO_SAMPLE = 44100  	# Audio sample rate (Hz)
    AUDIO_CHANNELS = 1  	# Mono audio
    AUDIO_FORMAT = pyaudio.paInt16

    # Frequency Settings
    center_frequency = 94.95e6  # FM Radio

    def __init__(self):
        self.receiver = None
        self.pyaudio = None
        self.stream = None
        self.loop = asyncio.get_event_loop()
        self.sample_rate = Radio.SAMPLE_RATE
        self.sample_size = Radio.SAMPLE_SIZE
        self.gain = Radio.GAIN
        self.offset = Radio.OFFSET
        self.decoder = Decoder()
        self.audio_levels = []

    def setup_receiver(self):
        center_frequency = self.center_frequency - self.offset
        self.sdr = RtlSdr()
        self.sdr.center_freq = center_frequency
        self.sdr.sample_rate = self.sample_rate
        self.sdr.gain = self.gain

    def setup_playback(self):
        self.pyaudio = pyaudio.PyAudio()
        self.stream = self.pyaudio.open(
            format=Radio.AUDIO_FORMAT,
            channels=Radio.AUDIO_CHANNELS,
            rate=Radio.AUDIO_SAMPLE,
            output=True
        )

    def play(self):
        try:
            self.loop.run_until_complete(self.streaming())
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            self.stop()

    async def streaming(self):
        self.setup_receiver()
        self.setup_playback()
        fig, ax = plt.subplots()
        ax.set_title("Real-Time Audio Levels")
        ax.set_xlabel("Time")
        ax.set_ylabel("RMS")
        line, = ax.plot([], [], lw=2)
        ax.set_ylim(0, 0.1)  # Adjust based on expected RMS range
        ax.set_xlim(0, 100)  # Display last 100 frames

        def update(frame):
            if self.audio_levels:
                line.set_data(range(len(self.audio_levels)), self.audio_levels)
                ax.set_xlim(max(0, len(self.audio_levels) - 100), len(self.audio_levels))
            return line,

        ani = FuncAnimation(fig, update, interval=50)

        try:
            async for samples in self.sdr.stream(self.sample_size):
                data = self.decoder.decode(samples, self.sample_rate, self.offset)
                self.stream.write(data.tobytes())
                rms = np.sqrt(np.mean(np.square(data)))
                if not isinstance(rms, (int, float)):
                    print(f"Invalid RMS value: {rms}")
                    continue
                self.audio_levels.append(rms)
                if len(self.audio_levels) > 100:
                    self.audio_levels.pop(0)
        except Exception as e:
            print(f"An error occurred during streaming: {e}")
        finally:
            await self.stop_sdr()

        plt.show()

    async def stop_sdr(self):
        if self.sdr:
            try:
                await self.sdr.stop()
            except Exception as e:
                print("An error occurred while stopping the SDR")
            self.sdr.close()
            self.sdr = None

    def stop(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"An error occurred while stopping audio playback: {e}")
            self.stream = None


if __name__ == "__main__":
    radio = Radio()
    radio.play()
