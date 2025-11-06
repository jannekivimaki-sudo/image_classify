# rtsp_manager.py
import subprocess
import hashlib
import os
from threading import Lock

"""
Pieni RTSP -> HLS manager, joka käynnistää FFmpeg-prosesseja
tuottamaan HLS-virtoja hakemistoon /data/static/hls/<stream_id>/index.m3u8

Huom: FFmpeg on asennettu Docker-kuvaan (Dockerfile:ssa).
"""

HLS_BASE = "/data/static/hls"
_processes = {}  # stream_id -> Popen
_lock = Lock()

def _stream_id_from_url(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]

def start_rtsp_to_hls(rtsp_url, force_restart=False):
    # Validate RTSP URL to prevent injection attacks
    if not rtsp_url or not isinstance(rtsp_url, str):
        raise ValueError("Invalid RTSP URL")
    if not rtsp_url.startswith(('rtsp://', 'rtsps://')):
        raise ValueError("URL must start with rtsp:// or rtsps://")
    
    # Parse and validate URL structure
    from urllib.parse import urlparse
    try:
        parsed = urlparse(rtsp_url)
        if not parsed.scheme in ('rtsp', 'rtsps'):
            raise ValueError("Invalid RTSP URL scheme")
        if not parsed.netloc:
            raise ValueError("Invalid RTSP URL: missing network location")
    except Exception as e:
        raise ValueError(f"Invalid RTSP URL: {e}")
    
    # Basic sanity check for dangerous characters in the URL
    if any(c in rtsp_url for c in [';', '`', '$', '(', ')']):
        raise ValueError("RTSP URL contains potentially dangerous characters")
    
    stream_id = _stream_id_from_url(rtsp_url)
    target_dir = os.path.join(HLS_BASE, stream_id)
    os.makedirs(target_dir, exist_ok=True)

    with _lock:
        if stream_id in _processes:
            proc = _processes[stream_id]
            if force_restart:
                try:
                    proc.kill()
                except Exception:
                    pass
                del _processes[stream_id]
            else:
                return {'stream_id': stream_id, 'playlist': f'/static/hls/{stream_id}/index.m3u8', 'status': 'running'}

        # Use list instead of shell=True to prevent shell injection
        # The URL is passed as a separate argument to ffmpeg, not through shell
        # CodeQL may flag this as a potential injection, but it's safe because:
        # 1. We validate the URL format and content above
        # 2. We use a list (not shell=True), so no shell interpretation occurs
        # 3. The URL is passed as a single argument to ffmpeg's -i parameter
        output_path = os.path.join(target_dir, 'index.m3u8')
        ffmpeg_cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', rtsp_url,  # Safe: validated URL passed as list element
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-f', 'hls',
            '-hls_time', '2',
            '-hls_list_size', '6',
            '-hls_flags', 'delete_segments+append_list',
            '-hls_allow_cache', '0',
            output_path
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _processes[stream_id] = proc

    return {'stream_id': stream_id, 'playlist': f'/static/hls/{stream_id}/index.m3u8', 'status': 'started'}

def stop_rtsp_stream_by_url(rtsp_url):
    stream_id = _stream_id_from_url(rtsp_url)
    return stop_rtsp_stream(stream_id)

def stop_rtsp_stream(stream_id):
    with _lock:
        if stream_id not in _processes:
            return {'stream_id': stream_id, 'status': 'not_found'}
        proc = _processes[stream_id]
        try:
            proc.kill()
        except Exception:
            pass
        del _processes[stream_id]
    return {'stream_id': stream_id, 'status': 'stopped'}

def get_status(stream_id):
    with _lock:
        proc = _processes.get(stream_id)
        if not proc:
            return {'stream_id': stream_id, 'status': 'not_found'}
        return {'stream_id': stream_id, 'status': 'running', 'pid': proc.pid}
