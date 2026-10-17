"""Voz: transcrição (WAV -> texto) e síntese (texto -> áudio).

O Streamlit entrega a gravação do microfone como WAV. Este módulo:
  1. normaliza o WAV para PCM 16-bit (formato que as bibliotecas de STT aceitam);
  2. transcreve com o motor escolhido em STT_ENGINE.

Motores de transcrição (variável de ambiente STT_ENGINE):
  - "google" (padrão): API web gratuita via SpeechRecognition. Sem chave, precisa de internet.
  - "openai": Whisper da OpenAI. Precisa de OPENAI_API_KEY. Mais preciso em português.

Para trocar por outro motor (faster-whisper local, etc.), basta criar uma função
_stt_xxx(wav_bytes, language) -> str e registrá-la em _ENGINES.
"""

import io
import os


class TranscriptionError(Exception):
    """Falha ao transcrever (sem internet, áudio ilegível, chave ausente...)."""


def _to_pcm16_wav(audio_bytes: bytes) -> bytes:
    """Converte qualquer WAV (float, estéreo, 24-bit...) para WAV PCM 16-bit."""
    import soundfile as sf

    try:
        data, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="int16")
    except Exception as exc:  # áudio corrompido ou formato não suportado
        raise TranscriptionError(f"Não consegui ler o áudio gravado: {exc}") from exc

    out = io.BytesIO()
    sf.write(out, data, sample_rate, format="WAV", subtype="PCM_16")
    return out.getvalue()


def _stt_google(wav_bytes: bytes, language: str) -> str:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        return ""  # nada reconhecido
    except sr.RequestError as exc:
        raise TranscriptionError(f"Serviço de transcrição indisponível (internet?): {exc}") from exc


def _stt_openai(wav_bytes: bytes, language: str) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise TranscriptionError("STT_ENGINE=openai exige a variável OPENAI_API_KEY.")
    from openai import OpenAI

    client = OpenAI()
    try:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", wav_bytes, "audio/wav"),
            language=language.split("-")[0],
        )
    except Exception as exc:
        raise TranscriptionError(f"Erro na API de transcrição: {exc}") from exc
    return result.text


_ENGINES = {"google": _stt_google, "openai": _stt_openai}


def transcribe(audio_bytes: bytes, language: str = "pt-BR") -> str:
    """Recebe os bytes do WAV gravado e devolve o texto ('' se não entendeu nada)."""
    engine = os.getenv("STT_ENGINE", "google").lower()
    if engine not in _ENGINES:
        raise TranscriptionError(f"STT_ENGINE desconhecido: {engine}")
    wav = _to_pcm16_wav(audio_bytes)
    return _ENGINES[engine](wav, language).strip()


def synthesize(text: str):
    """Texto -> bytes de MP3 (gTTS). Devolve None se falhar (sem internet, sem gTTS...)."""
    try:
        from gtts import gTTS

        buf = io.BytesIO()
        gTTS(text=text, lang="pt", tld="com.br").write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None
