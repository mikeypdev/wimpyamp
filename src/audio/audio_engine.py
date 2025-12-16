"""
AudioEngine class for WimPyAmp application.

This class provides a simple interface for audio loading, playback,
and equalization using librosa, sounddevice, and scipy.
"""

import numpy as np
import librosa
import sounddevice as sd  # type: ignore
import threading
import time
from typing import Dict
from mutagen import File as MutagenFile
from scipy import signal  # type: ignore
import queue
from collections import deque


class AudioEngine:
    def __init__(self, playback_callback=None):
        """Initialize the AudioEngine."""
        self.audio_data = None
        self.sample_rate = None
        self.current_position = 0.0
        self.is_playing = False
        self.is_paused = False
        self.play_thread = None
        self.eq_bands = {}
        self.file_path = None
        self.metadata = {}
        self.duration = 0.0
        self.bitrate = 0
        self.is_vbr = False
        self.playback_callback = playback_callback

        # For volume and seeking
        self.volume = 1.0
        self.balance = 0.0  # -1.0 to 1.0, where 0.0 is center
        self.is_eq_on = False  # Whether EQ is currently active

        # Thread control
        self.stop_event = threading.Event()

        # Position update lock for thread safety
        self.position_lock = threading.Lock()

        # Seeking control
        self.seek_requested = False
        self.seek_position = 0.0

        # Visualization-related attributes
        self.vis_mode = "SPECTRUM"  # Current visualization mode
        self.vis_data_queue = queue.Queue()  # Thread-safe queue for visualization data
        self.vis_thread = None  # Thread for visualization processing
        self.vis_stop_event = threading.Event()  # Event to stop visualization thread
        self.audio_buffer = deque(
            maxlen=2048
        )  # Buffer to hold recent audio samples for oscilloscope

    def load_track(self, file_path: str):
        """Loads a track using librosa into a NumPy array."""
        try:
            # Stop any existing playback before loading a new track
            self._ensure_stopped()

            # Load audio file using librosa with proper parameters
            self.audio_data, self.sample_rate = librosa.load(
                file_path, sr=None, mono=False
            )
            self.current_position = 0.0
            self.file_path = file_path
            # Calculate duration properly
            self.duration = (
                librosa.get_duration(y=self.audio_data, sr=self.sample_rate)
                if self.audio_data is not None and self.sample_rate
                else 0.0
            )

            # Reset seeking state for new track
            with self.position_lock:
                self.seek_requested = False
                self.seek_position = 0.0

            # Check if audio data is properly loaded
            if self.audio_data is None or len(self.audio_data) == 0:
                print(f"Error: No audio data loaded from {file_path}")
                return False

            # If the file is mono, librosa returns a 1D array, if stereo, it returns a 2D array [channels, samples]
            # With mono=False, stereo files return [2, samples], mono files return [1, samples]
            print(
                f"Loaded track: {file_path}, Sample rate: {self.sample_rate} Hz, Duration: {self.duration:.2f} s, Shape: {self.audio_data.shape if self.audio_data is not None else 'None'}"
            )
            print(
                f"Audio data type: {self.audio_data.dtype if self.audio_data is not None else 'None'}"
            )

            # Load metadata
            self._load_metadata(file_path)

            return True
        except Exception as e:
            print(f"Error loading track {file_path}: {e}")
            return False

    def has_track_loaded(self):
        """Check if a track has been loaded."""
        return self.file_path is not None

    def _load_metadata(self, file_path):
        """Load metadata from audio file using mutagen."""
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is not None:
                # Helper function to safely extract metadata
                def safe_extract_metadata(audio_file, keys):
                    result = "Unknown"
                    for key in keys:
                        try:
                            if key in audio_file:
                                tag_value = audio_file[key]
                                if isinstance(tag_value, list) and len(tag_value) > 0:
                                    try:
                                        raw_value = tag_value[0]
                                        # Only convert to string if it's not None
                                        if raw_value is not None:
                                            result = str(raw_value).strip()
                                        else:
                                            result = "Unknown"
                                    except (
                                        UnicodeDecodeError,
                                        TypeError,
                                        AttributeError,
                                    ):
                                        # Handle cases where value can't be converted to string
                                        result = "Unknown"
                                elif (
                                    isinstance(tag_value, list) and len(tag_value) == 0
                                ):
                                    continue
                                else:
                                    try:
                                        # Handle single values
                                        if tag_value is not None:
                                            result = str(tag_value).strip()
                                        else:
                                            result = "Unknown"
                                    except (
                                        UnicodeDecodeError,
                                        TypeError,
                                        AttributeError,
                                    ):
                                        # Handle cases where value can't be converted to string
                                        result = "Unknown"
                                break
                        except Exception:
                            # If any key access fails, continue to next key
                            continue
                    return result if result else "Unknown"

                # Title - try multiple possible keys for different formats
                title_keys = ["TIT2", "title", "\xa9nam", "TITLE", "©nam"]
                self.metadata["title"] = safe_extract_metadata(audio_file, title_keys)

                # Artist - try multiple possible keys for different formats
                artist_keys = ["TPE1", "artist", "\xa9ART", "ARTIST", "©ART"]
                self.metadata["artist"] = safe_extract_metadata(audio_file, artist_keys)

                # Album - try multiple possible keys for different formats
                album_keys = ["TALB", "album", "\xa9alb", "ALBUM", "©alb"]
                self.metadata["album"] = safe_extract_metadata(audio_file, album_keys)

                # Album artist - try multiple possible keys for different formats
                album_artist_keys = ["TPE2", "albumartist", "aART", "©aAR"]
                self.metadata["album_artist"] = safe_extract_metadata(
                    audio_file, album_artist_keys
                )

                # Extract embedded album art
                self.metadata["album_art"] = self._extract_album_art(audio_file)

                # Duration is already calculated from the audio data
                self.metadata["duration"] = self.duration

                # Bitrate and other technical info
                if hasattr(audio_file, "info"):
                    info = audio_file.info
                    self.bitrate = (
                        int(getattr(info, "bitrate", 0) / 1000)
                        if hasattr(info, "bitrate")
                        else 0
                    )
                    # Check if VBR (some formats might not have this info)
                    self.is_vbr = (
                        getattr(info, "bitrate_mode", 0) != 0
                    )  # Placeholder logic
            else:
                # Fallback for formats not supported by mutagen
                self.metadata = {
                    "title": "Unknown",
                    "artist": "Unknown",
                    "album": "Unknown",
                    "album_artist": "Unknown",
                    "album_art": None,
                    "duration": self.duration,
                }
        except Exception:
            # If metadata loading fails completely, use defaults
            self.metadata = {
                "title": "Unknown",
                "artist": "Unknown",
                "album": "Unknown",
                "album_artist": "Unknown",
                "album_art": None,
                "duration": self.duration,
            }

    def play(self):
        """Starts playback in a separate thread."""
        if self.audio_data is None:
            print("No track loaded")
            return

        # Check if we are resuming from a paused state before stopping
        was_paused = self.is_paused

        # Ensure any existing playback is stopped before starting new playback
        self._ensure_stopped()

        # If we were paused, don't reset the position
        if not was_paused and not self.is_playing:
            self.current_position = 0.0  # Start from beginning if not currently playing and not resuming from pause

        self.is_playing = True
        self.is_paused = False
        self.stop_event.clear()  # Clear the stop event
        self.play_thread = threading.Thread(target=self._playback_worker)
        self.play_thread.start()

    def _ensure_stopped(self):
        """Ensures any existing playback is properly stopped."""
        if self.is_playing or self.is_paused:
            # Stop playback properly by setting flags and waiting for thread to finish
            self.is_playing = False
            self.is_paused = False
            self.stop_event.set()  # Signal the thread to stop
            # Wait for the thread to finish with a timeout
            if self.play_thread and self.play_thread.is_alive():
                self.play_thread.join(
                    timeout=2.0
                )  # Wait up to 2 seconds for thread to finish

    def pause(self):
        """Pauses playback."""
        if self.is_playing:
            self.is_paused = True
            self.is_playing = False

    def stop(self):
        """Stops playback and resets the position."""
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0
        self.stop_event.set()  # Set stop event to signal thread to stop
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(
                timeout=2.0
            )  # Wait for thread to finish with longer timeout

    def set_eq(self, bands: Dict):
        """Sets the gain for different EQ frequency bands."""
        self.eq_bands = bands.copy()  # Make a copy to avoid reference issues
        # Update the equalization bands with default values if not provided
        # Values are in dB, typically ranging from -12dB to +12dB (Winamp standard)
        default_bands = {
            "preamp": 0.0,  # in dB
            "60hz": 0.0,  # in dB
            "170hz": 0.0,  # in dB
            "310hz": 0.0,  # in dB
            "600hz": 0.0,  # in dB
            "1khz": 0.0,  # in dB
            "3khz": 0.0,  # in dB
            "6khz": 0.0,  # in dB
            "12khz": 0.0,  # in dB
            "14khz": 0.0,  # in dB
            "16khz": 0.0,  # in dB
        }

        # Update with provided values
        for key, value in bands.items():
            if key in default_bands:
                default_bands[key] = value

        self.eq_bands = default_bands

    def _apply_eq_to_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """Apply equalization to an audio chunk using scipy filters."""
        if not self.eq_bands or not any(v != 0.0 for v in self.eq_bands.values()):
            # If no EQ is active (all gains are 0), return original chunk
            return chunk

        # Convert dB gains to linear scale
        gains = {}
        for band, db_gain in self.eq_bands.items():
            gains[band] = 10 ** (db_gain / 20.0)  # Convert dB to linear scale

        # Apply preamp gain first
        chunk = chunk * gains["preamp"] if gains["preamp"] != 1.0 else chunk

        # For each frequency band, apply a bandpass filter and adjust its gain
        # We'll use a combination of butterworth filters for each band
        if chunk.ndim == 1:
            # Mono audio
            chunk = self._apply_eq_to_mono(chunk, gains)
        elif chunk.ndim == 2 and chunk.shape[0] <= 2:
            # Stereo audio - apply the same EQ to both channels
            if chunk.shape[0] == 2:
                # Separate left and right channels
                left_channel = self._apply_eq_to_mono(chunk[0], gains)
                right_channel = self._apply_eq_to_mono(chunk[1], gains)
                chunk = np.vstack([left_channel, right_channel])
            elif chunk.shape[0] == 1:
                # Mono audio embedded in stereo container
                chunk[0] = self._apply_eq_to_mono(chunk[0], gains)

        return chunk

    def _apply_eq_to_mono(self, mono_chunk: np.ndarray, gains: Dict) -> np.ndarray:
        """Apply EQ to a single channel of audio using biquad peaking filters."""
        processed_chunk = mono_chunk.copy().astype(np.float64)

        # Define frequency bands for Winamp-style EQ
        bands = [
            ("60hz", 60),
            ("170hz", 170),
            ("310hz", 310),
            ("600hz", 600),
            ("1khz", 1000),
            ("3khz", 3000),
            ("6khz", 6000),
            ("12khz", 12000),
            ("14khz", 14000),
            ("16khz", 16000),
        ]

        # Apply each band's gain using a peaking filter
        for band_name, center_freq in bands:
            db_gain = self.eq_bands[band_name]
            if db_gain != 0.0:  # Only process if gain is not zero
                # Create peaking EQ filter using biquad coefficients
                processed_chunk = self._apply_peaking_filter(
                    processed_chunk, center_freq, db_gain, self.sample_rate
                )

        return processed_chunk

    def _apply_peaking_filter(
        self,
        audio: np.ndarray,
        center_freq: float,
        db_gain: float,
        sample_rate: int,
        q: float = 1.41,
    ) -> np.ndarray:
        """Apply a peaking filter to audio using biquad coefficients."""
        # Calculate the intermediate variables
        A = 10 ** (db_gain / 40.0)  # Amplitude factor
        w0 = 2 * np.pi * center_freq / sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2 * q)

        # Calculate the biquad coefficients for a peaking EQ filter
        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A

        # Normalize by a0
        b = np.array([b0, b1, b2]) / a0
        a = np.array([a0, a1, a2]) / a0

        # Apply the filter
        filtered = signal.lfilter(b, a, audio)
        return filtered

    def get_waveform_data(self) -> np.ndarray:
        """Returns the entire waveform data."""
        if self.audio_data is not None:
            return self.audio_data
        return np.array([])

    def get_current_position(self) -> float:
        """Returns the current playback position in seconds."""
        with self.position_lock:
            return self.current_position

    def get_duration(self) -> float:
        """Returns the total duration of the loaded track."""
        return self.duration

    def _extract_album_art(self, audio_file):
        """Extract embedded album art from audio file."""
        try:
            # For M4A files (iTunes-style metadata), images are stored as "covr" tag - check this first
            if "covr" in audio_file:
                from mutagen.mp4 import MP4Cover  # Import the specific M4A cover type

                cover_data_list = audio_file["covr"]
                # In M4A files, cover_data_list contains MP4Cover objects or raw image bytes
                if cover_data_list and len(cover_data_list) > 0:
                    # The cover art is typically stored as MP4Cover objects or raw bytes in a list
                    for cover_item in cover_data_list:
                        if isinstance(cover_item, MP4Cover):
                            # MP4Cover is a specialized bytes subclass with image format info
                            return bytes(cover_item)
                        elif isinstance(cover_item, bytes):
                            return cover_item
                        elif hasattr(cover_item, "data") and hasattr(
                            cover_item, "imageformat"
                        ):
                            # For Picture objects from other formats
                            return cover_item.data
                        elif hasattr(cover_item, "value") and isinstance(
                            cover_item.value, bytes
                        ):
                            # Alternative access pattern
                            return cover_item.value
                        else:
                            try:
                                # Try to convert to bytes if possible
                                return bytes(cover_item)
                            except Exception:
                                continue
                # If all fails, try with the first item directly
                if cover_data_list:
                    first_item = cover_data_list[0]
                    if isinstance(first_item, bytes):
                        return (
                            bytes(first_item)
                            if isinstance(first_item, MP4Cover)
                            else first_item
                        )

            # For MP3 files (ID3 tags), images are stored in APIC frames
            elif hasattr(audio_file, "tags") and audio_file.tags:
                # Check for ID3 tags (MP3 files)
                if hasattr(audio_file.tags, "getall"):
                    apic_frames = audio_file.tags.getall("APIC")
                    if apic_frames:
                        # Return the first image data found
                        return apic_frames[0].data

            # For FLAC files (Vorbis comments), images are stored as "METADATA_BLOCK_PICTURE"
            elif "METADATA_BLOCK_PICTURE" in audio_file:
                from mutagen.flac import Picture

                picture_data = audio_file["METADATA_BLOCK_PICTURE"][
                    0
                ]  # Get first picture
                pic = Picture(picture_data)
                return pic.data

        except Exception as e:
            print(f"Error extracting album art: {e}")
            return None

        return None

    def get_album_art(self):
        """Returns embedded album art data of the loaded track."""
        if self.metadata and "album_art" in self.metadata:
            return self.metadata["album_art"]
        return None

    def get_metadata(self):
        """Returns metadata of the loaded track."""
        return self.metadata

    def is_stereo_track(self) -> bool:
        """Returns True if the loaded track is stereo."""
        if self.audio_data is not None:
            return self.audio_data.ndim > 1 and self.audio_data.shape[0] == 2
        return True  # Default to true if no track loaded

    def get_playback_state(self):
        """Returns the current playback state."""
        # Acquire the position lock to ensure thread-safe access to current_position
        with self.position_lock:
            return {
                "is_playing": self.is_playing,
                "is_paused": self.is_paused,
                "position": self.current_position,
                "duration": self.duration,
                "volume": self.volume,
            }

    def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))

    def set_balance(self, balance: float):
        """Set playback balance (-1.0 to 1.0, where 0.0 is center)."""
        self.balance = max(-1.0, min(1.0, balance))

    def toggle_eq(self, enabled: bool):
        """Enable or disable the equalizer."""
        self.is_eq_on = bool(enabled)

    def set_visualization_mode(self, mode: str):
        """Set the visualization mode and start/stop visualization processing as needed."""
        self.vis_mode = mode
        if mode in ["SPECTRUM", "OSCILLOSCOPE"]:
            if not self.vis_thread or not self.vis_thread.is_alive():
                self.start_visualization_thread()
        else:  # OFF mode
            self.stop_visualization_thread()

    def start_visualization_thread(self):
        """Start the visualization processing thread."""
        if self.vis_thread and self.vis_thread.is_alive():
            self.stop_visualization_thread()

        self.vis_stop_event.clear()
        self.vis_thread = threading.Thread(target=self._visualization_worker)
        self.vis_thread.daemon = True  # Dies when main thread dies
        self.vis_thread.start()

    def stop_visualization_thread(self):
        """Stop the visualization processing thread."""
        self.vis_stop_event.set()
        if self.vis_thread and self.vis_thread.is_alive():
            self.vis_thread.join(
                timeout=1.0
            )  # Wait up to 1 second for thread to finish

    def _visualization_worker(self):
        """Internal method that handles visualization processing in a separate thread."""

        # Process audio data for visualization as it becomes available
        while not self.vis_stop_event.is_set():
            # Only process if we're playing audio
            if self.is_playing and not self.is_paused and self.audio_data is not None:
                # Get recent audio samples from the buffer for processing
                if len(self.audio_buffer) > 0:
                    # Convert deque to numpy array for processing
                    audio_samples = np.array(list(self.audio_buffer))

                    # Process based on current visualization mode
                    if self.vis_mode == "SPECTRUM":
                        # Perform FFT and compute 19 frequency bands
                        vis_data = self._process_spectrum_data(audio_samples)
                    elif self.vis_mode == "OSCILLOSCOPE":
                        # Return raw audio data for oscilloscope
                        vis_data = audio_samples
                    else:
                        # If mode is OFF, no data to send
                        vis_data = None

                    # Put visualization data in the queue if available
                    if vis_data is not None:
                        try:
                            # Don't block if queue is full
                            self.vis_data_queue.put(vis_data, block=False)
                        except queue.Full:
                            # If queue is full, remove oldest item and add new one
                            try:
                                self.vis_data_queue.get_nowait()
                                self.vis_data_queue.put(vis_data, block=False)
                            except queue.Empty:
                                pass  # Ignore if get_nowait fails
            # Sleep to control processing rate (~30 FPS)
            time.sleep(0.033)  # ~30 FPS

    def _process_spectrum_data(self, audio_samples):
        """Process audio samples for spectrum analyzer visualization."""
        import numpy as np

        # Ensure we have enough samples for FFT
        if len(audio_samples) < 512:
            return [0.0] * 19  # Return 19 zero values if not enough samples

        # Use a subset of the audio samples for FFT
        # Take the last 2048 samples or all if fewer available
        fft_size = min(2048, len(audio_samples))
        samples_for_fft = audio_samples[-fft_size:]

        # If stereo, convert to mono by averaging
        if samples_for_fft.ndim > 1 and samples_for_fft.shape[0] == 2:
            samples_for_fft = np.mean(samples_for_fft, axis=0)
        elif samples_for_fft.ndim > 1:
            # For other multi-channel formats, take the first channel
            samples_for_fft = samples_for_fft[0]

        # Apply a window function to reduce spectral leakage
        windowed = samples_for_fft * np.hanning(len(samples_for_fft))

        # Perform the FFT
        fft_result = np.fft.rfft(windowed)

        # Calculate the magnitude of the FFT
        magnitude = np.abs(fft_result) / (fft_size / 2)

        # Define 19 frequency bands across the audible spectrum (20Hz - 20kHz)
        # Using a logarithmic scale to better match human hearing
        sample_rate = self.sample_rate if self.sample_rate is not None else 44100

        # Correctly calculate frequency for each bin
        # frequency_for_bin_k = k * sample_rate / fft_size
        # To get bin_for_frequency_f: bin = f * fft_size / sample_rate

        # Define logarithmic frequency band edges (19 bands + 1 edge points)
        # Frequencies from 20Hz to 20kHz, spread logarithmically
        min_freq = 20
        max_freq = 20000  # Limit to 20kHz for the upper range
        log_freqs = np.logspace(
            np.log10(min_freq), np.log10(max_freq), 20
        )  # 20 points = 19 bands + 1

        # Convert frequencies to FFT bin indices
        band_edges = np.array([int(f * fft_size / sample_rate) for f in log_freqs])
        band_edges = np.clip(band_edges, 0, len(magnitude) - 1)  # Clamp to valid range

        # Calculate the average magnitude for each band
        spectrum_bands = []
        for i in range(19):  # 19 bands
            start_bin = band_edges[i]
            end_bin = band_edges[i + 1]

            if end_bin > start_bin:
                # Calculate average magnitude for this band
                band_magnitude = np.mean(magnitude[start_bin:end_bin])
            else:
                # If the band has no bins, use the single nearest bin
                band_magnitude = (
                    magnitude[start_bin] if start_bin < len(magnitude) else 0
                )

            # Normalize and scale the magnitude to 0-1 for visualization
            # Use a power curve to achieve a logarithmic-like effect for values between 0 and 1
            normalized = min(1.0, band_magnitude**0.3)

            spectrum_bands.append(normalized)

        return spectrum_bands

    def seek(self, position: float):
        """Seek to a position in the track (0.0 to 1.0 as fraction of total duration)."""
        if self.audio_data is not None and self.sample_rate > 0:
            target_sample = int(position * self.duration * self.sample_rate)
            # Clamp to valid range
            target_time = max(0.0, min(self.duration, target_sample / self.sample_rate))

            with self.position_lock:
                self.current_position = target_time
                # Set seeking flag and position
                self.seek_position = target_time
                self.seek_requested = True

    def _playback_worker(self):
        """Internal method that handles audio playback in a separate thread."""
        # Define chunk size for streaming
        chunk_size = 4096

        # Calculate start index based on current position
        start_idx = int(self.current_position * self.sample_rate)

        # Determine number of channels
        if self.audio_data.ndim == 1:
            channels = 1
        else:
            channels = self.audio_data.shape[0]

        # Use the object-level lock for safe position updates
        position_lock = self.position_lock

        # Track last callback time for throttling
        callback_interval = 0.1  # 100ms between callbacks to avoid flooding UI
        last_callback_time = [
            time.time()
        ]  # Use list to make it mutable in nested function

        # Callback function for sounddevice stream
        def audio_callback(outdata, frames, callback_time, status):
            nonlocal start_idx

            # Check if a seek has been requested
            with self.position_lock:
                if self.seek_requested:
                    # Convert seek position (in seconds) to sample index
                    seek_start_idx = int(self.seek_position * self.sample_rate)
                    start_idx = seek_start_idx
                    # Also update current position to reflect the seek
                    self.current_position = self.seek_position
                    # Reset the seek flag
                    self.seek_requested = False

            # Calculate end index for this chunk
            end_idx = min(
                start_idx + frames,
                (
                    self.audio_data.shape[-1]
                    if self.audio_data.ndim > 1
                    else len(self.audio_data)
                ),
            )

            # Extract chunk
            if self.audio_data.ndim == 1:
                chunk = self.audio_data[start_idx:end_idx]
                # Pad with zeros if chunk is smaller than frames
                if len(chunk) < frames:
                    chunk = np.pad(chunk, (0, frames - len(chunk)), mode="constant")
            else:
                chunk = self.audio_data[:, start_idx:end_idx]
                # Pad with zeros if chunk is smaller than frames
                if chunk.shape[1] < frames:
                    pad_size = frames - chunk.shape[1]
                    chunk = np.pad(chunk, ((0, 0), (0, pad_size)), mode="constant")

            # Apply volume
            chunk = chunk * self.volume

            # Apply balance if stereo
            if self.audio_data.ndim > 1 and self.audio_data.shape[0] == 2:
                left_gain = min(
                    1.0, 1.0 - self.balance
                )  # 0 when balance = 1.0, 1.0 when balance = -1.0
                right_gain = min(
                    1.0, 1.0 + self.balance
                )  # 0 when balance = -1.0, 1.0 when balance = 1.0
                if chunk.shape[0] >= 2:  # Ensure we have 2 channels
                    chunk[0, :] *= left_gain  # Left channel
                    chunk[1, :] *= right_gain  # Right channel
                elif (
                    chunk.shape[0] == 1
                ):  # Mono file being balanced - duplicate to both channels
                    mono_audio = chunk[0, :]
                    chunk = np.array([mono_audio * left_gain, mono_audio * right_gain])

            # Apply EQ if enabled
            # Note: self.eq_bands is always a dict, but might be empty initially
            # Only apply EQ if it's turned on (self.is_eq_on is True)
            if self.is_eq_on:
                chunk = self._apply_eq_to_chunk(chunk)

            # Update position based on frames processed
            # Calculate position as a time value in seconds
            new_position = end_idx / self.sample_rate if self.sample_rate > 0 else 0.0

            # Clamp position to valid range to prevent overflow
            new_position = max(0.0, min(new_position, self.duration))

            with position_lock:
                self.current_position = new_position

            # Add audio samples to the visualization buffer for processing
            # Convert to mono if needed for visualization
            if chunk.ndim > 1:
                mono_chunk = (
                    np.mean(chunk, axis=0) if chunk.shape[0] > 1 else chunk[0, :]
                )
            else:
                mono_chunk = chunk

            # Add the samples to the visualization buffer
            for sample in mono_chunk:
                self.audio_buffer.append(sample)

            # Throttle the callbacks to avoid flooding the UI
            current_time = time.time()
            if (current_time - last_callback_time[0]) >= callback_interval:
                try:
                    # Use a copy of the position to avoid race conditions
                    with position_lock:
                        pos_copy = self.current_position

                    # Call playback callback if available
                    if self.playback_callback:
                        self.playback_callback(pos_copy, self.duration)

                    last_callback_time[0] = current_time
                except Exception as e:
                    print(f"Error in audio callbacks: {e}")

            # Copy to output buffer
            if self.audio_data.ndim > 1:
                # For multi-dimensional (stereo) audio
                if (
                    outdata.shape[1] == chunk.shape[0]
                ):  # Output expects [frames, channels]
                    outdata[:, :] = chunk.T
                elif (
                    outdata.shape[0] == chunk.shape[1]
                    and outdata.shape[1] == chunk.shape[0]
                ):  # Correct orientation
                    outdata[:, :] = chunk.T
                else:
                    # Fallback: reshape appropriately
                    if outdata.shape[1] == 2 and chunk.shape[0] == 2:
                        if chunk.shape[1] == outdata.shape[0]:
                            outdata[:, :] = chunk.T
                        else:
                            # Need to make sure chunk has proper width
                            if chunk.shape[1] < outdata.shape[0]:
                                chunk = np.pad(
                                    chunk,
                                    ((0, 0), (0, outdata.shape[0] - chunk.shape[1])),
                                    mode="constant",
                                )
                            outdata[: chunk.shape[1], :] = chunk.T
                    elif outdata.shape[1] == 1:  # Output is mono
                        if chunk.shape[0] == 1:
                            outdata[: chunk.shape[1], 0] = (
                                chunk[0, :] if chunk.ndim > 1 else chunk[:]
                            )
                        else:  # Convert stereo to mono by averaging
                            mono_chunk = (chunk[0, :] + chunk[1, :]) / 2
                            outdata[: len(mono_chunk), 0] = mono_chunk
            else:
                # For mono audio
                if outdata.shape[1] == 1:  # Output expects mono
                    if len(chunk) > outdata.shape[0]:
                        outdata[:, 0] = chunk[: outdata.shape[0]]
                    else:
                        outdata[: len(chunk), 0] = chunk
                else:  # Output expects stereo but we have mono
                    if len(chunk) > outdata.shape[0]:
                        outdata[:, 0] = chunk[: outdata.shape[0]]
                        outdata[:, 1] = chunk[: outdata.shape[0]]
                    else:
                        outdata[: len(chunk), 0] = chunk
                        outdata[: len(chunk), 1] = chunk

            # Update start index for next callback
            start_idx = end_idx

            # Stop if we've reached the end
            if end_idx >= (
                self.audio_data.shape[-1]
                if self.audio_data.ndim > 1
                else len(self.audio_data)
            ):
                self.is_playing = False
                self.is_paused = False

        # Open and start the audio stream
        try:
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=channels,
                callback=audio_callback,
                blocksize=chunk_size,
            ):
                # Continue while playing and not paused
                total_samples = (
                    self.audio_data.shape[-1]
                    if self.audio_data.ndim > 1
                    else len(self.audio_data)
                )
                while (
                    self.is_playing
                    and start_idx < total_samples
                    and not self.stop_event.is_set()
                ):
                    time.sleep(0.05)  # Smaller delay for smoother UI updates

                    # Check if we've reached the end
                    if start_idx >= total_samples:
                        break

        except Exception as e:
            print(f"Error in audio playback: {e}")

        finally:
            # When playback finishes, update state
            if not self.is_paused:
                self.is_playing = False
                self.is_paused = False
            # Clear the stop event for next playback
            self.stop_event.clear()
