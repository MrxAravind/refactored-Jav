import os
import subprocess
import time
import sys
import logging
import random

def split_video(input_file, max_size_mb=1900):
    max_size_bytes = max_size_mb * 1024 * 1024
    temp_dir = 'temp_splits'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Probe the video duration
    probe_command = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', input_file
    ]
    result = subprocess.run(probe_command, stdout=subprocess.PIPE, text=True)
    duration = float(result.stdout.strip())
    
    # Estimate the video bitrate
    bitrate_command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=bit_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1', input_file
    ]
    bitrate_result = subprocess.run(bitrate_command, stdout=subprocess.PIPE, text=True)
    bitrate = int(bitrate_result.stdout.strip())  # Bitrate in bits per second
    
    # Calculate chunk duration based on bitrate
    if bitrate == 0:
        raise ValueError("Bitrate could not be determined.")
    
    # Convert max_size_bytes to bits
    max_size_bits = max_size_bytes * 8
    chunk_duration = max_size_bits / bitrate  # Duration in seconds
    
    # Split the video
    split_command = [
        'ffmpeg', '-i', input_file, '-c', 'copy', '-map', '0',
        '-f', 'segment', '-segment_time', str(chunk_duration),
        '-segment_format', 'mp4', '-reset_timestamps', '1',
        os.path.join(temp_dir, f'{os.path.basename(input_file).replace(".mp4","")}_%03d.mp4')
    ]
    subprocess.run(split_command, check=True)
    
    # Collect split file paths
    filepaths = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.mp4')]
    return filepaths


def gen_thumb(file_name, output_filename, retry_interval=10, max_retries=10):
    retries = 0
    while retries < max_retries:
        if os.path.exists(file_name):
            video_duration = get_video_duration(file_name)
            if video_duration is None:
                logging.error("Could not retrieve video duration.")
                return False
            
            random_time = random.uniform(0, video_duration)
            random_time_str = time.strftime('%H:%M:%S', time.gmtime(random_time))
            
            command = ['ffmpeg', '-ss', random_time_str, '-i', file_name, '-vframes', '1', output_filename]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
                logging.info(f"Thumbnail saved as {output_filename} at {random_time_str}")
                return True
            except subprocess.CalledProcessError as e:
                logging.error(f"Error: {e}")
                logging.error(f"Command output: {e.output.decode()}")
                return False
        else:
            logging.info(f"File {file_name} does not exist. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
            retries += 1

    logging.error(f"{max_retries} retries.")
    return False

def print_progress_bar(name, downloaded, total_size, length=40):
    percent = ("{0:.1f}").format(100 * (downloaded / float(total_size)))
    filled_length = int(length * downloaded // total_size)
    bar = '#' * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{name}\n[{bar}] {percent}%')
    sys.stdout.flush()

def format_bytes(byte_count):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    index = 0
    while byte_count >= 1024 and index < len(suffixes) - 1:
        byte_count /= 1024
        index += 1
    return f"{byte_count:.2f} {suffixes[index]}"

def get_video_duration(file_name):
    command = ['ffmpeg', '-i', file_name, '-hide_banner']
    result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
    duration_line = [x for x in result.stderr.split('\n') if 'Duration' in x]
    if duration_line:
        duration = duration_line[0].split()[1]
        h, m, s = duration.split(':')
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s[:-1])
        return total_seconds
    return None
