"""
SiteSync AI — Voice Input Agent

Provides speech-to-text transcription for field supervisor voice input.
Priority:
  1. faster-whisper (offline, local)
  2. SpeechRecognition + Google STT (requires internet)
  3. Text-only fallback
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

def transcribe_audio(audio_path: str | Path) -> Optional[str]:
    """Transcribe an audio file to text."""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        console.print(f"[red]Audio file not found: {audio_path}[/red]")
        return None

    result = _transcribe_whisper(audio_path)
    if result is not None:
        return result

    result = _transcribe_speech_recognition(audio_path)
    if result is not None:
        return result

    console.print("[yellow]⚠ Voice transcription not available. Please type your update.[/yellow]")
    return None

def _transcribe_whisper(audio_path: Path) -> Optional[str]:
    try:
        from faster_whisper import WhisperModel

        console.print("[dim]🎤 Transcribing with Whisper (offline)...[/dim]")
        model = WhisperModel("base", device="cpu", compute_type="int8")

        segments, info = model.transcribe(
            str(audio_path),
            language="en",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=(
                "Construction progress report. WBS, formwork, reinforcement, concreting, "
                "earthworks, piping, spool, CPM schedule, discipline, zone, percent complete."
            ),
        )

        text = " ".join(seg.text.strip() for seg in segments)
        console.print(f"[green]✅ Whisper transcription: {text[:80]}...[/green]")
        return text.strip() if text.strip() else None

    except ImportError:
        console.print("[dim]faster-whisper not installed, trying fallback...[/dim]")
        return None
    except Exception as e:
        console.print(f"[yellow]Whisper error: {e}[/yellow]")
        return None

def _transcribe_speech_recognition(audio_path: Path) -> Optional[str]:
    try:
        import speech_recognition as sr

        console.print("[dim]🎤 Transcribing with Google STT...[/dim]")
        recognizer = sr.Recognizer()

        wav_path = audio_path
        if audio_path.suffix.lower() not in ('.wav',):
            try:
                import subprocess
                wav_path = audio_path.with_suffix('.wav')
                subprocess.run(['ffmpeg', '-i', str(audio_path), str(wav_path), '-y'], capture_output=True, timeout=30)
            except Exception:
                pass

        with sr.AudioFile(str(wav_path)) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)
        console.print(f"[green]✅ Google STT: {text[:80]}[/green]")
        return text

    except ImportError:
        console.print("[dim]SpeechRecognition not installed.[/dim]")
        return None
    except Exception as e:
        console.print(f"[yellow]Google STT error: {e}[/yellow]")
        return None

def is_voice_available() -> bool:
    try:
        import faster_whisper
        return True
    except ImportError:
        pass
    try:
        import speech_recognition
        return True
    except ImportError:
        pass
    return False
