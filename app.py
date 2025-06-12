from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import yt_dlp
import uuid

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"

# Ensure download folder exists
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route("/")
def index():
    error = request.args.get('error')
    return render_template("index.html", error=error)

@app.route("/process_url", methods=["POST"])
def process_url():
    url = request.form.get("url")
    if not url:
        return redirect(url_for("index", error="Please enter a URL"))
    
    # Check if it's a YouTube URL
    if "youtube.com" in url or "youtu.be" in url:
        return redirect(url_for("youtube", url=url))
    # Check if it's an Instagram URL
    elif "instagram.com" in url:
        return redirect(url_for("instagram", url=url))
    else:
        return redirect(url_for("index", error="Unsupported URL. Please provide a YouTube or Instagram URL."))

@app.route("/instagram", methods=["GET", "POST"])
def instagram():
    video_info = None
    error = None
    url = request.args.get("url") or (request.form.get("url") if request.method == "POST" else None)
    
    if url:
        try:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "force_generic_extractor": False,
                "extract_flat": False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get best video format with audio
                video_formats = [
                    f for f in info.get("formats", [])
                    if f.get("vcodec") != "none" and f.get("acodec") != "none"  # Must have both video and audio
                ]
                
                # Sort by quality (highest first)
                video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                
                # Get audio-only formats
                audio_formats = [
                    f for f in info.get("formats", [])
                    if f.get("vcodec") == "none" and f.get("acodec") != "none"
                ]
                
                # Sort audio formats by quality
                audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
                
                if not video_formats and not audio_formats:
                    raise Exception("No downloadable formats found")
                
                # Get the best thumbnail
                thumbnails = info.get('thumbnails', [])
                thumbnail = info.get('thumbnail') or (thumbnails[-1]['url'] if thumbnails else None)
                
                video_info = {
                    "title": info.get("title") or "Instagram Video",
                    "video_formats": video_formats,
                    "audio_formats": audio_formats,
                    "url": url,
                    "thumbnail": thumbnail
                }
        except Exception as e:
            error = str(e)
            video_info = None
            
    return render_template("instagram.html", video_info=video_info, error=error)

@app.route("/youtube", methods=["GET", "POST"])
def youtube():
    video_info = None
    error = None
    url = request.args.get("url") or (request.form.get("url") if request.method == "POST" else None)
    
    if url:
        try:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "force_generic_extractor": False,
                "noplaylist": True,
                "extract_flat": False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get video formats
                video_formats = [
                    f for f in info.get("formats", [])
                    if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("ext") == "mp4"
                ]
                
                # Get audio-only formats
                audio_formats = [
                    f for f in info.get("formats", [])
                    if f.get("vcodec") == "none" and f.get("acodec") != "none"
                ]
                
                if not video_formats and not audio_formats:
                    raise Exception("No downloadable formats found")
                
                video_info = {
                    "title": info.get("title"),
                    "video_formats": video_formats,
                    "audio_formats": audio_formats,
                    "url": url,
                    "thumbnail": info.get("thumbnail")
                }
        except Exception as e:
            error = str(e)
            video_info = None
            
    return render_template("youtube.html", video_info=video_info, error=error)

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    format_id = request.form.get("format_id")
    source = request.form.get("source")  # 'instagram' or 'youtube'
    file_id = str(uuid.uuid4())[:8]
    
    # Determine file extension based on source and format type
    if source == "youtube" and "audioonly" in format_id.lower():
        filename = f"{file_id}.mp3"
    else:
        filename = f"{file_id}.mp4"
        
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    ydl_opts = {
        "format": format_id,
        "outtmpl": filepath,
        "noplaylist": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return f"Download error: {str(e)}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)