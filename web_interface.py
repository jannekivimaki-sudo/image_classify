from flask import Flask, render_template, request, jsonify, send_from_directory
import json
from datetime import datetime, timedelta
from pathlib import Path
import os
import logging

# Aseta logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Yritä tuoda RTSP-manageri (valinnainen)
_RTPS_AVAILABLE = False
try:
    from rtsp_manager import start_rtsp_to_hls, stop_rtsp_stream, stop_rtsp_stream_by_url, get_status
    _RTPS_AVAILABLE = True
    logger.info("RTSP manager ladattu")
except Exception as e:
    logger.info(f"RTSP manager ei saatavilla: {e}")

def create_templates():
    """Luo HTML-templatit"""
    template_dir = Path(__file__).parent / 'templates'
    template_dir.mkdir(exist_ok=True)
    
    # index.html (sisältää RTSP-hallinnan ja valinnan vertailua varten)
    index_html = '''
<!DOCTYPE html>
<html lang="fi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kuvien Luokittelu ja Selaus</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .warning-banner {
            background: #ff9800;
            color: white;
            padding: 15px;
            text-align: center;
            margin: 20px;
            border-radius: 5px;
            font-weight: bold;
        }
        .controls {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        .time-selection {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .time-group {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 2px solid #e9ecef;
        }
        .time-group h3 {
            margin-bottom: 15px;
            color: #2c3e50;
            text-align: center;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            margin-bottom: 15px;
        }
        label {
            font-weight: 600;
            margin-bottom: 5px;
            color: #495057;
        }
        input, select, button {
            padding: 12px 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }
        button {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(52, 152, 219, 0.4);
        }
        .classify-btn {
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
        }
        .compare-btn {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        }
        .timelapse-btn {
            background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .nav-link {
            display: inline-block;
            padding: 12px 25px;
            background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .nav-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(155, 89, 182, 0.4);
        }
        .images-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .image-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .image-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.2);
        }
        .image-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .image-info {
            padding: 15px;
        }
        .image-info h3 {
            margin-bottom: 8px;
            color: #2c3e50;
            font-size: 16px;
        }
        .image-meta {
            font-size: 14px;
            color: #7f8c8d;
        }
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #7f8c8d;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-top: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        .time-slider {
            width: 100%;
            margin: 10px 0;
        }
        .time-display {
            text-align: center;
            font-weight: bold;
            margin: 10px 0;
            color: #2c3e50;
        }
        .time-presets {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 10px;
        }
        .preset-btn {
            padding: 8px 12px;
            font-size: 14px;
        }
        .timelapse-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .timelapse-content {
            background: white;
            border-radius: 15px;
            padding: 30px;
            max-width: 95%;
            max-height: 95%;
            overflow: auto;
            width: 800px;
        }
        .timelapse-controls {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            align-items: end;
            margin: 20px 0;
        }
        .speed-control {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 5px;
            grid-column: 1 / -1;
            margin-top: 10px;
        }
        .speed-control button {
            padding: 8px 5px;
            font-size: 12px;
        }
        .timelapse-image {
            max-width: 100%;
            max-height: 60vh;
            object-fit: contain;
            border: 2px solid #e9ecef;
            border-radius: 8px;
        }
        .close-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            font-size: 20px;
            cursor: pointer;
        }
        .active {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) !important;
        }
        /* RTSP section */
        .rtsp-section {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 15px;
        }
        .rtsp-section input {
            flex: 1;
        }
        .hls-video {
            width: 100%;
            max-height: 480px;
            margin-top: 15px;
            display: none;
            border-radius: 8px;
            background: #000;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖼️ Kuvien Luokittelu ja Selaus</h1>
            <p>Selaa, vertaile ja katso timelapse-kuvia aikavälin mukaan</p>
        </div>

        {% if not classification_available %}
        <div class="warning-banner">
            ⚠️ Luokitteluominaisuudet eivät ole saatavilla. Tarkista että kaikki tiedostot on kopioitu oikein.
        </div>
        {% endif %}

        <div class="controls">
            <div class="time-selection">
                <div class="time-group">
                    <h3>📅 Aikaväli</h3>
                    <div class="form-group">
                        <label for="startDate">Alkupäivä:</label>
                        <input type="date" id="startDate" value="{{ start_date }}">
                    </div>
                    <div class="form-group">
                        <label for="endDate">Loppupäivä:</label>
                        <input type="date" id="endDate" value="{{ end_date }}">
                    </div>
                    <div class="time-presets">
                        <button class="preset-btn" onclick="setTimePreset('week')">Viime viikko</button>
                        <button class="preset-btn" onclick="setTimePreset('month')">Viime kuukausi</button>
                        <button class="preset-btn" onclick="setTimePreset('year')">Viime vuosi</button>
                    </div>
                </div>

                <div class="time-group">
                    <h3>⏰ Aikayksikkö</h3>
                    <div class="form-group">
                        <label for="timeUnit">Näytä kuvat:</label>
                        <select id="timeUnit">
                            <option value="all">Kaikki kuvat</option>
                            <option value="year">Vuosittain</option>
                            <option value="month">Kuukausittain</option>
                            <option value="week">Viikoittain</option>
                            <option value="day">Päivittäin</option>
                            <option value="hour">Tunneittain</option>
                            <option value="minute">Minuuteittain</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="timeValue">Valitse aika:</label>
                        <select id="timeValue" disabled>
                            <option value="">Valitse ensin aikayksikkö</option>
                        </select>
                    </div>
                </div>

                <div class="time-group">
                    <h3>🔍 Suodatus</h3>
                    <div class="form-group">
                        <label for="timeRange">Aikajana:</label>
                        <input type="range" id="timeRange" class="time-slider" min="0" max="100" value="50">
                        <div id="timeDisplay" class="time-display">Keskipiste</div>
                    </div>
                    <button onclick="applyTimeFilter()">Käytä aikasuodatin</button>
                    <button onclick="clearTimeFilter()" style="background: #95a5a6; margin-top: 10px;">Tyhjennä suodatin</button>
                </div>
            </div>

            <div class="button-group">
                <button class="classify-btn" onclick="classifyImages()" {% if not classification_available %}disabled{% endif %}>
                    🗂️ Luokittele Kuvat
                </button>
                <a href="/compare" class="nav-link">
                    ⚖️ Vertaile Kuvia
                </a>
                <button class="timelapse-btn" onclick="openTimelapseModal()" id="timelapseBtn" disabled>
                    🎬 Timelapse
                </button>
            </div>

            <div class="rtsp-section">
                <input type="text" id="rtspUrl" placeholder="rtsp://kamera:554/stream1">
                <button onclick="startRTSP()" id="startRtspBtn">Käynnistä stream</button>
                <button onclick="stopRTSP()" id="stopRtspBtn">Pysäytä stream</button>
            </div>

            <div id="stats" class="stats" style="display: none;"></div>
        </div>

        <div id="imagesContainer" class="images-grid">
            <div class="loading">
                Valitse aikaväli ja klikkaa "Hae Kuvat"
            </div>
        </div>

        <video id="hlsVideo" class="hls-video" controls></video>
    </div>

    <!-- Timelapse Modal -->
    <div id="timelapseModal" class="timelapse-modal">
        <div class="timelapse-content">
            <button class="close-btn" onclick="closeTimelapseModal()">×</button>
            <h2>🎬 Timelapse-katselu</h2>
            
            <div class="timelapse-controls">
                <div class="form-group">
                    <label for="timelapseStartDate">Alkupäivä:</label>
                    <input type="date" id="timelapseStartDate" value="{{ start_date }}">
                </div>
                <div class="form-group">
                    <label for="timelapseEndDate">Loppupäivä:</label>
                    <input type="date" id="timelapseEndDate" value="{{ end_date }}">
                </div>
                
                <div class="form-group">
                    <label for="timelapseCategory">Aikayksikkö:</label>
                    <select id="timelapseCategory">
                        <option value="all">Kaikki kuvat</option>
                        <option value="year">Vuosi</option>
                        <option value="month">Kuukausi</option>
                        <option value="week">Viikko</option>
                        <option value="day">Päivä</option>
                        <option value="hour">Tunti</option>
                        <option value="minute">Minuutti</option>
                    </select>
                </div>
                
                <div class="speed-control">
                    <label>Nopeus:</label>
                    <button onclick="changeSpeed(0.125)">0.125x</button>
                    <button onclick="changeSpeed(0.25)">0.25x</button>
                    <button onclick="changeSpeed(0.5)">0.5x</button>
                    <button onclick="changeSpeed(1)" class="active">1x</button>
                    <button onclick="changeSpeed(2)">2x</button>
                    <button onclick="changeSpeed(4)">4x</button>
                    <button onclick="changeSpeed(8)">8x</button>
                    <button onclick="changeSpeed(16)">16x</button>
                </div>
                
                <button onclick="loadTimelapseImages()" id="loadTimelapseBtn">Lataa Kuvat</button>
                <button onclick="startTimelapse()" id="startTimelapse" disabled>Käynnistä</button>
                <button onclick="stopTimelapse()" id="stopTimelapse" style="display:none;">Pysäytä</button>
            </div>
            
            <div id="timelapseInfo" style="text-align: center; margin: 20px 0;">
                <div id="timelapseStats">Valitse aikaväli ja lataa kuvat</div>
            </div>
            
            <div id="timelapseContainer">
                <img id="timelapseImage" class="timelapse-image" src="" style="display:none;">
                <div id="timelapseProgress" style="text-align: center; margin: 20px 0;"></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        let currentImages = [];
        let timelapseInterval = null;
        let currentSpeed = 1;
        let currentTimelapseIndex = 0;
        let availableTimeValues = {};
        let timelapseImages = [];

        // Aikapresetit
        function setTimePreset(preset) {
            const endDate = new Date();
            let startDate = new Date();
            
            switch(preset) {
                case 'week':
                    startDate.setDate(endDate.getDate() - 7);
                    break;
                case 'month':
                    startDate.setMonth(endDate.getMonth() - 1);
                    break;
                case 'year':
                    startDate.setFullYear(endDate.getFullYear() - 1);
                    break;
            }
            
            document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
            document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
            loadImages();
        }

        // Lataa saatavilla olevat aikayksiköt
        async function loadTimeUnits() {
            const timeUnit = document.getElementById('timeUnit').value;
            if (timeUnit === 'all') {
                document.getElementById('timeValue').disabled = true;
                document.getElementById('timeValue').innerHTML = '<option value="">Ei saatavilla</option>';
                return;
            }

            try {
                const response = await fetch('/api/time_units?unit=' + timeUnit);
                const units = await response.json();
                
                availableTimeValues[timeUnit] = units;
                const select = document.getElementById('timeValue');
                select.innerHTML = '<option value="">Valitse ' + timeUnit + '</option>';
                select.disabled = false;
                
                units.forEach(unit => {
                    const option = document.createElement('option');
                    option.value = unit.value;
                    option.textContent = unit.label;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading time units:', error);
            }
        }

        // Hae kuvat aikavälin mukaan
        async function loadImages() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const timeUnit = document.getElementById('timeUnit').value;
            const timeValue = document.getElementById('timeValue').value;

            const container = document.getElementById('imagesContainer');
            container.innerHTML = '<div class="loading">Haetaan kuvia...</div>';

            try {
                let url = `/api/images?start_date=${startDate}&end_date=${endDate}`;
                
                if (timeUnit !== 'all' && timeValue) {
                    url += `&time_unit=${timeUnit}&time_value=${timeValue}`;
                }

                const response = await fetch(url);
                const images = await response.json();
                currentImages = images;

                if (images.length === 0) {
                    container.innerHTML = '<div class="loading">Ei kuvia löytynyt valitulla aikavälillä</div>';
                    document.getElementById('timelapseBtn').disabled = true;
                    return;
                }

                document.getElementById('timelapseBtn').disabled = false;

                // Päivitä aikajanan maksimiarvo
                document.getElementById('timeRange').max = images.length - 1;
                updateTimeDisplay();

                container.innerHTML = images.map((image, index) => `
                    <div class="image-card" onclick="selectImage('${image.path}')" data-index="${index}">
                        <img src="/images/${image.path}" alt="${image.filename}" onerror="this.style.display='none'">
                        <div class="image-info">
                            <h3>${image.filename}</h3>
                            <div class="image-meta">
                                <div>${image.date_display}</div>
                                <div>${image.category}</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                container.innerHTML = '<div class="loading">Virhe kuvien haussa</div>';
                console.error('Error:', error);
            }
        }

        // Päivitä aikajanan näyttö
        function updateTimeDisplay() {
            const slider = document.getElementById('timeRange');
            const display = document.getElementById('timeDisplay');
            const index = parseInt(slider.value);
            
            if (currentImages[index]) {
                const image = currentImages[index];
                display.textContent = `Kuva ${index + 1}/${currentImages.length}: ${image.date_display}`;
            }
        }

        // Käytä aikasuodatinta
        function applyTimeFilter() {
            const slider = document.getElementById('timeRange');
            const index = parseInt(slider.value);
            
            if (currentImages[index]) {
                // Korosta valittu kuva
                document.querySelectorAll('.image-card').forEach(card => {
                    card.style.opacity = '0.6';
                });
                
                const selectedCard = document.querySelector(`.image-card[data-index="${index}"]`);
                if (selectedCard) {
                    selectedCard.style.opacity = '1';
                    selectedCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        }

        // Tyhjennä aikasuodatin
        function clearTimeFilter() {
            document.querySelectorAll('.image-card').forEach(card => {
                card.style.opacity = '1';
            });
            document.getElementById('timeRange').value = Math.floor(currentImages.length / 2);
            updateTimeDisplay();
        }

        // Luokittelu
        async function classifyImages() {
            try {
                const response = await fetch('/api/classify', { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    showStats(result.result);
                    alert('Kuvien luokittelu valmis!');
                    loadImages();
                } else {
                    alert('Luokittelu epäonnistui: ' + result.error);
                }
            } catch (error) {
                alert('Virhe luokittelussa: ' + error.message);
            }
        }

        function showStats(result) {
            const statsDiv = document.getElementById('stats');
            const stats = result.stats;
            const classified = result.classified;

            statsDiv.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${stats.total}</div>
                    <div>Yhteensä kuvia</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.filesystem}</div>
                    <div>Tiedostojärjestelmä</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${classified.year.images}</div>
                    <div>Vuosikuvia</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${classified.minute.images}</div>
                    <div>Minuuttikuvia</div>
                </div>
            `;
            statsDiv.style.display = 'grid';
        }

        function selectImage(imagePath) {
            sessionStorage.setItem('selectedImage', imagePath);
            alert('Kuva valittu vertailua varten! Mene "Vertaile Kuvia" -sivulle.');
        }

        // RTSP / HLS -toiminnot
        let current_stream = null;
        async function startRTSP() {
            const url = document.getElementById('rtspUrl').value;
            if (!url) { alert('Anna RTSP-URL'); return; }
            try {
                const res = await fetch('/api/rtsp/start', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({url})
                });
                const body = await res.json();
                if (body.playlist) {
                    current_stream = body;
                    playHls(body.playlist);
                } else {
                    alert('Streamin käynnistys epäonnistui: ' + (body.error || 'Tuntematon virhe'));
                }
            } catch (err) {
                alert('RTSP start virhe: ' + err.message);
            }
        }

        async function stopRTSP() {
            if (!current_stream) {
                alert('Ei käynnissä olevaa streamia');
                return;
            }
            try {
                const res = await fetch('/api/rtsp/stop', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({stream_id: current_stream.stream_id})
                });
                const body = await res.json();
                if (body.status === 'stopped' || body.status === 'not_found') {
                    alert('Stream pysäytetty');
                    const v = document.getElementById('hlsVideo');
                    if (v) { v.pause(); v.style.display='none'; v.src=''; }
                    current_stream = null;
                } else {
                    alert('Pysäytys epäonnistui');
                }
            } catch (err) {
                alert('RTSP stop virhe: ' + err.message);
            }
        }

        function playHls(playlist) {
            const video = document.getElementById('hlsVideo');
            const videoSrc = playlist;
            if (Hls.isSupported()) {
                const hls = new Hls();
                hls.loadSource(videoSrc);
                hls.attachMedia(video);
                video.style.display = 'block';
                video.play().catch(()=>{});
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = videoSrc;
                video.style.display = 'block';
                video.play().catch(()=>{});
            } else {
                alert('Selaimesi ei tue HLS-soitinta suoraan');
            }
        }

        // Timelapse-toiminnot
        function openTimelapseModal() {
            document.getElementById('timelapseModal').style.display = 'flex';
            // Aseta oletusarvot
            const today = new Date();
            const lastWeek = new Date();
            lastWeek.setDate(today.getDate() - 7);
            
            document.getElementById('timelapseStartDate').value = lastWeek.toISOString().split('T')[0];
            document.getElementById('timelapseEndDate').value = today.toISOString().split('T')[0];
        }

        function closeTimelapseModal() {
            document.getElementById('timelapseModal').style.display = 'none';
            stopTimelapse();
        }

        // Lataa timelapse-kuvat
        async function loadTimelapseImages() {
            const startDate = document.getElementById('timelapseStartDate').value;
            const endDate = document.getElementById('timelapseEndDate').value;
            const category = document.getElementById('timelapseCategory').value;

            if (!startDate || !endDate) {
                alert('Valitse aikaväli!');
                return;
            }

            try {
                document.getElementById('timelapseStats').innerHTML = 'Ladataan kuvia...';
                
                let url = `/api/images?start_date=${startDate}&end_date=${endDate}`;
                
                if (category !== 'all') {
                    const unitsResponse = await fetch(`/api/time_units?unit=${category}`);
                    const units = await unitsResponse.json();
                    
                    if (units.length > 0) {
                        const firstUnit = units[0].value;
                        url += `&time_unit=${category}&time_value=${firstUnit}`;
                    }
                }

                const response = await fetch(url);
                const images = await response.json();
                
                timelapseImages = images.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                
                if (timelapseImages.length === 0) {
                    document.getElementById('timelapseStats').innerHTML = 
                        `Ei kuvia aikavälillä ${startDate} - ${endDate}`;
                    document.getElementById('startTimelapse').disabled = true;
                    return;
                }

                document.getElementById('timelapseStats').innerHTML = 
                    `Ladattu ${timelapseImages.length} kuvaa aikaväliltä ${startDate} - ${endDate}`;
                document.getElementById('startTimelapse').disabled = false;
                
                if (timelapseImages.length > 0) {
                    const firstImage = timelapseImages[0];
                    document.getElementById('timelapseImage').src = `/images/${firstImage.path}`;
                    document.getElementById('timelapseImage').style.display = 'block';
                    document.getElementById('timelapseProgress').innerHTML = 
                        `Kuva 1/${timelapseImages.length}: ${firstImage.date_display}`;
                }
                
            } catch (error) {
                console.error('Error loading timelapse images:', error);
                document.getElementById('timelapseStats').innerHTML = 'Virhe kuvien latauksessa';
            }
        }

        function changeSpeed(speed) {
            currentSpeed = speed;
            document.querySelectorAll('.speed-control button').forEach(btn => {
                btn.classList.remove('active');
            });
            // event may be undefined in some calls; guard
            try { event.target.classList.add('active'); } catch (e) {}
            
            if (timelapseInterval) {
                stopTimelapse();
                startTimelapse();
            }
        }

        function startTimelapse() {
            if (timelapseImages.length === 0) {
                alert('Lataa kuvat ensin!');
                return;
            }
            
            document.getElementById('startTimelapse').style.display = 'none';
            document.getElementById('stopTimelapse').style.display = 'inline-block';
            document.getElementById('loadTimelapseBtn').disabled = true;
            
            currentTimelapseIndex = 0;
            const intervalTime = 1000 / currentSpeed;
            
            timelapseInterval = setInterval(() => {
                if (currentTimelapseIndex >= timelapseImages.length) {
                    currentTimelapseIndex = 0; // Aloita alusta
                }
                
                const image = timelapseImages[currentTimelapseIndex];
                const timelapseImage = document.getElementById('timelapseImage');
                const timelapseProgress = document.getElementById('timelapseProgress');
                
                timelapseImage.src = `/images/${image.path}`;
                timelapseImage.style.display = 'block';
                timelapseProgress.innerHTML = `
                    <strong>${image.filename}</strong><br>
                    ${image.date_display}<br>
                    ${image.category}<br>
                    Kuva ${currentTimelapseIndex + 1} / ${timelapseImages.length}<br>
                    Nopeus: ${currentSpeed}x
                `;
                
                currentTimelapseIndex++;
            }, intervalTime);
        }

        function stopTimelapse() {
            if (timelapseInterval) {
                clearInterval(timelapseInterval);
                timelapseInterval = null;
            }
            document.getElementById('startTimelapse').style.display = 'inline-block';
            document.getElementById('stopTimelapse').style.display = 'none';
            document.getElementById('loadTimelapseBtn').disabled = false;
        }

        // Alustus
        document.addEventListener('DOMContentLoaded', function() {
            loadImages();
            
            // Kuuntele aikayksikön muutoksia
            document.getElementById('timeUnit').addEventListener('change', loadTimeUnits);
            document.getElementById('timeValue').addEventListener('change', loadImages);
            
            // Kuuntele aikajanan muutoksia
            document.getElementById('timeRange').addEventListener('input', updateTimeDisplay);
        });
    </script>
</body>
</html>
    '''

    # compare.html (sisältää loadSelectedFromSession ja korjatun liukusäätimen)
    compare_html = '''
<!DOCTYPE html>
<html lang="fi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kuvavertailu</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); min-height:100vh; padding:20px; }
        .container { max-width:1600px; margin:0 auto; background:white; border-radius:15px; box-shadow:0 20px 40px rgba(0,0,0,0.1); overflow:hidden; }
        .header { background: linear-gradient(135deg,#2c3e50 0%,#3498db 100%); color:white; padding:30px; text-align:center; }
        .header h1 { font-size:2.5em; margin-bottom:10px; }
        .comparison-section { padding:30px; }
        .time-selection { display:grid; grid-template-columns:1fr 1fr; gap:30px; margin-bottom:30px; }
        .time-group { background:#f8f9fa; padding:20px; border-radius:10px; border:2px solid #e9ecef; }
        .form-group { display:flex; flex-direction:column; margin-bottom:15px; }
        label { font-weight:600; margin-bottom:5px; color:#495057; }
        input, select, button { padding:12px 15px; border:2px solid #e9ecef; border-radius:8px; font-size:16px; transition:all 0.3s ease; }
        button { background: linear-gradient(135deg,#3498db 0%,#2980b9 100%); color:white; border:none; cursor:pointer; font-weight:600; }
        .image-selectors { display:grid; grid-template-columns:1fr 1fr; gap:30px; margin-bottom:30px; }
        .selector { background:#f8f9fa; padding:20px; border-radius:10px; }
        .image-preview { width:100%; height:300px; background:#e9ecef; border-radius:8px; margin-bottom:15px; overflow:hidden; display:flex; align-items:center; justify-content:center; }
        .image-preview img { max-width:100%; max-height:100%; object-fit:contain; }
        .image-scroller { display:flex; align-items:center; gap:10px; margin:10px 0; }
        .scroll-btn { padding:10px; background:#6c757d; color:white; border:none; border-radius:5px; cursor:pointer; }
        .image-counter { text-align:center; font-weight:bold; color:#495057; }
        .image-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(120px,1fr)); gap:10px; margin-top:15px; max-height:200px; overflow-y:auto; }
        .grid-image { width:100%; height:80px; object-fit:cover; border-radius:6px; cursor:pointer; transition:all 0.3s ease; }
        .grid-image:hover { transform:scale(1.05); box-shadow:0 5px 15px rgba(0,0,0,0.3); }
        .selected { border:3px solid #3498db; box-shadow:0 0 0 3px rgba(52,152,219,0.3); }
        .comparison-container { position:relative; width:100%; height:600px; background:#000; border-radius:12px; overflow:hidden; margin-bottom:20px; }
        .comparison-image { position:absolute; top:0; left:0; width:100%; height:100%; object-fit:contain; }
        .image-before { z-index:1; }
        .image-after { z-index:2; clip-path: polygon(0 0, 50% 0, 50% 100%, 0 100%); }
        .slider-container { position:absolute; top:0; left:0; width:100%; height:100%; z-index:3; }
        .slider { position:absolute; top:0; left:50%; transform:translateX(-50%); width:4px; height:100%; background:#3498db; cursor:ew-resize; }
        .slider-handle { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:50px; height:50px; background:#3498db; border-radius:50%; border:4px solid white; box-shadow:0 2px 10px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; color:white; font-size:18px; }
        .controls { display:flex; gap:15px; justify-content:center; margin-top:20px; }
        .back-btn { background: linear-gradient(135deg,#95a5a6 0%,#7f8c8d 100%); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚖️ Kuvavertailu</h1>
            <p>Vertaa kahta kuvaa eri ajoista liukusäätimellä</p>
        </div>

        <div class="comparison-section">
            <!-- Aikavalinta -->
            <div class="time-selection">
                <div class="time-group">
                    <h3>📅 Vanhemman kuvan aika</h3>
                    <div class="form-group">
                        <label for="beforeDate">Päivämäärä:</label>
                        <input type="date" id="beforeDate">
                    </div>
                    <button onclick="loadBeforeImages()">Hae vanhemmat kuvat</button>
                    <button onclick="loadSelectedFromSession()">Valittu istunnosta</button>
                </div>

                <div class="time-group">
                    <h3>📅 Uudemman kuvan aika</h3>
                    <div class="form-group">
                        <label for="afterDate">Päivämäärä:</label>
                        <input type="date" id="afterDate">
                    </div>
                    <button onclick="loadAfterImages()">Hae uudemmat kuvat</button>
                </div>
            </div>

            <!-- Kuvien valinta -->
            <div class="image-selectors">
                <div class="selector">
                    <h3>Vanha Kuva (Vasen)</h3>
                    <div class="image-preview" id="beforePreview">
                        <div style="color: #7f8c8d;">Valitse kuva</div>
                    </div>
                    <div class="image-scroller">
                        <button class="scroll-btn" onclick="scrollBeforeImage(-1)">◀</button>
                        <div class="image-counter" id="beforeCounter">0/0</div>
                        <button class="scroll-btn" onclick="scrollBeforeImage(1)">▶</button>
                    </div>
                    <div class="image-grid" id="beforeGrid"></div>
                </div>

                <div class="selector">
                    <h3>Uusi Kuva (Oikea)</h3>
                    <div class="image-preview" id="afterPreview">
                        <div style="color: #7f8c8d;">Valitse kuva</div>
                    </div>
                    <div class="image-scroller">
                        <button class="scroll-btn" onclick="scrollAfterImage(-1)">◀</button>
                        <div class="image-counter" id="afterCounter">0/0</div>
                        <button class="scroll-btn" onclick="scrollAfterImage(1)">▶</button>
                    </div>
                    <div class="image-grid" id="afterGrid"></div>
                </div>
            </div>

            <!-- Vertailu -->
            <div class="comparison-container" id="comparisonContainer" style="display: none;">
                <img id="beforeImage" class="comparison-image image-before" src="" alt="Vanha kuva">
                <img id="afterImage" class="comparison-image image-after" src="" alt="Uusi kuva">
                <div class="slider-container">
                    <div class="slider">
                        <div class="slider-handle">⇄</div>
                    </div>
                </div>
            </div>

            <div class="controls">
                <button class="back-btn" onclick="window.location.href='/'">← Takaisin</button>
                <button onclick="startComparison()" id="compareBtn" disabled>Aloita Vertailu</button>
                <button onclick="resetComparison()">Nollaa Valinnat</button>
            </div>
        </div>
    </div>

    <script>
        let beforeImages = [];
        let afterImages = [];
        let currentBeforeIndex = 0;
        let currentAfterIndex = 0;
        let selectedImages = {
            before: null,
            after: null
        };

        // Aseta oletuspäivämäärät
        function setDefaultDates() {
            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(today.getDate() - 1);
            
            document.getElementById('beforeDate').value = yesterday.toISOString().split('T')[0];
            document.getElementById('afterDate').value = today.toISOString().split('T')[0];
        }

        // Hae vanhemmat kuvat
        async function loadBeforeImages() {
            const date = document.getElementById('beforeDate').value;
            if (!date) {
                alert('Valitse päivämäärä ensin');
                return;
            }

            try {
                const response = await fetch(`/api/unique_images?start_date=${date}&end_date=${date}`);
                const images = await response.json();
                
                beforeImages = images.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                
                if (beforeImages.length === 0) {
                    alert(`Ei kuvia valitulle päivämäärälle ${date}!`);
                } else {
                    alert(`Löytyi ${beforeImages.length} uniikkia kuvaa päivältä ${date}`);
                }
                
                updateBeforeDisplay();
                populateImageGrid('beforeGrid', beforeImages, 'before');
            } catch (error) {
                console.error('Error loading before images:', error);
                alert('Virhe kuvien haussa');
            }
        }

        // Hae uudemmat kuvat
        async function loadAfterImages() {
            const date = document.getElementById('afterDate').value;
            if (!date) {
                alert('Valitse päivämäärä ensin');
                return;
            }

            try {
                const response = await fetch(`/api/unique_images?start_date=${date}&end_date=${date}`);
                const images = await response.json();
                
                afterImages = images.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                
                if (afterImages.length === 0) {
                    alert(`Ei kuvia valitulle päivämäärälle ${date}!`);
                } else {
                    alert(`Löytyi ${afterImages.length} uniikkia kuvaa päivältä ${date}`);
                }
                
                updateAfterDisplay();
                populateImageGrid('afterGrid', afterImages, 'after');
            } catch (error) {
                console.error('Error loading after images:', error);
                alert('Virhe kuvien haussa');
            }
        }

        // Päivitä näyttö
        function updateBeforeDisplay() {
            const counter = document.getElementById('beforeCounter');
            const preview = document.getElementById('beforePreview');
            
            counter.textContent = `${currentBeforeIndex + 1}/${beforeImages.length}`;
            
            if (beforeImages.length > 0) {
                const image = beforeImages[currentBeforeIndex];
                preview.innerHTML = `<img src="/images/${image.path}" alt="${image.filename}">`;
                selectedImages.before = image;
            } else {
                preview.innerHTML = '<div style="color: #7f8c8d;">Ei kuvia</div>';
                selectedImages.before = null;
            }
            
            updateCompareButton();
        }

        function updateAfterDisplay() {
            const counter = document.getElementById('afterCounter');
            const preview = document.getElementById('afterPreview');
            
            counter.textContent = `${currentAfterIndex + 1}/${afterImages.length}`;
            
            if (afterImages.length > 0) {
                const image = afterImages[currentAfterIndex];
                preview.innerHTML = `<img src="/images/${image.path}" alt="${image.filename}">`;
                selectedImages.after = image;
            } else {
                preview.innerHTML = '<div style="color: #7f8c8d;">Ei kuvia</div>';
                selectedImages.after = null;
            }
            
            updateCompareButton();
        }

        // Scrollaa kuvia
        function scrollBeforeImage(direction) {
            if (beforeImages.length === 0) return;
            
            currentBeforeIndex = (currentBeforeIndex + direction + beforeImages.length) % beforeImages.length;
            updateBeforeDisplay();
        }

        function scrollAfterImage(direction) {
            if (afterImages.length === 0) return;
            
            currentAfterIndex = (currentAfterIndex + direction + afterImages.length) % afterImages.length;
            updateAfterDisplay();
        }

        // Populoi kuvagrid
        function populateImageGrid(gridId, images, type) {
            const grid = document.getElementById(gridId);
            grid.innerHTML = '';

            images.forEach((image, index) => {
                const img = document.createElement('img');
                img.src = `/images/${image.path}`;
                img.className = 'grid-image';
                img.title = `${image.filename}\\n${image.date_display}`;
                img.onerror = function() { this.style.display = 'none'; };
                
                img.addEventListener('click', () => {
                    if (type === 'before') {
                        currentBeforeIndex = index;
                        updateBeforeDisplay();
                    } else {
                        currentAfterIndex = index;
                        updateAfterDisplay();
                    }
                });
                
                grid.appendChild(img);
            });
        }

        function updateCompareButton() {
            const btn = document.getElementById('compareBtn');
            btn.disabled = !(selectedImages.before && selectedImages.after);
        }

        function startComparison() {
            if (!selectedImages.before || !selectedImages.after) return;

            document.getElementById('beforeImage').src = `/images/${selectedImages.before.path}`;
            document.getElementById('afterImage').src = `/images/${selectedImages.after.path}`;
            document.getElementById('comparisonContainer').style.display = 'block';

            initSlider();
        }

        function resetComparison() {
            beforeImages = [];
            afterImages = [];
            currentBeforeIndex = 0;
            currentAfterIndex = 0;
            selectedImages.before = null;
            selectedImages.after = null;
            
            document.getElementById('beforePreview').innerHTML = '<div style="color: #7f8c8d;">Valitse kuva</div>';
            document.getElementById('afterPreview').innerHTML = '<div style="color: #7f8c8d;">Valitse kuva</div>';
            document.getElementById('beforeCounter').textContent = '0/0';
            document.getElementById('afterCounter').textContent = '0/0';
            document.getElementById('beforeGrid').innerHTML = '';
            document.getElementById('afterGrid').innerHTML = '';
            document.getElementById('comparisonContainer').style.display = 'none';
            
            updateCompareButton();
        }

        function initSlider() {
            const sliderContainer = document.querySelector('.slider-container');
            const sliderBar = document.querySelector('.slider');
            const handle = document.querySelector('.slider-handle');
            const afterImage = document.querySelector('.image-after');
            let isDragging = false;

            function updateSliderPosition(clientX) {
                const container = document.querySelector('.comparison-container');
                const rect = container.getBoundingClientRect();
                let percentage = ((clientX - rect.left) / rect.width) * 100;
                percentage = Math.max(0, Math.min(100, percentage));
                afterImage.style.clipPath = `polygon(0 0, ${percentage}% 0, ${percentage}% 100%, 0 100%)`;
                sliderBar.style.left = `${percentage}%`;
                handle.style.left = `${percentage}%`;
            }

            sliderContainer.addEventListener('pointerdown', function(e) {
                isDragging = true;
                sliderContainer.setPointerCapture(e.pointerId);
                updateSliderPosition(e.clientX);
            });

            sliderContainer.addEventListener('pointermove', function(e) {
                if (!isDragging) return;
                updateSliderPosition(e.clientX);
            });

            sliderContainer.addEventListener('pointerup', function(e) {
                isDragging = false;
                try { sliderContainer.releasePointerCapture(e.pointerId); } catch (err) {}
            });

            // Touch-friendly: pointer events cover mouse and touch in modern browsers
        }

        // Lataa istunnosta valittu kuva ja asettaa sen ennen-kuvaksi
        function loadSelectedFromSession() {
            const sel = sessionStorage.getItem('selectedImage');
            if (!sel) { alert('Ei valittua kuvaa istunnossa'); return; }
            fetch('/api/image_by_path?path=' + encodeURIComponent(sel)).then(r=>r.json()).then(img=>{
                if (img && img.path) {
                    beforeImages = [img];
                    populateImageGrid('beforeGrid', beforeImages, 'before');
                    currentBeforeIndex = 0;
                    updateBeforeDisplay();
                    alert('Istunnosta ladattu kuva vanhemmaksi kuvaksi. Valitse toinen kuva vertailuun.');
                } else {
                    alert('Kuvaa ei löydy palvelimelta');
                }
            }).catch(err => { console.error(err); alert('Virhe haettaessa kuvaa'); });
        }

        // Alustus
        document.addEventListener('DOMContentLoaded', function() {
            setDefaultDates();
        });
    </script>
</body>
</html>
    '''
    
    # Tallenna templatit
    (template_dir / 'index.html').write_text(index_html, encoding='utf-8')
    (template_dir / 'compare.html').write_text(compare_html, encoding='utf-8')
    logger.info("Templatit luotu onnistuneesti")

