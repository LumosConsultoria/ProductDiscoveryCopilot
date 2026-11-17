import io
import wave
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1

class MeetingRecorder:
    def __init__(self):
        self.frames = []
        self.stream = None
        self.recording = False
        self.paused = False

    def _callback(self, indata, frames, time, status):
        if self.recording and not self.paused:
            self.frames.append(indata.copy())

    def start(self):
        if self.recording:
            return
        self.frames = []
        self.recording = True
        self.paused = False
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=self._callback,
        )
        self.stream.start()

    def pause(self):
        if self.recording:
            self.paused = True

    def resume(self):
        if self.recording:
            self.paused = False

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        self.stream = None
        self.recording = False
        self.paused = False

    def has_audio(self):
        return bool(self.frames)

    def to_wav_bytes(self):
        if not self.frames:
            return b""
        audio = np.concatenate(self.frames, axis=0)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buffer.getvalue()
