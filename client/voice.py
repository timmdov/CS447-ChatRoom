import pyaudio
import wave
import threading
import time
import io
import os

class VoiceRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.recording = False
        self.frames = []
        self.chunk = 1024
        self.sample_format = pyaudio.paInt16
        self.channels = 1
        self.sample_rate = 44100
        
    def start_recording(self):
        """Start recording audio"""
        self.recording = True
        self.frames = []
        
        def record():
            stream = self.audio.open(
                format=self.sample_format,
                channels=self.channels,
                rate=self.sample_rate,
                frames_per_buffer=self.chunk,
                input=True
            )
            
            while self.recording:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    self.frames.append(data)
                except Exception as e:
                    print(f"Error recording: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            
        self.record_thread = threading.Thread(target=record)
        self.record_thread.start()
        
    def stop_recording(self):
        """Stop recording and return the audio data"""
        self.recording = False
        if hasattr(self, 'record_thread'):
            self.record_thread.join()
        
        audio_data = b''.join(self.frames)
        return audio_data
        
    def save_recording(self, filename):
        """Save the recording to a WAV file"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.sample_format))
        wf.setframerate(self.sample_rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()

class VoicePlayer:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        
    def play_audio(self, audio_data):
        """Play audio from bytes data"""
        try:
            wav_file = io.BytesIO()
            with wave.open(wav_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  
                wf.setframerate(44100)
                wf.writeframes(audio_data)
                
            wav_file.seek(0)
            with wave.open(wav_file, 'rb') as wf:
                stream = self.audio.open(
                    format=self.audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)
                    
                stream.stop_stream()
                stream.close()
                
        except Exception as e:
            print(f"Error playing audio: {e}")
            
    def play_file(self, filename):
        """Play audio from a WAV file"""
        try:
            with wave.open(filename, 'rb') as wf:
                stream = self.audio.open(
                    format=self.audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)
                    
                stream.stop_stream()
                stream.close()
                
        except Exception as e:
            print(f"Error playing file: {e}")