# Yritä tuoda luokittelumoduuli
CLASSIFICATION_AVAILABLE = False
DB = None

try:
    from classify_images import classify_images_hierarchical
    from app import ImageDatabase
    
    # Alusta tietokanta
    BASE_PATH = Path('/data/classified')
    DB = ImageDatabase(BASE_PATH)
    CLASSIFICATION_AVAILABLE = True
    logger.info("Luokittelumoduulit ladattu onnistuneesti")
except ImportError as e:
    logger.warning(f"Luokittelumoduuleja ei voitu ladata: {e}")
except Exception as e:
    logger.error(f"Tietokannan alustus epäonnistui: {e}")

# API-reitit

@app.route('/api/time_units')
def get_time_units():
    """Hae saatavilla olevat aikayksiköt"""
    if not CLASSIFICATION_AVAILABLE:
        return jsonify([])
    
    try:
        unit = request.args.get('unit', '')
        images = DB.get_images_by_date_range('', '')
        
        if unit == 'year':
            years = set()
            for img in images:
                if 'year_' in img['category']:
                    year_value = img['category'].split('year_')[1]
                    years.add(year_value)
            units = sorted(years)
            return jsonify([{'value': u, 'label': f'Vuosi {u}'} for u in units])
            
        elif unit == 'month':
            months = set()
            for img in images:
                if 'month_' in img['category']:
                    month_value = img['category'].split('month_')[1]
                    months.add(month_value)
            units = sorted(months)
            return jsonify([{'value': u, 'label': f'Kuukausi {u}'} for u in units])
            
        elif unit == 'week':
            weeks = set()
            for img in images:
                if 'week_' in img['category']:
                    week_value = img['category'].split('week_')[1]
                    weeks.add(week_value)
            units = sorted(weeks)
            return jsonify([{'value': u, 'label': f'Viikko {u}'} for u in units])
            
        elif unit == 'day':
            days = set()
            for img in images:
                if 'day_' in img['category']:
                    day_value = img['category'].split('day_')[1]
                    days.add(day_value)
            units = sorted(days)
            return jsonify([{'value': u, 'label': f'Päivä {u}'} for u in units])
            
        elif unit == 'hour':
            hours = set()
            for img in images:
                if 'hour_' in img['category']:
                    hour_value = img['category'].split('hour_')[1]
                    hours.add(hour_value)
            units = sorted(hours)
            return jsonify([{'value': u, 'label': f'Tunti {u}'} for u in units])
            
        elif unit == 'minute':
            minutes = set()
            for img in images:
                if 'minute_' in img['category']:
                    minute_value = img['category'].split('minute_')[1]
                    minutes.add(minute_value)
            units = sorted(minutes)
            return jsonify([{'value': u, 'label': f'Minuutti {u}'} for u in units])
            
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"Virhe aikayksiköiden haussa: {e}")
        return jsonify([])

