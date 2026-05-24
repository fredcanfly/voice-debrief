from __future__ import annotations

import argparse
from pathlib import Path

from .config import get_settings
from .stt_local import LocalWhisperSTT


def main() -> None:
    parser = argparse.ArgumentParser(description='Benchmark local faster-whisper transcription')
    parser.add_argument('audio', help='Path to an audio file, e.g. .m4a/.mp3/.wav/.webm')
    args = parser.parse_args()
    result = LocalWhisperSTT(get_settings()).transcribe_file(Path(args.audio))
    print('--- transcript ---')
    print(result['text'])
    print('--- metadata ---')
    for key in ('elapsed_seconds', 'duration_seconds', 'model', 'device', 'compute_type', 'language', 'language_probability'):
        print(f"{key}: {result.get(key)}")


if __name__ == '__main__':
    main()
