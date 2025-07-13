from flask import Flask, request, send_file, redirect, url_for, render_template_string, abort
import noisereduce as nr
import librosa
import soundfile as sf
import os
import uuid
import io

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB limit

audio_store = {}  # In-memory store for processed audio

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template_string('''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>File Too Large</title>
        <style>
            body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); min-height: 100vh; margin: 0; font-family: 'Segoe UI', Arial, sans-serif; display: flex; align-items: center; justify-content: center; }
            .container { background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(30,60,114,0.15); padding: 40px 32px 32px 32px; max-width: 400px; width: 100%; text-align: center; }
            h1 { color: #1e3c72; margin-bottom: 12px; }
            .subtitle { color: #2a5298; font-size: 1.1rem; margin-bottom: 28px; }
            .try-another-btn { background: #fff; color: #2a5298; border: 2px solid #2a5298; border-radius: 8px; padding: 12px 0; font-size: 1.1rem; font-weight: bold; cursor: pointer; transition: background 0.2s; width: 100%; margin-top: 14px; text-decoration: none; display: inline-block; }
            .try-another-btn:hover { background: #2a5298; color: #fff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>File Too Large</h1>
            <div class="subtitle">You can only upload audio files up to 10 MB in size. Please choose a smaller file.</div>
            <a href="/" class="try-another-btn">Try Another</a>
        </div>
    </body>
    </html>
    '''), 413

@app.route('/')
def index():
    return '''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload Audio for Noise Reduction</title>
        <style>
            body {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                margin: 0;
                font-family: 'Segoe UI', Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: #fff;
                border-radius: 16px;
                box-shadow: 0 4px 24px rgba(30,60,114,0.15);
                padding: 40px 32px 32px 32px;
                max-width: 400px;
                width: 100%;
                text-align: center;
            }
            h1 {
                color: #1e3c72;
                margin-bottom: 12px;
            }
            .subtitle {
                color: #2a5298;
                font-size: 1.1rem;
                margin-bottom: 28px;
            }
            .file-limit {
                color: #d32f2f;
                font-size: 1rem;
                margin-bottom: 18px;
            }
            form {
                display: flex;
                flex-direction: column;
                gap: 18px;
            }
            input[type="file"] {
                border: 2px solid #2a5298;
                border-radius: 8px;
                padding: 8px;
                background: #f4f8fb;
                color: #1e3c72;
                font-size: 1rem;
            }
            button {
                background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 12px 0;
                font-size: 1.1rem;
                font-weight: bold;
                cursor: pointer;
                transition: background 0.2s;
            }
            button:hover {
                background: linear-gradient(90deg, #2a5298 0%, #1e3c72 100%);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Audio Noise Remover</h1>
            <div class="subtitle">Easily remove background noise from your audio files. Upload your audio and get a cleaner, clearer sound in seconds!</div>
            <div class="file-limit">Maximum file size: 10 MB</div>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="audio_file" accept=".wav, .mp3, .flac" required>
                <button type="submit">Upload and Process</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_file' not in request.files:
        return 'No file part', 400
    audio_file = request.files['audio_file']
    if audio_file.filename == '':
        return 'No selected file', 400

    # Read the uploaded file into memory
    audio_bytes = audio_file.read()
    audio_buffer = io.BytesIO(audio_bytes)

    # Load the audio file from memory
    y, sr = librosa.load(audio_buffer, sr=None)

    # Apply noise reduction
    y_denoised = nr.reduce_noise(y=y, sr=sr)

    # Normalize the denoised audio
    y_normalized = librosa.util.normalize(y_denoised)

    # Write the processed audio to a BytesIO object
    output_buffer = io.BytesIO()
    sf.write(output_buffer, y_normalized, sr, format='WAV')
    output_buffer.seek(0)

    # Store the processed audio in the in-memory store
    audio_id = str(uuid.uuid4())
    audio_store[audio_id] = {
        'audio': output_buffer.getvalue(),
        'filename': os.path.splitext(audio_file.filename)[0] + '_denoised.wav'
    }

    return redirect(url_for('result', audio_id=audio_id))

@app.route('/result')
def result():
    audio_id = request.args.get('audio_id')
    audio_url = url_for('preview_audio', audio_id=audio_id)
    download_url = url_for('download_audio', audio_id=audio_id)
    return render_template_string('''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Processed Audio Result</title>
        <style>
            body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); min-height: 100vh; margin: 0; font-family: 'Segoe UI', Arial, sans-serif; display: flex; align-items: center; justify-content: center; }
            .container { background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(30,60,114,0.15); padding: 40px 32px 32px 32px; max-width: 400px; width: 100%; text-align: center; }
            h1 { color: #1e3c72; margin-bottom: 12px; }
            .subtitle { color: #2a5298; font-size: 1.1rem; margin-bottom: 28px; }
            .audio-player { margin: 24px 0; }
            .download-btn { background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); color: #fff; border: none; border-radius: 8px; padding: 12px 0; font-size: 1.1rem; font-weight: bold; cursor: pointer; transition: background 0.2s; width: 100%; margin-top: 18px; text-decoration: none; display: inline-block; }
            .download-btn:hover { background: linear-gradient(90deg, #2a5298 0%, #1e3c72 100%); }
            .try-another-btn { background: #fff; color: #2a5298; border: 2px solid #2a5298; border-radius: 8px; padding: 12px 0; font-size: 1.1rem; font-weight: bold; cursor: pointer; transition: background 0.2s; width: 100%; margin-top: 14px; text-decoration: none; display: inline-block; }
            .try-another-btn:hover { background: #2a5298; color: #fff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Noise Removed!</h1>
            <div class="subtitle">Listen to your cleaned audio below. You can play it or download it to your device.</div>
            <div class="audio-player">
                <audio controls style="width:100%">
                    <source src="{{ audio_url }}" type="audio/wav">
                    Your browser does not support the audio element.
                </audio>
            </div>
            <a href="{{ download_url }}" class="download-btn" download>Download Processed Audio</a>
            <a href="/" class="try-another-btn">Try Another</a>
        </div>
    </body>
    </html>
    ''', audio_url=audio_url, download_url=download_url)

@app.route('/preview_audio')
def preview_audio():
    audio_id = request.args.get('audio_id')
    audio_entry = audio_store.get(audio_id)
    if not audio_entry:
        return 'No audio to preview', 404
    return send_file(io.BytesIO(audio_entry['audio']), mimetype='audio/wav')

@app.route('/download_audio')
def download_audio():
    audio_id = request.args.get('audio_id')
    audio_entry = audio_store.get(audio_id)
    if not audio_entry:
        return 'No audio to download', 404
    return send_file(io.BytesIO(audio_entry['audio']), mimetype='audio/wav', as_attachment=True, download_name=audio_entry['filename'])

if __name__ == "__main__":
    app.run(debug=True)