@app.route('/api/images_by_category')
def get_images_by_category():
    """Hae kuvat kategorian perusteella"""
    try:
        if not CLASSIFICATION_AVAILABLE:
            return jsonify([])
            
        category_type = request.args.get('type', '')
        category_value = request.args.get('value', '')
        
        if not category_type or not category_value:
            return jsonify([])
        
        images = DB.get_images_by_date_range('', '')
        filtered_images = [img for img in images if f"{category_type}_{category_value}" in img['category']]
        
        return jsonify(filtered_images)
    except Exception as e:
        logger.error(f"Virhe kuvien haussa kategorian perusteella: {e}")
        return jsonify([])

@app.route('/api/debug')
def debug_info():
    """Debug-tietoja ongelmanratkaisua varten"""
    try:
        if not CLASSIFICATION_AVAILABLE:
            return jsonify({'error': 'Luokittelu ei ole saatavilla'})
        
        total_images = len(DB.images)
        categories = DB.get_categories()
        
        classified_path = Path('/data/classified')
        year_images = list(classified_path.rglob('01_vuodet/*/*.jpg')) + list(classified_path.rglob('01_vuodet/*/*.png'))
        month_images = list(classified_path.rglob('02_kuukaudet/*/*.jpg')) + list(classified_path.rglob('02_kuukaudet/*/*.png'))
        day_images = list(classified_path.rglob('04_paivat/*/*.jpg')) + list(classified_path.rglob('04_paivat/*/*.png'))
        
        test_images = DB.get_images_by_date_range('', '')
        
        return jsonify({
            'database': {
                'total_images': total_images,
                'categories_count': len(categories),
                'categories_sample': categories[:10] if categories else []
            },
            'filesystem': {
                'year_images': len(year_images),
                'month_images': len(month_images),
                'day_images': len(day_images),
                'year_folders': len(list(classified_path.glob('01_vuodet/*'))),
                'month_folders': len(list(classified_path.glob('02_kuukaudet/*'))),
                'day_folders': len(list(classified_path.glob('04_paivat/*')))
            },
            'api_test': {
                'images_found': len(test_images),
                'sample_images': [img['filename'] for img in test_images[:5]] if test_images else []
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/debug_compare')
def debug_compare():
    """Debug-tietoja vertailusivun ongelmanratkaisua varten"""
    try:
        if not CLASSIFICATION_AVAILABLE:
            return jsonify({'error': 'Luokittelu ei ole saatavilla'})
        
        test_dates = [
            '2023-10-15',
            '2023-10-16', 
            '2024-01-01'
        ]
        
        results = {}
        for test_date in test_dates:
            images = DB.get_images_by_date_range(test_date, test_date)
            results[test_date] = {
                'images_found': len(images),
                'sample': [img['filename'] for img in images[:3]] if images else []
            }
        
        total_images = len(DB.images)
        date_range = DB.get_date_range()
        
        return jsonify({
            'database': {
                'total_images': total_images,
                'date_range': {
                    'start': date_range[0].isoformat() if date_range[0] else 'None',
                    'end': date_range[1].isoformat() if date_range[1] else 'None'
                }
            },
            'test_results': results,
            'all_categories': DB.get_categories()[:10]
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/rescan')
def rescan_images():
    """Pakota kuvien uudelleenskannaus"""
    try:
        if not CLASSIFICATION_AVAILABLE:
            return jsonify({'success': False, 'error': 'Luokittelu ei ole saatavilla'})
        
        added_count = DB.scan_for_images()
        return jsonify({'success': True, 'added_count': added_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def index():
    """Pääsivu"""
    try:
        if CLASSIFICATION_AVAILABLE:
            date_range = DB.get_date_range()
            categories = DB.get_categories()
            
            start_date = date_range[0].strftime('%Y-%m-%d') if date_range[0] else ''
            end_date = date_range[1].strftime('%Y-%m-%d') if date_range[1] else ''
        else:
            start_date = ''
            end_date = ''
            categories = []
        
        return render_template('index.html', 
                             start_date=start_date,
                             end_date=end_date,
                             categories=categories,
                             classification_available=CLASSIFICATION_AVAILABLE)
    except Exception as e:
        logger.error(f"Virhe pääsivulla: {e}")
        return f"<h1>Kuvien Selaus</h1><p>Sovellus käynnistyy, mutta luokitteluominaisuudet eivät ole saatavilla. Tarkista logit.</p>"

@app.route('/api/images')
def get_images():
    """Hae kuvat aikavälin perusteella ilman duplikaatteja"""
    try:
        if not CLASSIFICATION_AVAILABLE:
            return jsonify([])
            
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        time_unit = request.args.get('time_unit', '')
        time_value = request.args.get('time_value', '')
        
        images = DB.get_unique_images_by_date_range(start_date, end_date)
        
        if time_unit and time_value:
            images = [img for img in images if f"{time_unit}_{time_value}" in img['category']]
        
        logger.info(f"Palautetaan {len(images)} uniikkia kuvaa aikavälillä {start_date} - {end_date}")
        return jsonify(images)
    except Exception as e:
        logger.error(f"Virhe kuvien haussa: {e}")
        return jsonify([])

@app.route('/api/unique_images')
def get_unique_images():
    """Hae uniikit kuvat aikavälin perusteella (vaihtoehtoinen tapa)"""
    try:
        if not CLASSIFICATION_AVAILABLE:
            return jsonify([])
            
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        all_images = DB.get_images_by_date_range(start_date, end_date)
        
        unique_images = []
        seen_filenames = set()
        
        for image in all_images:
            if image['filename'] not in seen_filenames:
                seen_filenames.add(image['filename'])
                unique_images.append(image)
        
        logger.info(f"Palautetaan {len(unique_images)} uniikkia kuvaa (alkuperäisesti {len(all_images)})")
        return jsonify(unique_images)
    except Exception as e:
        logger.error(f"Virhe uniikkien kuvien haussa: {e}")
        return jsonify([])

@app.route('/api/search_images')
def search_images():
    """Hae kuvia hakukyselyllä (nimi tai kategoria)"""
    try:
        q = (request.args.get('q') or '').strip().lower()
        if not CLASSIFICATION_AVAILABLE:
            return jsonify([])
        images = DB.get_unique_images_by_date_range('', '')
        if not q:
            return jsonify(images)
        filtered = [img for img in images if q in img['filename'].lower() or q in img['category'].lower()]
        return jsonify(filtered)
    except Exception as e:
        logger.error(f"Virhe haussa: {e}")
        return jsonify([])

@app.route('/api/image_by_path')
def image_by_path():
    """Palauttaa yhden kuvan tiedot polun perusteella (esim. istunnosta valittu)"""
    try:
        p = request.args.get('path', '')
        if not CLASSIFICATION_AVAILABLE or not p:
            return jsonify({})
        info = DB.images.get(p)
        if not info:
            return jsonify({})
        return jsonify({
            'path': p,
            'timestamp': info['timestamp'],
            'category': info['category'],
            'filename': info['filename'],
            'date_display': datetime.fromisoformat(info['timestamp']).strftime('%Y-%m-%d %H:%M:%S') if info['timestamp'] else ''
        })
    except Exception as e:
        logger.error(f"Virhe image_by_path: {e}")
        return jsonify({})

@app.route('/api/classify', methods=['POST'])
def classify_images():
    """Suorita kuvien luokittelu"""
    if not CLASSIFICATION_AVAILABLE:
        return jsonify({'success': False, 'error': 'Luokittelumoduulia ei ole saatavilla'})
    
    try:
        source_dir = '/data/source'
        target_dir = '/data/classified'
        
        result = classify_images_hierarchical(source_dir, target_dir, DB)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']})
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Virhe luokittelussa: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/rtsp/start', methods=['POST'])
def api_rtsp_start():
    """Käynnistä RTSP -> HLS stream (palauttaa playlist polun)"""
    try:
        if not _RTPS_AVAILABLE:
            return jsonify({'error': 'RTSP manager ei ole saatavilla'}), 500
        data = request.get_json() or {}
        url = data.get('url')
        if not url:
            return jsonify({'error': 'no url provided'}), 400
        result = start_rtsp_to_hls(url)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Virhe RTSP startissa: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rtsp/stop', methods=['POST'])
def api_rtsp_stop():
    """Pysäytä RTSP stream stream_id:llä tai url:llä"""
    try:
        if not _RTPS_AVAILABLE:
            return jsonify({'error': 'RTSP manager ei ole saatavilla'}), 500
        data = request.get_json() or {}
        stream_id = data.get('stream_id')
        url = data.get('url')
        if stream_id:
            res = stop_rtsp_stream(stream_id)
        elif url:
            res = stop_rtsp_stream_by_url(url)
        else:
            return jsonify({'error': 'no stream_id or url provided'}), 400
        return jsonify(res)
    except Exception as e:
        logger.error(f"Virhe RTSP stopissa: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Palvele kuvia"""
    try:
        return send_from_directory('/data/classified', filename)
    except Exception as e:
        logger.error(f"Virhe kuvan palvelussa: {e}")
        return "Kuvaa ei löytynyt", 404

@app.route('/api/categories')
def get_categories():
    """Hae kaikki kategoriat"""
    if not CLASSIFICATION_AVAILABLE:
        return jsonify([])
    try:
        categories = DB.get_categories()
        return jsonify(categories)
    except Exception as e:
        logger.error(f"Virhe kategorioiden haussa: {e}")
        return jsonify([])

@app.route('/api/date_range')
def get_date_range():
    """Hae kuvien aikaväli"""
    if not CLASSIFICATION_AVAILABLE:
        return jsonify({'start': '', 'end': ''})
    try:
        date_range = DB.get_date_range()
        if date_range[0] and date_range[1]:
            return jsonify({
                'start': date_range[0].isoformat(),
                'end': date_range[1].isoformat()
            })
        return jsonify({'start': '', 'end': ''})
    except Exception as e:
        logger.error(f"Virhe aikavälin haussa: {e}")
        return jsonify({'start': '', 'end': ''})

@app.route('/compare')
def compare_view():
    """Kuvavertailusivu"""
    return render_template('compare.html')

@app.route('/health')
def health_check():
    """Terveystarkistus"""
    return jsonify({'status': 'healthy', 'classification_available': CLASSIFICATION_AVAILABLE, 'rtsp_available': _RTPS_AVAILABLE})

if __name__ == '__main__':
    # Varmista että templatit-kansio on olemassa
    template_dir = Path(__file__).parent / 'templates'
    template_dir.mkdir(exist_ok=True)
    
    # Luo templatit
    create_templates()
    
    logger.info("Käynnistetään sovellus...")
    app.run(host='0.0.0.0', port=5000, debug=True)
