"""
Retro Cassette Player v2
Batch 18: Fix trapesium vs window overlap + roda lebih rapi
Jalankan: python retro_player.py
"""
import sys
import os
import math
import random
import vlc
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QComboBox
)
from PySide6.QtCore import (
    Qt, QPointF, QRectF, QTimer, QThread, Signal, QSettings
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QPolygonF, QPixmap
)

try:
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    import pyaudiowpatch as pyaudio
    HAS_AUDIO_CAP = True
except ImportError:
    HAS_AUDIO_CAP = False


C = {
    "body_blue_1":  "#B9CFE0",
    "body_blue_2":  "#8FB1CB",
    "body_blue_3":  "#6E92B0",
    "panel_blue_1": "#CFDDE8",
    "panel_blue_2": "#A8C2D6",
    "panel_blue_3": "#8AABC4",
    "cream_1":      "#F7EFDD",
    "cream_2":      "#EDE2C9",
    "cream_3":      "#DDD0B5",
    "cream_track":  "#C9BFA8",
    "cass_1":       "#F5E8D0",
    "cass_2":       "#E5D5B8",
    "cass_border":  "#3A3530",
    "orange_1":     "#D87F52",
    "orange_2":     "#C26B44",
    "orange_soft":  "#E5A98A",
    "peach_row":    "#F5D5C8",
    "tape_brown":   "#7A5A42",
    "tape_brown_d": "#5A4030",
    "tape_dark":    "#3A2A1E",
    "text_dark":    "#3A3530",
    "text_muted":   "#8A837A",
    "text_time":    "#6B5F52",
    "text_light":   "#F0E6D2",
    "play_btn":     "#E08A5C",
    "play_btn_hl":  "#EFA882",
    "vis_bar":      "#E5A88C",
    "vis_peak":     "#D47B4A",
    "btn_3d_top":   "#F0B594",
    "btn_3d_mid":   "#E08A5C",
    "btn_3d_bot":   "#B86540",
    "btn_3d_border":"#9B5232",
}


CASSETTE_PANEL = QRectF(50, 55, 510, 235)
CASSETTE_RECT  = QRectF(115, 72, 380, 200)

EQ_PANEL = QRectF(50, 300, 510, 175)
EQ_TRACK_TOP = 340
EQ_TRACK_BOTTOM = 450
EQ_TRACK_H = EQ_TRACK_BOTTOM - EQ_TRACK_TOP
EQ_GAIN_MIN = -12
EQ_GAIN_MAX = 12
EQ_BAND_COUNT = 10
EQ_FADER_X_START = 110
EQ_FADER_X_STEP = 45
EQ_FREQ_LABELS = ["60", "170", "310", "600", "1k", "3k", "6k", "12k", "14k", "16k"]

PLAYLIST_PANEL = QRectF(590, 55, 460, 420)
BOTTOM_BAR = QRectF(30, 485, 1020, 200)


