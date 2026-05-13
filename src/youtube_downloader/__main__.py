import os
from flask import Flask, request, render_template
import yt_dlp

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            ydl_opts = {
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'format': 'best'
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                message = f"Successfully downloaded video from {url}"
            except Exception as e:
                message = f"Error: {str(e)}"
    return render_template("index.html", message=message)

def main():
    app.run(debug=True)

if __name__ == "__main__":
    main()