"""
ÉIRE REMEMBERED - CLOUD MUSIC STREAMING SERVER
Streams music to all users via the internet, even when your PC is off.
Deploy this to a cloud service (Render, Railway, PythonAnywhere, etc.)
"""

from flask import Flask, Response, render_template_string, jsonify
import os
import random
import glob
from pathlib import Path

app = Flask(__name__)

# Configuration
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = APP_DIR  # Music files in root

# Global variable to store current random track
current_random_track = None

def get_random_music_file():
    """Get a random MP3 file from the music directory"""
    global current_random_track
    
    # Find all MP3 files in the root directory
    mp3_files = glob.glob(os.path.join(MUSIC_DIR, '*.mp3'))
    
    if not mp3_files:
        return None
    
    # Pick a random file if we don't have one, or return the current one
    if current_random_track is None or not os.path.exists(current_random_track):
        current_random_track = random.choice(mp3_files)
    
    return current_random_track

def get_track_name_from_path(file_path):
    """Extract a clean track name from file path"""
    if not file_path:
        return "No track available"
    
    # Get filename without extension and replace underscores with spaces
    filename = os.path.basename(file_path)
    name = os.path.splitext(filename)[0]
    return name.replace('_', ' ')

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
    track_file = get_random_music_file()
    
    if track_file:
        return jsonify({
            'enabled': True,
            'track_name': get_track_name_from_path(track_file),
            'track_url': os.path.basename(track_file),
            'volume': 85
        })
    else:
        return jsonify({
            'enabled': False,
            'track_name': 'No music files available',
            'track_url': '',
            'volume': 50
        })


@app.route('/stream')
def stream():
    """Stream a random music file"""
    track_file = get_random_music_file()
    
    if not track_file or not os.path.exists(track_file):
        return "No music available", 404
    
    # Determine MIME type
    ext = os.path.splitext(track_file)[1].lower()
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg'
    }
    mime_type = mime_types.get(ext, 'audio/mpeg')
    
    return Response(
        stream_audio_file(track_file),
        mimetype=mime_type,
        headers={
            'Cache-Control': 'no-cache',
            'Content-Disposition': f'inline; filename="{os.path.basename(track_file)}"'
        }
    )


@app.route('/next')
def next_track():
    """Switch to next random track"""
    global current_random_track
    current_random_track = None  # Reset to pick a new random track
    track_file = get_random_music_file()
    
    if track_file:
        return jsonify({
            'success': True,
            'track_name': get_track_name_from_path(track_file)
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No music files available'
        })


if __name__ == '__main__':
    print("=" * 80)
    print("ÉIRE REMEMBERED - CLOUD MUSIC STREAMING SERVER")
    print("=" * 80)
    print(f"Music Directory: {MUSIC_DIR}")
    print()
    
    # List available MP3 files
    mp3_files = glob.glob(os.path.join(MUSIC_DIR, '*.mp3'))
    if mp3_files:
        print(f"📀 Found {len(mp3_files)} music files:")
        for mp3 in mp3_files:
            print(f"   - {os.path.basename(mp3)}")
    else:
        print("⚠️  No MP3 files found!")
    
    print()
    print("=" * 80)
    print("🎵 Random song will play each time")
    print("🌐 Users can access at: http://localhost:5001")
    print("=" * 80)
    print()
    print("Deploying to: Render.com (free tier)")
    print()
    print("=" * 80)
    
    # Run server
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
