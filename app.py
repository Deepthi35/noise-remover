from flask import Flask, request, send_file, redirect, url_for, render_template_string
import noisereduce as nr
import librosa
import soundfile as sf
import os
import uuid

app = Flask(__name__)

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
    # Check if the audio file is part of the request
    if 'audio_file' not in request.files:
        return 'No file part', 400
    audio_file = request.files['audio_file']
    
    if audio_file.filename == '':
        return 'No selected file', 400

    # Save the uploaded file
    input_file_path = os.path.join("uploads", audio_file.filename)
    audio_file.save(input_file_path)

    # Load the audio file
    y, sr = librosa.load(input_file_path, sr=None)

    # Apply noise reduction
    y_denoised = nr.reduce_noise(y=y, sr=sr)

    # Normalize the denoised audio to improve loudness
    y_normalized = librosa.util.normalize(y_denoised)

    # Generate unique code and construct output filename
    base_name, _ = os.path.splitext(audio_file.filename)
    unique_code = uuid.uuid4().hex[:8]
    output_filename = f"{base_name}_{unique_code}.wav"
    output_file_path = os.path.join("uploads", output_filename)
    sf.write(output_file_path, y_normalized, sr)

    # Optionally, remove the original uploaded file to save space
    os.remove(input_file_path)

    # Redirect to result page
    return redirect(url_for('result', filename=output_filename))

@app.route('/result/<filename>')
def result(filename):
    audio_url = url_for('uploaded_file', filename=filename)
    download_url = url_for('download_file', filename=filename)
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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join('uploads', filename))

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join('uploads', filename), as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
