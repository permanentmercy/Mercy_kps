"""
core/audio_capture.py
Singleton that captures Windows system audio (WASAPI loopback) in a background
thread and exposes a normalised FFT bar array for the kps_visualizer widget.
"""
import threading
import time

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    import pyaudiowpatch as pyaudio
    _HAS_PYAUDIO = True
except ImportError:
    _HAS_PYAUDIO = False


class AudioCapture:
    """Singleton WASAPI loopback capture.

    Usage:
        ac = AudioCapture.instance()
        ac.start()          # idempotent
        bars = ac.get_bars(n=16)
        ac.stop()           # call on app exit
    """

    _instance = None
    _lock = threading.Lock()
    _global_pa = None
    _global_pa_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "AudioCapture":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def get_pa(cls):
        with cls._global_pa_lock:
            if cls._global_pa is None:
                if _HAS_PYAUDIO:
                    try:
                        cls._global_pa = pyaudio.PyAudio()
                    except Exception:
                        pass
            return cls._global_pa

    @classmethod
    def terminate_global_pa(cls):
        """Called upon application exit to cleanly release PortAudio resources."""
        with cls._global_pa_lock:
            if cls._global_pa is not None:
                try:
                    cls._global_pa.terminate()
                except Exception:
                    pass
                cls._global_pa = None

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._stream = None
        self._device_name = None

        # Shared raw FFT magnitude array (half of FFT size)
        self._fft_mag = []
        self._fft_lock = threading.Lock()

        self._sample_rate = 44100
        self._chunk = 1024
        self._channels = 2
        self.error: str = ""          # last init error, empty = OK
        self.available: bool = False  # True once stream opened OK

    # ── Public API ────────────────────────────────────────────────────────

    @classmethod
    def get_loopback_devices(cls) -> list:
        """Returns a list of dicts: [{'index': idx, 'name': name}] of all WASAPI loopback devices."""
        pa = cls.get_pa()
        if pa is None:
            return []
        devices = []
        try:
            for i in range(pa.get_device_count()):
                d = pa.get_device_info_by_index(i)
                if d.get("isLoopbackDevice"):
                    devices.append({
                        'index': i,
                        'name': d['name']
                    })
        except Exception:
            pass
        return devices

    def start(self, device_name=None):
        """Start the background capture thread with a specific device_name (idempotent if same device)."""
        if self._running and self._device_name == device_name:
            return
        
        if self._running:
            self.stop()

        self._device_name = device_name
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="AudioCapture")
        self._thread.start()

    def stop(self):
        """Signal the capture thread to stop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._cleanup()

    def get_bars(self, n: int = 16) -> list:
        """Return n normalised bar heights [0..1] from the last FFT frame."""
        with self._fft_lock:
            mag = list(self._fft_mag)

        if not mag:
            return [0.0] * n

        # Bin the spectrum into n groups
        usable = len(mag)
        bin_size = max(1, usable // n)
        bars = []
        if _HAS_NUMPY:
            arr = np.asarray(mag, dtype=np.float32)
            for i in range(n):
                start = i * bin_size
                end = min(start + bin_size, usable)
                bars.append(float(arr[start:end].mean()) if end > start else 0.0)
        else:
            for i in range(n):
                start = i * bin_size
                end = min(start + bin_size, usable)
                chunk = mag[start:end]
                bars.append(sum(chunk) / len(chunk) if chunk else 0.0)

        # Normalise
        mx = max(bars) if bars else 0.0
        if mx > 1e-6:
            bars = [v / mx for v in bars]
        return bars

    # ── Internal ──────────────────────────────────────────────────────────

    def _run(self):
        pa = self.get_pa()
        if pa is None:
            self.error = "pyaudiowpatch not installed or failed to initialize"
            self._running = False
            return

        try:
            loopback_device = None


            # Try to match the saved device_name
            if self._device_name and self._device_name != "default":
                for i in range(pa.get_device_count()):
                    d = pa.get_device_info_by_index(i)
                    if d.get("isLoopbackDevice") and d["name"] == self._device_name:
                        loopback_device = d
                        break

            # Fallback to default speakers loopback
            if loopback_device is None:
                wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers_idx = wasapi_info["defaultOutputDevice"]
                device_info = pa.get_device_info_by_index(default_speakers_idx)

                for i in range(pa.get_device_count()):
                    d = pa.get_device_info_by_index(i)
                    if d.get("isLoopbackDevice") and d["name"] == device_info["name"]:
                        loopback_device = d
                        break

            if loopback_device is None:
                self.error = "No WASAPI loopback device found"
                self._running = False
                return

            self._sample_rate = int(loopback_device["defaultSampleRate"])
            self._channels = min(2, loopback_device["maxInputChannels"])

            self._stream = pa.open(
                format=pyaudio.paFloat32,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                input_device_index=loopback_device["index"],
                frames_per_buffer=self._chunk,
            )
            self.available = True

            while self._running:
                try:
                    raw = self._stream.read(self._chunk, exception_on_overflow=False)
                    self._process(raw)
                except Exception:
                    time.sleep(0.01)

        except Exception as exc:
            self.error = str(exc)
            self._running = False
        finally:
            self._cleanup()

    def _process(self, raw: bytes):
        """Convert raw bytes → FFT magnitude spectrum."""
        if not _HAS_NUMPY:
            return
        try:
            data = np.frombuffer(raw, dtype=np.float32)
            # Mix to mono
            if self._channels == 2:
                data = data.reshape(-1, 2).mean(axis=1)
            # Apply Hanning window then FFT
            window = np.hanning(len(data))
            spectrum = np.abs(np.fft.rfft(data * window))
            # Discard DC bin, keep only useful range (up to 8 kHz-ish)
            spectrum = spectrum[1:]
            max_bin = max(1, len(spectrum) // 2)
            spectrum = spectrum[:max_bin]
            with self._fft_lock:
                self._fft_mag = spectrum.tolist()
        except Exception:
            pass

    def _cleanup(self):
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
        except Exception:
            pass

