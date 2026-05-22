"""
ÉIRE REMEMBERED - CLOUD MUSIC STREAMING SERVER
Streams music to all users via the internet, even when your PC is off.
Deploy this to a cloud service (Render, Railway, PythonAnywhere, etc.)
"""

from flask import Flask, Response, render_template_string, jsonify
import os
import sqlite3
import threading
import time
from pathlib import Path

# Try to import pygame for audio
try:
    import pygame
    from pygame import mixer
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

app = Flask(__name__)

# Configuration
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, 'data')
MUSIC_DIR = os.path.join(APP_DIR, 'music')
DATABASE_PATH = os.path.join(DATA_DIR, 'irelands_own.db')

# Global music state
current_music = {
    'enabled': False,
    'track_name': 'No track',
    'track_url': '',
    'volume': 50,
    'is_playing': False
}

# HTML Player Template
PLAYER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Éire Remembered - Live Music Stream</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Georgia, serif;
            background: linear-gradient(135deg, #1a5f1a 0%, #2d8f2d 100%);
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #ffd700;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }
        .subtitle {
            font-size: 1.2em;
            margin-bottom: 30px;
            font-style: italic;
            opacity: 0.9;
        }
        .music-icon {
            font-size: 5em;
            margin: 20px 0;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .track-info {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .track-name {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .status {
            font-size: 1.1em;
            opacity: 0.8;
        }
        .controls {
            margin-top: 30px;
        }
        button {
            background: #ffd700;
            color: #1a5f1a;
            border: none;
            padding: 15px 40px;
            font-size: 1.2em;
            border-radius: 50px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
            transition: all 0.3s;
        }
        button:hover {
            background: #ffed4e;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 215, 0, 0.6);
        }
        button:active {
            transform: translateY(0);
        }
        .volume-control {
            margin-top: 20px;
        }
        input[type="range"] {
            width: 100%;
            height: 8px;
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.3);
            outline: none;
            -webkit-appearance: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #ffd700;
            cursor: pointer;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
        }
        .footer {
            margin-top: 30px;
            opacity: 0.7;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ÉIRE REMEMBERED</h1>
        <div class="subtitle">Live Music Stream 🍀</div>
        
        <div class="music-icon">🎵</div>
        
        <div class="track-info">
            <div class="track-name" id="trackName">Loading...</div>
            <div class="status" id="status">Connecting to stream...</div>
        </div>
        
        <div class="controls">
            <button id="playBtn" onclick="togglePlayback()">▶️ Play Music</button>
        </div>
        
        <div class="volume-control">
            <label>🔊 Volume</label><br>
            <input type="range" id="volumeSlider" min="0" max="100" value="50" onchange="setVolume(this.value)">
            <div id="volumeValue">50%</div>
        </div>
        
        <div class="footer">
            Traditional Irish Music • Broadcasting 24/7
        </div>
    </div>
    
    <audio id="audioPlayer" preload="auto"></audio>
    
    <script>
        const audioPlayer = document.getElementById('audioPlayer');
        const playBtn = document.getElementById('playBtn');
        const trackName = document.getElementById('trackName');
        const status = document.getElementById('status');
        const volumeSlider = document.getElementById('volumeSlider');
        const volumeValue = document.getElementById('volumeValue');
        
        let isPlaying = false;
        
        // Fetch current music info
        async function updateMusicInfo() {
            try {
                const response = await fetch('/api/music-info');
                const data = await response.json();
                
                trackName.textContent = data.track_name;
                
                if (data.enabled && data.track_url) {
                    status.textContent = '🎶 Live Stream Active';
                    if (!isPlaying) {
                        playBtn.textContent = '▶️ Play Music';
                    }
                } else {
                    status.textContent = '⏸️ Stream Offline';
                    playBtn.textContent = '⏸️ Stream Offline';
                    playBtn.disabled = true;
                }
            } catch (error) {
                console.error('Error fetching music info:', error);
                status.textContent = '❌ Connection Error';
            }
        }
        
        function togglePlayback() {
            if (isPlaying) {
                audioPlayer.pause();
                playBtn.textContent = '▶️ Play Music';
                isPlaying = false;
            } else {
                audioPlayer.src = '/stream';
                audioPlayer.play()
                    .then(() => {
                        playBtn.textContent = '⏸️ Pause';
                        status.textContent = '🎶 Now Playing';
                        isPlaying = true;
                    })
                    .catch(err => {
                        console.error('Playback error:', err);
                        status.textContent = '❌ Playback Error';
                    });
            }
        }
        
        function setVolume(value) {
            audioPlayer.volume = value / 100;
            volumeValue.textContent = value + '%';
        }
        
        // Initialize
        setVolume(50);
        updateMusicInfo();
        
        // Update music info every 10 seconds
        setInterval(updateMusicInfo, 10000);
    </script>
</body>
</html>
"""


def get_music_settings():
    """Get music settings from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        settings = {}
        cursor.execute("SELECT key, value FROM site_settings WHERE key LIKE 'music_%'")
        rows = cursor.fetchall()
        
        for row in rows:
            settings[row['key']] = row['value']
        
        conn.close()
        
        return {
            'enabled': settings.get('music_enabled', 'false') == 'true',
            'track_name': settings.get('music_track_name', 'No track selected'),
            'track_url': settings.get('music_track_url', ''),
            'volume': int(settings.get('music_volume', '50')),
        }
    except Exception as e:
        print(f"Database error: {e}")
        return {
            'enabled': False,
            'track_name': 'No track',
            'track_url': '',
            'volume': 50
        }


def stream_audio_file(file_path):
    """Stream audio file in chunks"""
    try:
        with open(file_path, 'rb') as audio_file:
            while True:
                chunk = audio_file.read(4096)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        print(f"Streaming error: {e}")


@app.route('/')
def index():
    """Serve the music player page"""
    return render_template_string(PLAYER_HTML)


@app.route('/api/music-info')
def music_info():
    """Get current music information"""
    settings = get_music_settings()
    return jsonify(settings)


@app.route('/stream')
def stream():
    """Stream the current music file"""
    settings = get_music_settings()
    
    if not settings['enabled'] or not settings['track_url']:
        return "No music available", 404
    
    track_path = settings['track_url']
    
    if not os.path.exists(track_path):
        return "Music file not found", 404
    
    # Determine MIME type
    ext = os.path.splitext(track_path)[1].lower()
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg'
    }
    mime_type = mime_types.get(ext, 'audio/mpeg')
    
    return Response(
        stream_audio_file(track_path),
        mimetype=mime_type,
        headers={
            'Cache-Control': 'no-cache',
            'Content-Disposition': f'inline; filename="{os.path.basename(track_path)}"'
        }
    )


if __name__ == '__main__':
    print("=" * 80)
    print("ÉIRE REMEMBERED - CLOUD MUSIC STREAMING SERVER")
    print("=" * 80)
    print(f"Music Directory: {MUSIC_DIR}")
    print(f"Database: {DATABASE_PATH}")
    print("=" * 80)
    print()
    print("Server starting...")
    print("Users can access the music player at: http://localhost:5001")
    print()
    print("To deploy to cloud:")
    print("  - Render.com (free tier)")
    print("  - Railway.app (free tier)")
    print("  - PythonAnywhere.com (free tier)")
    print()
    print("=" * 80)
    
    # Run server
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
