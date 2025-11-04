# rtsp_manager.py
import subprocess
import hashlib
import os
import shlex
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

        ffmpeg_cmd = (
            f"ffmpeg -rtsp_transport tcp -i {shlex.quote(rtsp_url)} \
            -c:v copy -c:a aac -f hls \
            -hls_time 2 -hls_list_size 6 -hls_flags delete_segments+append_list \
            -hls_allow_cache 0 \
            {shlex.quote(os.path.join(target_dir, 'index.m3u8'))}"
        )

        proc = subprocess.Popen(ffmpeg_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