EQ_PRESETS = {
    "Flat":              [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Bass Boost":        [6, 5, 4, 2, 1, 0, -1, -2, -2, -2],
    "Bass & Treble":     [5, 4, 2, 0, -1, -1, 0, 2, 4, 5],
    "Treble Boost":      [0, 0, 0, 0, 0, 1, 2, 3, 4, 5],
    "Rock":              [4, 3, 2, 0, -1, -1, 1, 2, 3, 4],
    "Pop":               [-1, 1, 2, 3, 3, 2, 0, -1, -1, -1],
    "Jazz":              [2, 2, 1, 2, -1, -1, 0, 1, 2, 3],
    "Classical":         [3, 2, 1, 1, -1, -1, 0, 2, 3, 3],
    "Dance":             [4, 3, 1, 0, 0, -1, -2, -2, 1, 1],
    "Techno":            [3, 2, 1, 0, -1, -1, 0, 2, 3, 3],
    "Club":              [0, 0, 2, 3, 3, 3, 2, 0, 0, 0],
    "Party":             [4, 4, 2, 0, 0, 0, 0, 0, 3, 4],
    "Live":              [-1, 0, 2, 2, 2, 1, 1, 0, -1, -1],
    "Large Hall":        [5, 5, 3, 2, 1, -1, -1, -1, 1, 2],
    "Full Bass":         [6, 5, 4, 2, 1, 0, -1, -2, -2, -2],
    "Full Treble":       [-2, -2, -2, -1, 0, 3, 4, 5, 5, 5],
    "Reggae":            [0, 0, 0, -1, 0, 3, 3, 0, 0, 0],
    "Hip-Hop":           [4, 3, 2, 1, -1, -1, 1, 2, 3, 3],
    "Vocal Boost":       [-1, -1, -1, 1, 2, 3, 2, 1, 0, 0],
    "Headphones":        [2, 2, 1, 0, -1, -1, -1, 1, 2, 3],
    "Soft":              [1, 1, 0, -1, -1, -1, 1, 2, 2, 3],
    "Warm":              [2, 1, 1, 0, -1, -1, 0, 1, 1, 2],
    "Bright":            [-1, -1, 0, 0, 1, 2, 3, 3, 3, 3],
    "V-Shape":           [3, 2, 1, -1, -2, -1, 0, 2, 3, 4],
}


def eq_gain_to_y(gain):
    ratio = (EQ_GAIN_MAX - gain) / (EQ_GAIN_MAX - EQ_GAIN_MIN)
    return EQ_TRACK_TOP + ratio * EQ_TRACK_H


def eq_y_to_gain(y):
    ratio = (y - EQ_TRACK_TOP) / EQ_TRACK_H
    ratio = max(0.0, min(1.0, ratio))
    gain = EQ_GAIN_MAX - ratio * (EQ_GAIN_MAX - EQ_GAIN_MIN)
    return int(round(gain))


def fmt_duration(ms):
    if ms is None or ms < 0: ms = 0
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


def clean_artist(s):
    if not s: return ""
    s = s.strip()
    if s in ("\u2014", "-", "\u2013", "\u2015"): return ""
    return s


def read_metadata(path):
    info = {"title": os.path.splitext(os.path.basename(path))[0],
            "artist": "", "album": "", "duration": 0, "cover": None}
    if not HAS_MUTAGEN:
        return info
    try:
        audio = MutagenFile(path)
        if audio is None:
            return info
        easy = MutagenFile(path, easy=True)
        if easy:
            if easy.get("title"):  info["title"]  = str(easy["title"][0])
            if easy.get("artist"):
                a = str(easy["artist"][0]).strip()
                if a not in ("\u2014", "-", "\u2013", "\u2015"):
                    info["artist"] = a
            if easy.get("album"):  info["album"]  = str(easy["album"][0])
        if hasattr(audio, "info") and audio.info:
            if hasattr(audio.info, "length"):
                info["duration"] = int(audio.info.length * 1000)
        cover_data = None
        if hasattr(audio, "tags") and audio.tags:
            for key in audio.tags.keys():
                if str(key).startswith("APIC"):
                    cover_data = audio.tags[key].data
                    break
        if cover_data is None and hasattr(audio, "pictures") and audio.pictures:
            cover_data = audio.pictures[0].data
        if cover_data is None and hasattr(audio, "tags") and "covr" in audio.tags:
            cover_data = bytes(audio.tags["covr"][0])
        if cover_data:
            pm = QPixmap()
            pm.loadFromData(cover_data)
            if not pm.isNull():
                info["cover"] = pm
    except Exception:
        pass
    return info


class AudioCapture(QThread):
    bars_ready = Signal(object)

    def __init__(self, n_bars=32):
        super().__init__()
        self.n_bars = n_bars
        self.running = False

    def stop(self):
        self.running = False
        self.wait(1500)

    def run(self):
        if not HAS_AUDIO_CAP:
            return
        p = pyaudio.PyAudio()
        try:
            try:
                wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            except OSError:
                p.terminate(); return
            default_speakers = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
            if not default_speakers.get("isLoopbackDevice", False):
                found = None
                for lb in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in lb["name"]:
                        found = lb; break
                if found is None:
                    for lb in p.get_loopback_device_info_generator():
                        found = lb; break
                if found is None:
                    p.terminate(); return
                default_speakers = found
            rate = int(default_speakers["defaultSampleRate"])
            channels = default_speakers["maxInputChannels"]
            chunk = 2048
            stream = p.open(format=pyaudio.paFloat32, channels=channels,
                            rate=rate, input=True,
                            input_device_index=default_speakers["index"],
                            frames_per_buffer=chunk)
        except Exception:
            p.terminate(); return

        self.running = True
        freqs = np.fft.rfftfreq(chunk, 1.0 / rate)
        fmin, fmax = 40, min(14000, rate / 2 - 1)
        edges = np.logspace(np.log10(fmin), np.log10(fmax), self.n_bars + 1)
        band_idx = []
        for i in range(self.n_bars):
            lo = int(np.searchsorted(freqs, edges[i]))
            hi = int(np.searchsorted(freqs, edges[i + 1]))
            if hi <= lo: hi = lo + 1
            band_idx.append((lo, hi))
        window = np.hanning(chunk).astype(np.float32)

        while self.running:
            try:
                data = stream.read(chunk, exception_on_overflow=False)
            except Exception:
                continue
            samples = np.frombuffer(data, dtype=np.float32)
            if channels > 1:
                samples = samples.reshape(-1, channels).mean(axis=1)
            if len(samples) < chunk:
                samples = np.pad(samples, (0, chunk - len(samples)))
            spectrum = np.abs(np.fft.rfft(samples * window))
            bands = np.zeros(self.n_bars, dtype=np.float32)
            for i, (lo, hi) in enumerate(band_idx):
                bands[i] = spectrum[lo:hi].mean()
            self.bars_ready.emit(bands)

        try:
            stream.stop_stream(); stream.close()
        except Exception:
            pass
        p.terminate()


class RetroPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.resize(1080, 700)
        self.setWindowTitle("Retro Cassette Player")
        self.setFocusPolicy(Qt.StrongFocus)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.settings = QSettings(
            os.path.join(base_dir, "settings.ini"), QSettings.IniFormat)

        self.instance = vlc.Instance("--no-video", "--quiet")
        self.player = self.instance.media_player_new()

        self.bg_path = self.settings.value("bg_path", "", type=str)
        self.bg_pixmap = None
        self._load_background()

        self._drag_pos = None
        self._playing = False
        self._current_index = -1
        self._volume = 80
        self._shuffle = False
        self._repeat = False
        self._seeking = False
        self._rotation = 0.0
        self._hover_delete_idx = -1

        self.eq_gains = [0] * EQ_BAND_COUNT
        self._eq_obj = None
        self._dragging_eq = -1
        self._loading_preset = False

        self.playlist = []
        self.viz_smooth = np.zeros(32)
        self.viz_peak = np.zeros(32)

        self._hit_play = QRectF()
        self._hit_prev = QRectF()
        self._hit_next = QRectF()
        self._hit_shuffle = QRectF()
        self._hit_repeat = QRectF()
        self._hit_progress = QRectF()
        self._hit_volume = QRectF()
        self._hit_add = QRectF()
        self._hit_reset_eq = QRectF()
        self._hit_tracks = []
        self._hit_track_delete = []
        self._hit_eq_bands = []

        self.btn_close = QPushButton("\uE8BB", self)
        self.btn_close.setGeometry(1020, 22, 26, 26)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFocusPolicy(Qt.NoFocus)
        self.btn_close.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,100);color:#3A3530;border:none;
            font-family:"Segoe MDL2 Assets";font-size:11px;border-radius:13px;}
            QPushButton:hover{background:rgba(216,127,82,220);color:white;}
        """)
        self.btn_close.clicked.connect(self.close)

        self.btn_bg_pick = QPushButton("\uE91B", self)
        self.btn_bg_pick.setGeometry(988, 22, 26, 26)
        self.btn_bg_pick.setCursor(Qt.PointingHandCursor)
        self.btn_bg_pick.setFocusPolicy(Qt.NoFocus)
        self.btn_bg_pick.setToolTip("Pilih gambar background")
        self.btn_bg_pick.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,100);color:#3A3530;border:none;
            font-family:"Segoe MDL2 Assets";font-size:13px;border-radius:13px;}
            QPushButton:hover{background:rgba(216,127,82,220);color:white;}
        """)
        self.btn_bg_pick.clicked.connect(self._choose_background)

        self.btn_bg_clear = QPushButton("\uE74D", self)
        self.btn_bg_clear.setGeometry(956, 22, 26, 26)
        self.btn_bg_clear.setCursor(Qt.PointingHandCursor)
        self.btn_bg_clear.setFocusPolicy(Qt.NoFocus)
        self.btn_bg_clear.setToolTip("Hapus background")
        self.btn_bg_clear.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,100);color:#3A3530;border:none;
            font-family:"Segoe MDL2 Assets";font-size:12px;border-radius:13px;}
            QPushButton:hover{background:rgba(216,127,82,220);color:white;}
        """)
        self.btn_bg_clear.clicked.connect(self._clear_background)
        self.btn_bg_clear.setVisible(self.bg_pixmap is not None)

        self.combo_preset = QComboBox(self)
        self.combo_preset.addItem("Kustom")
        for name in EQ_PRESETS.keys():
            self.combo_preset.addItem(name)
        self.combo_preset.setGeometry(280, 306, 140, 22)
        self.combo_preset.setCursor(Qt.PointingHandCursor)
        self.combo_preset.setFocusPolicy(Qt.NoFocus)
        self.combo_preset.setStyleSheet("""
            QComboBox {
                background: #F7EFDD; color: #3A3530;
                border: 1px solid #C9BFA8; border-radius: 6px;
                padding: 2px 8px; font-family: "Segoe UI";
                font-size: 9pt;
            }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 4px solid #3A3530;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background: #F7EFDD; color: #3A3530;
                border: 1px solid #C9BFA8; border-radius: 6px;
                padding: 4px;
                selection-background-color: #D87F52;
                selection-color: #F7EFDD;
                outline: none; font-size: 9pt;
            }
        """)
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)

        self.capture = AudioCapture(n_bars=32)
        self.capture.bars_ready.connect(self._on_bars)
        self.capture.start()

        self.timer_ui = QTimer()
        self.timer_ui.timeout.connect(self._tick)
        self.timer_ui.start(60)

        self._ending_guard = False

        saved_vol = int(self.settings.value("volume", 80))
        self._volume = saved_vol
        self.player.audio_set_volume(saved_vol)

    def keyPressEvent(self, e):
        key = e.key()
        if key == Qt.Key_Space:
            self._toggle_play()
        elif key == Qt.Key_Right:
            self._next()
        elif key == Qt.Key_Left:
            self._prev()
        elif key == Qt.Key_Up:
            self._volume = min(100, self._volume + 5)
            self.player.audio_set_volume(self._volume)
            self.settings.setValue("volume", self._volume)
            self.update()
        elif key == Qt.Key_Down:
            self._volume = max(0, self._volume - 5)
            self.player.audio_set_volume(self._volume)
            self.settings.setValue("volume", self._volume)
            self.update()
        elif key == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    def _load_background(self):
        if self.bg_path and os.path.exists(self.bg_path):
            pm = QPixmap(self.bg_path)
            if not pm.isNull():
                self.bg_pixmap = pm

    def _choose_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih gambar background", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp);;All files (*.*)")
        if not path: return
        pm = QPixmap(path)
        if pm.isNull(): return
        self.bg_pixmap = pm
        self.bg_path = path
        self.settings.setValue("bg_path", path)
        self.settings.sync()
        self.btn_bg_clear.setVisible(True)
        self.update()

    def _clear_background(self):
        self.bg_pixmap = None
        self.bg_path = ""
        self.settings.setValue("bg_path", "")
        self.settings.sync()
        self.btn_bg_clear.setVisible(False)
        self.update()

    def _on_bars(self, bars):
        bars = np.asarray(bars, dtype=np.float32)
        if len(bars) != 32:
            idx = np.linspace(0, len(bars) - 1, 32)
            bars = np.interp(idx, np.arange(len(bars)), bars)
        target = np.clip(bars / 18.0, 0, 1)
        target[target < 0.015] = 0
        alpha = np.where(target > self.viz_smooth, 0.65, 0.20)
        self.viz_smooth = self.viz_smooth + alpha * (target - self.viz_smooth)
        self.viz_peak = np.maximum(self.viz_peak * 0.93, self.viz_smooth)

    def _tick(self):
        state = self.player.get_state()
        was = self._playing
        self._playing = (state == vlc.State.Playing)
        if was != self._playing:
            self.update()

        if self._playing:
            intensity = float(np.mean(self.viz_smooth))
            speed = 35 + intensity * 220
            self._rotation = (self._rotation + speed * 0.06) % 360

        if state == vlc.State.Ended and not self._ending_guard:
            self._ending_guard = True
            QTimer.singleShot(50, self._on_ended)

        self.update()

    def _on_ended(self):
        if self._repeat and self._current_index >= 0:
            self._play_index(self._current_index)
        else:
            self._next()
        self._ending_guard = False

    def _apply_eq(self):
        any_nonzero = any(g != 0 for g in self.eq_gains)
        if not any_nonzero:
            try:
                vlc.libvlc_media_player_set_equalizer(self.player, None)
            except Exception:
                pass
            return
        try:
            if self._eq_obj is None:
                self._eq_obj = vlc.libvlc_audio_equalizer_new()
            if self._eq_obj is None:
                return
            vlc.libvlc_audio_equalizer_set_preamp(self._eq_obj, 0.0)
            for i, g in enumerate(self.eq_gains):
                vlc.libvlc_audio_equalizer_set_amp_at_index(self._eq_obj, float(g), i)
            vlc.libvlc_media_player_set_equalizer(self.player, self._eq_obj)
        except Exception as e:
            print("EQ error:", e)

    def _set_eq_from_y(self, idx, y):
        if not (0 <= idx < EQ_BAND_COUNT):
            return
        val = eq_y_to_gain(y)
        val = max(EQ_GAIN_MIN, min(EQ_GAIN_MAX, val))
        if self.eq_gains[idx] != val:
            self.eq_gains[idx] = val
            self._apply_eq()
            if not self._loading_preset and self.combo_preset.currentIndex() != 0:
                self._loading_preset = True
                self.combo_preset.setCurrentIndex(0)
                self._loading_preset = False

    def _reset_eq(self):
        self.eq_gains = [0] * EQ_BAND_COUNT
        self._apply_eq()
        self._loading_preset = True
        self.combo_preset.setCurrentIndex(1)
        self._loading_preset = False
        self.update()

    def _on_preset_changed(self, idx):
        if self._loading_preset: return
        if idx <= 0: return
        name = self.combo_preset.itemText(idx)
        if name not in EQ_PRESETS: return
        self._loading_preset = True
        self.eq_gains = list(EQ_PRESETS[name])
        self._loading_preset = False
        self._apply_eq()
        self.update()

    def _open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Pilih lagu", "",
            "Audio (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.opus *.wma);;All files (*.*)")
        if not files: return
        for f in files:
            meta = read_metadata(f)
            self.playlist.append({
                "path": f, "title": meta["title"], "artist": meta["artist"],
                "duration": meta["duration"], "cover": meta["cover"],
            })
        if self._current_index == -1:
            self._play_index(0)
        else:
            self.update()

    def _remove_track(self, idx):
        if not (0 <= idx < len(self.playlist)): return
        was_current = (idx == self._current_index)
        self.playlist.pop(idx)
        if was_current:
            self.player.stop()
            if self.playlist:
                new_idx = min(idx, len(self.playlist) - 1)
                self._play_index(new_idx)
            else:
                self._current_index = -1
        elif idx < self._current_index:
            self._current_index -= 1
        self._hover_delete_idx = -1
        self.update()

    def _play_index(self, idx):
        if not (0 <= idx < len(self.playlist)): return
        self._current_index = idx
        entry = self.playlist[idx]
        media = self.instance.media_new(entry["path"])
        self.player.set_media(media)
        self.player.play()
        self.update()

    def _toggle_play(self):
        if not self.playlist:
            self._open_files(); return
        if self._current_index == -1:
            self._play_index(0); return
        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()
        self.update()

    def _next(self):
        if not self.playlist: return
        if self._shuffle and len(self.playlist) > 1:
            idx = self._current_index
            while idx == self._current_index:
                idx = random.randint(0, len(self.playlist) - 1)
            self._play_index(idx)
        else:
            self._play_index((self._current_index + 1) % len(self.playlist))

    def _prev(self):
        if not self.playlist: return
        self._play_index((self._current_index - 1) % len(self.playlist))

    def _toggle_shuffle(self):
        self._shuffle = not self._shuffle
        self.update()

    def _toggle_repeat(self):
        self._repeat = not self._repeat
        self.update()

    def _set_volume_from_x(self, x, rect):
        ratio = (x - rect.left()) / max(1, rect.width())
        ratio = max(0.0, min(1.0, ratio))
        self._volume = int(ratio * 100)
        self.player.audio_set_volume(self._volume)
        self.settings.setValue("volume", self._volume)

    def _seek_from_x(self, x, rect):
        ratio = (x - rect.left()) / max(1, rect.width())
        ratio = max(0.0, min(1.0, ratio))
        self.player.set_position(ratio)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        files = []
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus", ".wma"):
                files.append(path)
        if not files: return
        for f in files:
            meta = read_metadata(f)
            self.playlist.append({
                "path": f, "title": meta["title"], "artist": meta["artist"],
                "duration": meta["duration"], "cover": meta["cover"],
            })
        if self._current_index == -1:
            self._play_index(0)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        W, H = self.width(), self.height()
        self._hit_tracks = []
        self._hit_track_delete = []
        self._hit_eq_bands = []

        if self.bg_pixmap:
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(2, 2, W - 4, H - 4), 34, 34)
            p.setClipPath(clip)
            scaled = self.bg_pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation)
            bx = (W - scaled.width()) // 2
            by = (H - scaled.height()) // 2
            p.drawPixmap(bx, by, scaled)
            p.restore()

        self._draw_body(p, W, H)
        self._draw_cassette_panel(p, W, H)
        self._draw_eq_panel(p, W, H)
        self._draw_playlist_panel(p, W, H)
        self._draw_bottom_bar(p, W, H)

    def _draw_body(self, p, W, H):
        has_bg = self.bg_pixmap is not None
        body_alpha = 165 if has_bg else 255

        p.setPen(Qt.NoPen)
        if not has_bg:
            p.setBrush(QColor(0, 0, 0, 60))
            sh = QPainterPath()
            sh.addRoundedRect(QRectF(6, 8, W - 12, H - 8), 36, 36)
            p.drawPath(sh)

        c1 = QColor(C["body_blue_1"]); c1.setAlpha(body_alpha)
        c2 = QColor(C["body_blue_2"]); c2.setAlpha(body_alpha)
        c3 = QColor(C["body_blue_3"]); c3.setAlpha(body_alpha)
        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.5, c2)
        grad.setColorAt(1.0, c3)
        body = QPainterPath()
        body.addRoundedRect(QRectF(2, 2, W - 4, H - 4), 34, 34)
        p.setBrush(grad)
        p.drawPath(body)

        if not has_bg:
            p.setBrush(QColor(255, 255, 255, 40))
            hl = QPainterPath()
            hl.addRoundedRect(QRectF(6, 5, W - 12, H * 0.22), 32, 32)
            p.drawPath(hl)

    def _draw_cassette_panel(self, p, W, H):
        panel = CASSETTE_PANEL
        pg = QLinearGradient(0, panel.top(), 0, panel.bottom())
        pg.setColorAt(0, QColor(C["panel_blue_1"]))
        pg.setColorAt(0.5, QColor(C["panel_blue_2"]))
        pg.setColorAt(1, QColor(C["panel_blue_3"]))
        path = QPainterPath()
        path.addRoundedRect(panel, 14, 14)
        p.setBrush(pg)
        p.setPen(QPen(QColor(70, 90, 110, 120), 2))
        p.drawPath(path)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 60), 2))
        inner = QPainterPath()
        inner.addRoundedRect(panel.adjusted(3, 3, -3, -3), 12, 12)
        p.drawPath(inner)

        self._draw_cassette(p, CASSETTE_RECT)

    def _draw_cassette(self, p, rect):
        w = rect.width()
        h = rect.height()
        left = rect.left()
        top = rect.top()
        right = rect.right()
        bottom = rect.bottom()
        cx = left + w / 2

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 55))
        sh_path = QPainterPath()
        sh_path.addRoundedRect(rect.adjusted(4, 7, 4, 9), 9, 9)
        p.drawPath(sh_path)
        p.setBrush(QColor(0, 0, 0, 25))
        sh_path2 = QPainterPath()
        sh_path2.addRoundedRect(rect.adjusted(7, 10, 7, 12), 11, 11)
        p.drawPath(sh_path2)

        cg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        cg.setColorAt(0.0, QColor("#FDF7E8"))
        cg.setColorAt(0.35, QColor(C["cass_1"]))
        cg.setColorAt(0.75, QColor(C["cass_2"]))
        cg.setColorAt(1.0, QColor("#D2C1A0"))
        cpath = QPainterPath()
        cpath.addRoundedRect(rect, 8, 8)
        p.setBrush(cg)
        p.setPen(QPen(QColor(C["cass_border"]), 2.5))
        p.drawPath(cpath)

        p.setBrush(Qt.NoBrush)
        hl_path = QPainterPath()
        hl_path.addRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
        p.setPen(QPen(QColor(255, 255, 255, 130), 1.5))
        p.drawPath(hl_path)

        sh_in = QPainterPath()
        sh_in.addRoundedRect(rect.adjusted(3, 3, -3, -3), 5, 5)
        p.setPen(QPen(QColor(0, 0, 0, 55), 1))
        p.drawPath(sh_in)

        shine = QPainterPath()
        shine.addRoundedRect(QRectF(left + 8, top + 5, w - 16, 12), 6, 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 80))
        p.drawPath(shine)

        stripe_h = h * 0.20
        stripe_rect = QRectF(left + 4, bottom - stripe_h - 4, w - 8, stripe_h)
        spath = QPainterPath()
        spath.addRoundedRect(stripe_rect, 4, 4)
        sg = QLinearGradient(stripe_rect.topLeft(), stripe_rect.bottomLeft())
        sg.setColorAt(0, QColor("#d47a4e"))
        sg.setColorAt(1, QColor("#c5613a"))
        p.setBrush(sg)
        p.setPen(Qt.NoPen)
        p.drawPath(spath)
        p.setBrush(QColor(255, 255, 255, 50))
        p.drawRoundedRect(QRectF(stripe_rect.left() + 2, stripe_rect.top() + 1,
                                 stripe_rect.width() - 4, 3), 1.5, 1.5)

        reel_cy = top + h * 0.36
        reel_r = h * 0.20
        bridge_w = w * 0.42
        reel_cx1 = cx - bridge_w * 0.28
        reel_cx2 = cx + bridge_w * 0.28

        win_margin_v = 18
        win_margin_h = 22
        win_cx = cx
        win_cy = reel_cy
        reel_outer_x = max(abs(reel_cx1 - cx), abs(reel_cx2 - cx)) + reel_r
        win_w = 2 * (reel_outer_x + win_margin_h)
        win_h = 2 * (reel_r + win_margin_v)
        win_top = win_cy - win_h / 2
        win_bottom = win_cy + win_h / 2
        win_rect = QRectF(win_cx - win_w / 2, win_top, win_w, win_h)

        trap_top = win_bottom + 4
        trap_bottom = bottom - stripe_h - 4
        trap_h = trap_bottom - trap_top

        trap_top_w = w * 0.55
        trap_bot_w = w * 0.68

        if trap_h > 4:
            trap = QPolygonF([
                QPointF(cx - trap_top_w / 2, trap_top),
                QPointF(cx + trap_top_w / 2, trap_top),
                QPointF(cx + trap_bot_w / 2, trap_bottom),
                QPointF(cx - trap_bot_w / 2, trap_bottom),
            ])
            p.setPen(QPen(QColor("#c9baa3"), 1.5))
            p.setBrush(QColor(245, 235, 215, 120))
            p.drawPolygon(trap)

        wp = QPainterPath()
        wp.addRoundedRect(win_rect, 8, 8)
        p.setPen(QPen(QColor(C["cass_border"]), 2))
        p.setBrush(QColor("#F0E6CE"))
        p.drawPath(wp)

        bridge_h = reel_r * 1.4
        bridge_rect = QRectF(reel_cx1, reel_cy - bridge_h / 2,
                             reel_cx2 - reel_cx1, bridge_h)
        bp = QPainterPath()
        bp.addRoundedRect(bridge_rect, 8, 8)
        p.setBrush(QColor("#422d21"))
        p.setPen(QPen(QColor("#2b1c14"), 1.5))
        p.drawPath(bp)

        tape_strip = QRectF(reel_cx1, reel_cy - 3,
                            reel_cx2 - reel_cx1, 6)
        p.setBrush(QColor(C["tape_brown"]))
        p.setPen(Qt.NoPen)
        p.drawRect(tape_strip)
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRect(QRectF(reel_cx1, reel_cy - 2,
                          reel_cx2 - reel_cx1, 1.5))

        self._draw_reel(p, QPointF(reel_cx1, reel_cy), reel_r, direction=1)
        self._draw_reel(p, QPointF(reel_cx2, reel_cy), reel_r, direction=-1)

        if trap_h > 6:
            hole_y = trap_top + trap_h * 0.55
            p.setBrush(QColor("#2d2118"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx - trap_top_w * 0.35, hole_y), 5.5, 5.5)
            p.drawEllipse(QPointF(cx + trap_top_w * 0.35, hole_y), 5.5, 5.5)
            sq = 8
            p.drawRoundedRect(
                QRectF(cx - trap_top_w * 0.18 - sq / 2,
                       hole_y - sq / 2, sq, sq), 1.5, 1.5)
            p.drawRoundedRect(
                QRectF(cx + trap_top_w * 0.18 - sq / 2,
                       hole_y - sq / 2, sq, sq), 1.5, 1.5)

        screw_y_bottom = bottom - stripe_h - 12
        for sx, sy in [
            (left + 16, top + 16),
            (right - 16, top + 16),
            (left + 16, screw_y_bottom),
            (right - 16, screw_y_bottom),
            (cx, trap_top + 10),
        ]:
            p.setBrush(QColor(60, 55, 50, 80))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(sx, sy), 7, 7)
            p.setBrush(QColor(120, 115, 108))
            p.drawEllipse(QPointF(sx, sy), 5.5, 5.5)
            p.setBrush(QColor(60, 55, 50))
            p.drawEllipse(QPointF(sx, sy), 3, 3)
            p.setBrush(QColor(200, 195, 185, 150))
            p.drawEllipse(QPointF(sx - 1.5, sy - 1.5), 1, 1)
            p.setPen(QPen(QColor(180, 175, 168), 1.2))
            p.drawLine(QPointF(sx - 3.5, sy), QPointF(sx + 3.5, sy))
            p.drawLine(QPointF(sx, sy - 3.5), QPointF(sx, sy + 3.5))

    def _draw_reel(self, p, center, r, direction=1):
        tg = QRadialGradient(QPointF(center.x() - r * 0.2,
                                      center.y() - r * 0.2), r * 1.3)
        tg.setColorAt(0, QColor("#8A6B50"))
        tg.setColorAt(1, QColor(C["tape_brown"]))
        p.setBrush(tg)
        p.setPen(QPen(QColor("#2b1a11"), 2))
        p.drawEllipse(center, r, r)

        p.setPen(QPen(QColor(C["cass_border"]), 1.5))
        p.setBrush(QColor("#fcfaf2"))
        p.drawEllipse(center, r * 0.52, r * 0.52)

        p.save()
        p.translate(center)
        p.rotate(self._rotation * direction)
        p.setBrush(QColor(C["tape_brown_d"]))
        p.setPen(Qt.NoPen)
        for i in range(3):
            p.save()
            p.rotate(i * 120)
            spoke_rect = QRectF(-2.5, -r * 0.48, 5, r * 0.17)
            p.drawRoundedRect(spoke_rect, 1.5, 1.5)
            p.restore()
        p.restore()

        p.setBrush(QColor("#1f140d"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(center, r * 0.32, r * 0.32)

        p.setBrush(QColor(255, 255, 255, 40))
        hl_r = r * 0.18
        p.drawEllipse(QPointF(center.x() - r * 0.12,
                              center.y() - r * 0.12), hl_r, hl_r)

    def _draw_eq_panel(self, p, W, H):
        panel = EQ_PANEL

        pg = QLinearGradient(0, panel.top(), 0, panel.bottom())
        pg.setColorAt(0, QColor(C["cream_1"]))
        pg.setColorAt(1, QColor(C["cream_2"]))
        path = QPainterPath()
        path.addRoundedRect(panel, 14, 14)
        p.setBrush(pg)
        p.setPen(QPen(QColor(180, 165, 140, 100), 1.5))
        p.drawPath(path)

        p.setPen(QColor(C["text_dark"]))
        f = QFont("Georgia", 11, QFont.Bold)
        p.setFont(f)
        p.drawText(QRectF(panel.left() + 15, panel.top() + 6, 120, 22),
                   Qt.AlignLeft | Qt.AlignVCenter, "Equalizer")

        reset_rect = QRectF(panel.right() - 75, panel.top() + 8, 60, 22)
        self._hit_reset_eq = reset_rect
        p.setBrush(QColor(C["cream_3"]))
        p.setPen(QPen(QColor(180, 165, 140, 100), 1))
        rp = QPainterPath()
        rp.addRoundedRect(reset_rect, 6, 6)
        p.drawPath(rp)
        p.setPen(QColor(C["text_dark"]))
        f = QFont("Segoe UI", 9, QFont.Bold)
        p.setFont(f)
        p.drawText(reset_rect, Qt.AlignCenter, "Reset")

        p.setPen(QColor(C["text_muted"]))
        f = QFont("Segoe UI", 7)
        p.setFont(f)
        p.drawText(QRectF(panel.left() + 8, EQ_TRACK_TOP - 8, 30, 14),
                   Qt.AlignRight | Qt.AlignVCenter, "+12")
        p.drawText(QRectF(panel.left() + 8,
                          (EQ_TRACK_TOP + EQ_TRACK_BOTTOM) // 2 - 7, 30, 14),
                   Qt.AlignRight | Qt.AlignVCenter, "0")
        p.drawText(QRectF(panel.left() + 8, EQ_TRACK_BOTTOM - 6, 30, 14),
                   Qt.AlignRight | Qt.AlignVCenter, "\u221212")

        track_w = 6
        for i in range(EQ_BAND_COUNT):
            cx = EQ_FADER_X_START + i * EQ_FADER_X_STEP
            gain = self.eq_gains[i]
            handle_y = eq_gain_to_y(gain)

            p.setBrush(QColor(220, 205, 180))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(cx - track_w / 2, EQ_TRACK_TOP,
                                     track_w, EQ_TRACK_H), 3, 3)

            p.setBrush(QColor(200, 185, 160))
            p.drawRoundedRect(QRectF(cx - track_w / 2 + 1.5, EQ_TRACK_TOP + 2,
                                     track_w - 3, EQ_TRACK_H - 4), 2, 2)

            if handle_y < EQ_TRACK_BOTTOM - 2:
                fill_h = EQ_TRACK_BOTTOM - handle_y
                fg = QLinearGradient(cx, handle_y, cx, EQ_TRACK_BOTTOM)
                fg.setColorAt(0, QColor(C["orange_1"]))
                fg.setColorAt(1, QColor(C["orange_2"]))
                p.setBrush(fg)
                p.drawRoundedRect(QRectF(cx - track_w / 2, handle_y,
                                         track_w, fill_h), 3, 3)

            handle_w = 18
            handle_h = 22
            handle_rect = QRectF(cx - handle_w / 2, handle_y - handle_h / 2,
                                 handle_w, handle_h)

            p.setBrush(QColor(0, 0, 0, 45))
            p.drawRoundedRect(handle_rect.adjusted(1, 2, 1, 2), 9, 9)

            hg = QLinearGradient(0, handle_rect.top(), 0, handle_rect.bottom())
            hg.setColorAt(0, QColor("#FDF7E8"))
            hg.setColorAt(1, QColor(C["cream_2"]))
            p.setBrush(hg)
            p.setPen(QPen(QColor(C["cass_border"]), 1.5))
            p.drawRoundedRect(handle_rect, 9, 9)

            p.setPen(QPen(QColor(C["orange_1"]), 2.5))
            p.drawLine(QPointF(cx - 4, handle_y), QPointF(cx + 4, handle_y))
            p.setPen(Qt.NoPen)

            if gain != 0:
                p.setPen(QColor(C["text_dark"]))
                f = QFont("Consolas", 7, QFont.Bold)
                p.setFont(f)
                txt = f"{gain:+d}"
                p.drawText(QRectF(cx - 20, handle_y - 26, 40, 14),
                           Qt.AlignCenter, txt)

            p.setPen(QColor(C["text_dark"]))
            f = QFont("Segoe UI", 8, QFont.Bold)
            p.setFont(f)
            p.drawText(QRectF(cx - 25, EQ_TRACK_BOTTOM + 8, 50, 16),
                       Qt.AlignCenter, EQ_FREQ_LABELS[i])

            hit = QRectF(cx - 22, EQ_TRACK_TOP - 12, 44, EQ_TRACK_H + 30)
            self._hit_eq_bands.append((i, hit))

    def _draw_playlist_panel(self, p, W, H):
        panel = PLAYLIST_PANEL
        alpha = 170
        c1 = QColor(C["cream_1"]); c1.setAlpha(alpha)
        c2 = QColor(C["cream_2"]); c2.setAlpha(alpha)
        pg = QLinearGradient(0, panel.top(), 0, panel.bottom())
        pg.setColorAt(0, c1)
        pg.setColorAt(1, c2)
        path = QPainterPath()
        path.addRoundedRect(panel, 14, 14)
        p.setBrush(pg)
        p.setPen(QPen(QColor(180, 165, 140, 120), 1.5))
        p.drawPath(path)

        p.setPen(QColor(C["text_dark"]))
        f = QFont("Georgia", 13, QFont.Bold)
        p.setFont(f)
        p.drawText(QRectF(panel.left() + 20, panel.top() + 16, 200, 24),
                   Qt.AlignLeft | Qt.AlignVCenter, "Playlist")

        n = len(self.playlist)
        tracks_label = f"{n} track" if n == 1 else f"{n} tracks"
        total_ms = sum(t.get("duration", 0) for t in self.playlist)
        if total_ms > 0 and n > 0:
            tracks_label += f"  \u00B7  {fmt_duration(total_ms)}"

        p.setPen(QColor(C["text_time"]))
        f = QFont("Segoe UI", 9)
        p.setFont(f)
        p.drawText(QRectF(panel.left() + 20, panel.top() + 16,
                          panel.width() - 40, 24),
                   Qt.AlignRight | Qt.AlignVCenter, tracks_label)

        p.setPen(QPen(QColor(180, 165, 140, 80), 1))
        p.drawLine(int(panel.left() + 18), int(panel.top() + 48),
                   int(panel.right() - 18), int(panel.top() + 48))

        list_y = panel.top() + 58
        row_h = 42
        max_rows = int((panel.height() - 70) / row_h)

        if not self.playlist:
            p.setPen(QColor(C["text_muted"]))
            f = QFont("Segoe UI", 10)
            f.setItalic(True)
            p.setFont(f)
            p.drawText(QRectF(panel.left(), panel.top() + 100,
                              panel.width(), 60),
                       Qt.AlignCenter | Qt.TextWordWrap,
                       "Belum ada lagu.\nKlik + untuk menambah,\natau drag file ke sini.")

            add_size = 64
            add_x = panel.center().x() - add_size / 2
            add_y = panel.top() + 190
            self._hit_add = QRectF(add_x, add_y, add_size, add_size)

            p.setBrush(QColor(C["orange_1"]))
            p.setPen(Qt.NoPen)
            p.drawEllipse(self._hit_add)
            p.setPen(QPen(QColor(C["text_light"]), 4))
            p.drawLine(QPointF(add_x + 18, add_y + 32), QPointF(add_x + 46, add_y + 32))
            p.drawLine(QPointF(add_x + 32, add_y + 18), QPointF(add_x + 32, add_y + 46))
            return

        for i, track in enumerate(self.playlist[:max_rows]):
            row = QRectF(panel.left() + 10, list_y + i * row_h,
                         panel.width() - 20, row_h - 2)

            if i == self._current_index:
                hp = QPainterPath()
                hp.addRoundedRect(row, 8, 8)
                hl_color = QColor(C["peach_row"]); hl_color.setAlpha(200)
                p.setBrush(hl_color)
                p.setPen(Qt.NoPen)
                p.drawPath(hp)

            num_x = row.left() + 14
            num_y = row.center().y()
            if i == self._current_index and self._playing:
                p.setBrush(QColor(C["orange_1"]))
                p.setPen(Qt.NoPen)
                for k in range(3):
                    h_k = 6 + (k * 3)
                    p.drawRoundedRect(QRectF(num_x - 4 + k * 4,
                                             num_y - h_k / 2, 2.5, h_k), 1, 1)
            else:
                p.setPen(QColor(C["text_muted"]))
                f = QFont("Arial", 10)
                p.setFont(f)
                p.drawText(QRectF(num_x - 8, num_y - 8, 18, 16),
                           Qt.AlignCenter, str(i + 1))

            title = track["title"]
            if len(title) > 32:
                title = title[:31] + "\u2026"
            p.setPen(QColor(C["text_dark"]))
            f = QFont("Segoe UI", 10, QFont.Bold)
            p.setFont(f)

            artist = clean_artist(track.get("artist", ""))

            if artist:
                p.drawText(QRectF(row.left() + 40, row.top() + 6,
                                  row.width() - 130, 18),
                           Qt.AlignLeft | Qt.AlignVCenter, title)
                if len(artist) > 34:
                    artist = artist[:33] + "\u2026"
                p.setPen(QColor(C["text_muted"]))
                f = QFont("Segoe UI", 8)
                p.setFont(f)
                p.drawText(QRectF(row.left() + 40, row.top() + 22,
                                  row.width() - 130, 16),
                           Qt.AlignLeft | Qt.AlignVCenter, artist)
            else:
                p.drawText(QRectF(row.left() + 40, row.top(),
                                  row.width() - 130, row.height()),
                           Qt.AlignLeft | Qt.AlignVCenter, title)

            dur = fmt_duration(track["duration"]) if track["duration"] else ""
            p.setPen(QColor(C["text_time"]))
            f = QFont("Consolas", 9)
            p.setFont(f)
            p.drawText(QRectF(row.right() - 78, row.top(),
                              44, row.height()),
                       Qt.AlignRight | Qt.AlignVCenter, dur)

            del_rect = QRectF(row.right() - 26, row.center().y() - 10, 20, 20)
            if i == self._hover_delete_idx:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(180, 165, 140, 220))
                p.drawEllipse(del_rect)
                p.setPen(QColor(C["text_dark"]))
                f = QFont("Segoe UI", 10, QFont.Bold)
                p.setFont(f)
                p.drawText(del_rect, Qt.AlignCenter, "\u00D7")

            self._hit_track_delete.append((i, del_rect))
            self._hit_tracks.append((i, row))

    def _draw_bottom_bar(self, p, W, H):
        bar = BOTTOM_BAR
        bar_top = bar.top()
        bar_h = bar.height()

        alpha = 170
        c1 = QColor(C["cream_1"]); c1.setAlpha(alpha)
        c2 = QColor(C["cream_3"]); c2.setAlpha(alpha)
        bg = QLinearGradient(0, bar.top(), 0, bar.bottom())
        bg.setColorAt(0, c1)
        bg.setColorAt(1, c2)
        path = QPainterPath()
        path.addRoundedRect(bar, 14, 14)
        p.setBrush(bg)
        p.setPen(QPen(QColor(180, 165, 140, 120), 1.5))
        p.drawPath(path)

        art_size = 110
        art_x = bar.left() + 24
        art_y = bar_top + (bar_h - art_size) / 2
        art_rect = QRectF(art_x, art_y, art_size, art_size)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 55))
        sh_art = QPainterPath()
        sh_art.addRoundedRect(art_rect.adjusted(3, 4, 3, 4), 12, 12)
        p.drawPath(sh_art)

        ap = QPainterPath()
        ap.addRoundedRect(art_rect, 10, 10)
        p.setBrush(QColor(C["cass_border"]))
        p.drawPath(ap)

        current = self.playlist[self._current_index] if 0 <= self._current_index < len(self.playlist) else None
        if current and current.get("cover") and not current["cover"].isNull():
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(art_rect.adjusted(3, 3, -3, -3), 8, 8)
            p.setClipPath(clip)
            p.drawPixmap(art_rect.adjusted(3, 3, -3, -3).toRect(),
                         current["cover"])
            p.restore()
        else:
            ph = QLinearGradient(art_rect.topLeft(), art_rect.bottomRight())
            ph.setColorAt(0, QColor(C["orange_soft"]))
            ph.setColorAt(1, QColor(C["orange_2"]))
            p.setBrush(ph)
            ph_p = QPainterPath()
            ph_p.addRoundedRect(art_rect.adjusted(3, 3, -3, -3), 8, 8)
            p.drawPath(ph_p)
            p.setPen(QColor(255, 255, 255, 200))
            f = QFont("Georgia", 44)
            p.setFont(f)
            p.drawText(art_rect, Qt.AlignCenter, "\u266B")

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(C["cream_1"]), 2))
        border_art = QPainterPath()
        border_art.addRoundedRect(art_rect, 10, 10)
        p.drawPath(border_art)

        txt_x = art_rect.right() + 22
        txt_w = 300

        title = current["title"] if current else "\u2014"
        p.setPen(QColor(C["text_dark"]))
        f = QFont("Georgia", 15, QFont.Bold)
        p.setFont(f)
        fm = p.fontMetrics()
        elided_title = fm.elidedText(title, Qt.ElideRight, int(txt_w))
        p.drawText(QRectF(txt_x, art_y + 6, txt_w, 24),
                   Qt.AlignLeft | Qt.AlignVCenter, elided_title)

        artist = clean_artist(current.get("artist", "")) if current else ""
        if artist:
            p.setPen(QColor(C["text_muted"]))
            f = QFont("Segoe UI", 10)
            p.setFont(f)
            fm = p.fontMetrics()
            elided_artist = fm.elidedText(artist, Qt.ElideRight, int(txt_w))
            p.drawText(QRectF(txt_x, art_y + 32, txt_w, 18),
                       Qt.AlignLeft | Qt.AlignVCenter, elided_artist)

        prog_y = art_y + 66
        prog_rect = QRectF(txt_x, prog_y, txt_w, 5)
        self._hit_progress = QRectF(txt_x - 6, prog_y - 10, txt_w + 12, 25)

        p.setBrush(QColor(C["cream_track"]))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(prog_rect, 2.5, 2.5)

        pos = self.player.get_position() if current else 0.0
        if pos < 0: pos = 0.0
        fill_w = prog_rect.width() * pos
        if fill_w > 0.5:
            fill = QRectF(prog_rect.left(), prog_rect.top(),
                          fill_w, prog_rect.height())
            p.setBrush(QColor(C["orange_1"]))
            p.drawRoundedRect(fill, 2.5, 2.5)

        thumb_x = prog_rect.left() + fill_w
        thumb_y = prog_rect.center().y()
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor(C["orange_1"]), 2))
        p.drawEllipse(QPointF(thumb_x, thumb_y), 7, 7)

        cur_ms = max(0, self.player.get_time()) if current else 0
        dur_ms = self.player.get_length() if current else 0
        p.setPen(QColor(C["text_time"]))
        f = QFont("Consolas", 9)
        p.setFont(f)
        p.drawText(QRectF(txt_x, prog_y + 12, 80, 16),
                   Qt.AlignLeft, fmt_duration(cur_ms))
        p.drawText(QRectF(txt_x + txt_w - 60, prog_y + 12, 60, 16),
                   Qt.AlignRight, fmt_duration(dur_ms))

        div1_x = 500
        p.setPen(QPen(QColor(180, 165, 140, 90), 1))
        p.drawLine(QPointF(div1_x, bar_top + 30),
                   QPointF(div1_x, bar.bottom() - 30))
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.drawLine(QPointF(div1_x + 1, bar_top + 30),
                   QPointF(div1_x + 1, bar.bottom() - 30))

        ctrl_cy = bar_top + bar_h / 2
        ctrl_cx = 660

        sh_x = ctrl_cx - 120
        self._draw_round_ctrl(p, QPointF(sh_x, ctrl_cy), 22,
                              "shuffle", self._shuffle)
        self._hit_shuffle = QRectF(sh_x - 22, ctrl_cy - 22, 44, 44)

        prev_x = ctrl_cx - 60
        self._draw_round_ctrl(p, QPointF(prev_x, ctrl_cy), 22,
                              "prev", False)
        self._hit_prev = QRectF(prev_x - 22, ctrl_cy - 22, 44, 44)

        play_r = 32
        self._draw_play_button_3d(p, QPointF(ctrl_cx, ctrl_cy), play_r)
        self._hit_play = QRectF(ctrl_cx - play_r, ctrl_cy - play_r,
                                play_r * 2, play_r * 2)

        next_x = ctrl_cx + 60
        self._draw_round_ctrl(p, QPointF(next_x, ctrl_cy), 22,
                              "next", False)
        self._hit_next = QRectF(next_x - 22, ctrl_cy - 22, 44, 44)

        rp_x = ctrl_cx + 120
        self._draw_round_ctrl(p, QPointF(rp_x, ctrl_cy), 22,
                              "repeat", self._repeat)
        self._hit_repeat = QRectF(rp_x - 22, ctrl_cy - 22, 44, 44)

        div2_x = 810
        p.setPen(QPen(QColor(180, 165, 140, 90), 1))
        p.drawLine(QPointF(div2_x, bar_top + 30),
                   QPointF(div2_x, bar.bottom() - 30))
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.drawLine(QPointF(div2_x + 1, bar_top + 30),
                   QPointF(div2_x + 1, bar.bottom() - 30))

        viz_rect = QRectF(825, bar_top + 30, 170, 60)
        p.setBrush(QColor(C["cream_2"]))
        p.setPen(QPen(QColor(180, 165, 140, 100), 1))
        viz_border = QPainterPath()
        viz_border.addRoundedRect(viz_rect, 8, 8)
        p.drawPath(viz_border)
        self._draw_visualizer(p, viz_rect.adjusted(8, 8, -8, -8))

        vol_y = bar_top + 115
        vol_x = 825
        vol_w = 160

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["text_dark"]))
        spk_path = QPainterPath()
        spk_path.moveTo(vol_x, vol_y + 8)
        spk_path.lineTo(vol_x + 7, vol_y + 8)
        spk_path.lineTo(vol_x + 14, vol_y)
        spk_path.lineTo(vol_x + 14, vol_y + 20)
        spk_path.lineTo(vol_x + 7, vol_y + 12)
        spk_path.lineTo(vol_x, vol_y + 12)
        spk_path.closeSubpath()
        p.drawPath(spk_path)
        p.setPen(QPen(QColor(C["text_dark"]), 1.5))
        p.drawArc(QRectF(vol_x + 12, vol_y + 2, 10, 16), -60 * 16, 120 * 16)

        vol_slider = QRectF(vol_x + 32, vol_y + 7, vol_w, 6)
        self._hit_volume = QRectF(vol_x + 28, vol_y - 8, vol_w + 50, 30)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["cream_track"]))
        p.drawRoundedRect(vol_slider, 3, 3)

        fill_w = vol_slider.width() * (self._volume / 100.0)
        if fill_w > 0.5:
            p.setBrush(QColor(C["orange_1"]))
            p.drawRoundedRect(QRectF(vol_slider.left(), vol_slider.top(),
                                     fill_w, vol_slider.height()), 3, 3)

        thumb_x = vol_slider.left() + fill_w
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor(C["orange_1"]), 1.5))
        p.drawEllipse(QPointF(thumb_x, vol_slider.center().y()), 8, 8)

        p.setPen(QColor(C["text_time"]))
        f = QFont("Segoe UI", 9)
        p.setFont(f)
        p.drawText(QRectF(vol_slider.right() + 8, vol_y, 50, 22),
                   Qt.AlignLeft | Qt.AlignVCenter, f"{self._volume}%")

    def _draw_round_ctrl(self, p, center, r, kind, active):
        cx, cy = center.x(), center.y()

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawEllipse(QPointF(cx, cy + 2), r, r)

        if active:
            g = QLinearGradient(cx, cy - r, cx, cy + r)
            g.setColorAt(0, QColor("#FFB896"))
            g.setColorAt(1, QColor("#C26B44"))
            p.setBrush(g)
            p.setPen(Qt.NoPen)
        else:
            p.setBrush(QColor(C["cream_1"]))
            p.setPen(QPen(QColor(200, 185, 160), 1))
        p.drawEllipse(center, r, r)

        icon_col = QColor(C["text_light"]) if active else QColor(C["text_dark"])
        p.setPen(icon_col)
        if kind == "shuffle":
            f = QFont("Segoe MDL2 Assets", 10)
            p.setFont(f)
            p.drawText(QRectF(cx - r, cy - r, r * 2, r * 2),
                       Qt.AlignCenter, "\uE8B1")
        elif kind == "prev":
            f = QFont("Segoe MDL2 Assets", 11)
            p.setFont(f)
            p.drawText(QRectF(cx - r, cy - r, r * 2, r * 2),
                       Qt.AlignCenter, "\uE892")
        elif kind == "next":
            f = QFont("Segoe MDL2 Assets", 11)
            p.setFont(f)
            p.drawText(QRectF(cx - r, cy - r, r * 2, r * 2),
                       Qt.AlignCenter, "\uE893")
        elif kind == "repeat":
            f = QFont("Segoe MDL2 Assets", 10)
            p.setFont(f)
            p.drawText(QRectF(cx - r, cy - r, r * 2, r * 2),
                       Qt.AlignCenter, "\uE8EE")

    def _draw_play_button_3d(self, p, center, r):
        cx, cy = center.x(), center.y()

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(90, 58, 40, 100))
        p.drawEllipse(QPointF(cx, cy + 4), r, r)

        p.setBrush(QColor(C["btn_3d_bot"]))
        p.drawEllipse(center, r + 1, r + 1)

        g = QRadialGradient(
            QPointF(cx - r * 0.3, cy - r * 0.35), r * 1.6)
        g.setColorAt(0, QColor("#FAD0B2"))
        g.setColorAt(0.4, QColor(C["btn_3d_top"]))
        g.setColorAt(0.7, QColor(C["btn_3d_mid"]))
        g.setColorAt(1, QColor(C["btn_3d_bot"]))
        p.setBrush(g)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy - 1), r, r)

        hl_r = r - 6
        hl_rect = QRectF(cx - hl_r, cy - 1 - hl_r, hl_r * 2, hl_r * 2)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 160), 2.5))
        p.drawArc(hl_rect, 65 * 16, 55 * 16)

        p.setBrush(QColor("white"))
        p.setPen(Qt.NoPen)
        if self._playing:
            p.drawRoundedRect(QRectF(cx - 8, cy - 1 - 10, 6, 20), 2, 2)
            p.drawRoundedRect(QRectF(cx + 2, cy - 1 - 10, 6, 20), 2, 2)
        else:
            tri = QPolygonF([
                QPointF(cx - 7, cy - 1 - 11),
                QPointF(cx + 11, cy - 1),
                QPointF(cx - 7, cy - 1 + 11),
            ])
            p.drawPolygon(tri)

    def _draw_visualizer(self, p, rect):
        n = 24
        gap = 2
        bar_w = (rect.width() - (n - 1) * gap) / n

        for i in range(n):
            v = float(self.viz_smooth[int(i * 32 / n)])
            peak = float(self.viz_peak[int(i * 32 / n)])
            h = v * rect.height()
            x = rect.left() + i * (bar_w + gap)
            y = rect.bottom() - h

            if h > 0.5:
                p.setBrush(QColor(C["vis_bar"]))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(QRectF(x, y, bar_w, h), 1.5, 1.5)

            if peak > 0.03:
                py = rect.bottom() - peak * rect.height() - 2
                p.setBrush(QColor(C["vis_peak"]))
                p.drawRoundedRect(QRectF(x, py, bar_w, 2), 1, 1)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        pos = e.position()

        if self._hit_reset_eq.contains(pos):
            self._reset_eq()
            return

        for idx, rect in self._hit_eq_bands:
            if rect.contains(pos):
                self._dragging_eq = idx
                self._set_eq_from_y(idx, pos.y())
                return

        if self._hit_add.contains(pos):
            self._open_files(); return

        if self._hover_delete_idx >= 0:
            for idx, rect in self._hit_track_delete:
                if idx == self._hover_delete_idx and rect.contains(pos):
                    self._remove_track(idx)
                    return

        for idx, rect in self._hit_tracks:
            if rect.contains(pos):
                self._play_index(idx); return

        if self._hit_play.contains(pos):
            self._toggle_play(); return
        if self._hit_prev.contains(pos):
            self._prev(); return
        if self._hit_next.contains(pos):
            self._next(); return
        if self._hit_shuffle.contains(pos):
            self._toggle_shuffle(); return
        if self._hit_repeat.contains(pos):
            self._toggle_repeat(); return

        if self._hit_progress.contains(pos):
            self._seeking = True
            self._seek_from_x(pos.x(), self._hit_progress)
            return

        if self._hit_volume.contains(pos):
            self._set_volume_from_x(pos.x(), self._hit_volume)
            return

        self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        pos = e.position()

        new_hover = -1
        for idx, rect in self._hit_track_delete:
            if rect.contains(pos):
                new_hover = idx
                break
        if new_hover != self._hover_delete_idx:
            self._hover_delete_idx = new_hover
            self.update()

        if self._dragging_eq >= 0:
            self._set_eq_from_y(self._dragging_eq, pos.y())
            return
        if self._seeking:
            self._seek_from_x(pos.x(), self._hit_progress)
            return
        if e.buttons() & Qt.LeftButton:
            if self._hit_volume.contains(pos):
                self._set_volume_from_x(pos.x(), self._hit_volume)
                return
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._seeking = False
        self._dragging_eq = -1

    def closeEvent(self, e):
        try: self.capture.stop()
        except Exception: pass
        try: self.player.stop()
        except Exception: pass
        try:
            if self._eq_obj is not None:
                vlc.libvlc_audio_equalizer_release(self._eq_obj)
        except Exception: pass
        e.accept()


def main():
    app = QApplication(sys.argv)
    w = RetroPlayer()
    w.show()
    w.setFocus()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()