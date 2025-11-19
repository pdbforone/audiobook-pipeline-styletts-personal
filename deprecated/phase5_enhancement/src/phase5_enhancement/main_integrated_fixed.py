"""
Phase 5: Integrated Audio Enhancement with Phrase Cleanup

This version integrates automatic phrase removal before audio enhancement.
"""

import argparse
import logging
import os
import json
import time
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf
import noisereduce as nr
import pyloudnorm as pln
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import TIT2, TPE1
from pydantic import ValidationError
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import psutil
import tempfile
import shutil
import threading

# FIXED: Use relative imports for package modules
from .models import EnhancementConfig, AudioMetadata
from .phrase_cleaner import PhraseCleaner, PhraseCleanerConfig

# Setup logging
logger = logging.getLogger(__name__)
