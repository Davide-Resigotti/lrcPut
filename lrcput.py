#!/usr/bin/env python

# TO EXECUTE, RUN IN TERMINAL: python lrcput.py -d /path/to/directory -r -R

import os
import shutil
import argparse
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, USLT
from mutagen.easyid3 import EasyID3
from tqdm import tqdm

def has_embedded_lyrics(audio, file_extension):
    """Checks if the audio file already has embedded lyrics."""
    if file_extension == '.flac':
        return 'LYRICS' in audio
    elif file_extension == '.m4a':
        return '\xa9lyr' in audio.tags
    elif file_extension == '.mp3':
        return any(frame.FrameID == 'USLT' for frame in audio.tags.values())
    return False

def embed_lrc(directory, skip_existing, reduce_lrc, recursive):
    """Embeds LRC files into audio files and optionally deletes the LRC files."""
    audio_files = []
    
    # Collect all audio files in the directory (recursively if necessary)
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.flac', '.mp3', '.m4a')):
                audio_files.append(os.path.join(root, file))
    
    embedded_lyrics_files = 0
    failed_files = []
    
    # Progress bar to show the status
    with tqdm(total=len(audio_files), desc='Embedding LRC files', unit='file') as pbar:
        for audio_path in audio_files:
            file = os.path.basename(audio_path)
            lrc_file = os.path.splitext(file)[0] + '.lrc'
            lrc_path = os.path.join(os.path.dirname(audio_path), lrc_file)
            file_extension = os.path.splitext(audio_path)[1].lower()

            if os.path.exists(lrc_path):
                try:
                    audio = None
                    lyrics = open(lrc_path, 'r', encoding='utf-8').read()
                    
                    # If requested, skip files that already have embedded lyrics
                    if skip_existing:
                        if file_extension == '.flac':
                            audio = FLAC(audio_path)
                        elif file_extension == '.mp3':
                            audio = ID3(audio_path)
                        elif file_extension == '.m4a':
                            audio = MP4(audio_path)
                        
                        if has_embedded_lyrics(audio, file_extension):
                            pbar.set_postfix({"status": "skipped"})
                            pbar.update(1)
                            continue
                    
                    # Embed lyrics in the various formats
                    if file_extension == '.flac':
                        audio = FLAC(audio_path)
                        audio['LYRICS'] = lyrics
                        audio.save()
                    elif file_extension == '.mp3':
                        audio = ID3(audio_path)
                        audio['USLT'] = USLT(encoding=3, text=lyrics)
                        audio.save()
                    elif file_extension == '.m4a':
                        audio = MP4(audio_path)
                        audio.tags['\xa9lyr'] = lyrics
                        audio.save()
                    
                    embedded_lyrics_files += 1
                    pbar.set_postfix({"status": f"embedded: {file}"})
                    
                    # If requested, delete the LRC file after embedding
                    if reduce_lrc:
                        os.remove(lrc_path)
                        pbar.set_postfix({"status": f"embedded, LRC reduced: {file}"})
                
                except Exception as e:
                    print(f"Error embedding LRC for {file}: {str(e)}")
                    pbar.set_postfix({"status": f"error: {file}"})
                    failed_files.append(file)
                    if os.path.exists(lrc_path):
                        shutil.move(lrc_path, lrc_path + ".failed")
            
            pbar.update(1)
    
    return len(audio_files), embedded_lyrics_files, failed_files

if __name__ == "__main__":
    # Command-line argument parser
    parser = argparse.ArgumentParser(description='Embed LRC files into audio files (FLAC, MP3, and M4A) and optionally reduce LRC files.')
    parser.add_argument('-d', '--directory', required=True, help='Directory containing audio and LRC files')
    parser.add_argument('-s', '--skip', action='store_true', help='Skip files that already have embedded lyrics')  # Need to check if the tag exists
    parser.add_argument('-r', '--reduce', action='store_true', help='Reduce (delete) LRC files after embedding')
    parser.add_argument('-R', '--recursive', action='store_true', help='Recursively process subdirectories')
    args = parser.parse_args()

    # Run the script with the specified arguments
    directory_path = args.directory
    skip_existing = args.skip
    reduce_lrc = args.reduce
    recursive = args.recursive
    total, embedded, failed = embed_lrc(directory_path, skip_existing, reduce_lrc, recursive)
    
    # Final statistics
    percentage = (embedded / total) * 100 if total > 0 else 0
    print(f"Total audio files: {total}")
    print(f"Embedded lyrics in {embedded} audio files.")
    print(f"Percentage of audio files with embedded lyrics: {percentage:.2f}%")
    
    if failed:
        print("\nFailed to embed LRC for the following files:")
        for file in failed:
            print(file)