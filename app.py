from flask import (
    Flask,
    request,
    send_from_directory,
    render_template_string,
    render_template,
)
import os
import qrcode
import io
import base64

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def generate_qr(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@app.route("/")
def get_name():
    return render_template("index.html")


@app.route("/upload_page")
def index():
    files = os.listdir(UPLOAD_FOLDER)
    qr_upload = generate_qr(request.host_url + "upload/")
    print(qr_upload)
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>ShareWave</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
          <div class="container mt-5">
            <div class="row">
              <div class="col-12">
                <h1 class="text-center">
                  <img src="https://i.ibb.co/Yh0Nywm/logo.png" alt="ShareWave" width="200" height="150">
                </h1>
                <script>
                  document.addEventListener('DOMContentLoaded', function() {
                    const userName = localStorage.getItem('userName');
                    if (userName) {
                      document.getElementById('welcome-message').textContent = 'Welcome, ' + userName + '!';
                    }
                  });
                </script>
                <div class="text-center">
                  <h3 id="welcome-message"></h3>
                </div>
                <h2 class="mt-4">Upload new File</h2>
                <form method="post" enctype="multipart/form-data" action="/upload/">
                  <div class="mb-3">
                    <input type="file" class="form-control" name="file" multiple>
                  </div>
                  <button type="submit" class="btn btn-primary">Upload</button>
                </form>
                <h2 class="mt-4">Files</h2>
                <form method="get" action="{{ url_for('download_multiple_files') }}">
                  <ul class="list-group">
                    {% for file in files %}
                      <li class="list-group-item">
                        <input type="checkbox" name="files" value="{{ file }}"> {{ file }}
                      </li>
                    {% endfor %}
                  </ul>
                  <button type="submit" class="btn btn-success mt-3">Download Selected</button>
                </form>
                <h2 class="mt-4">QR Codes</h2>
                <p>Scan to upload files:</p>
                <img src="data:image/png;base64,{{ qr_upload }}" class="img-fluid">
                <h3 class="mt-4">Generate QR to download selected files:</h3>
                <form method="post" action="{{ url_for('generate_download_qr') }}">
                  <ul class="list-group">
                    {% for file in files %}
                      <li class="list-group-item">
                        <input type="checkbox" name="files" value="{{ file }}"> {{ file }}
                      </li>
                    {% endfor %}
                  </ul>
                  <button type="submit" class="btn btn-warning mt-3">Generate QR</button>
                </form>
              </div>
            </div>
          </div>
          <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """,
        files=files,
        qr_upload=qr_upload,
    )


@app.route("/upload/", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file part"
    files = request.files.getlist("file")
    if not files or files[0].filename == "":
        return "No selected file"
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        print(f"File saved: {file_path}")
    return "Files successfully uploaded"


@app.route("/download/<filename>")
def download(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    print(f"Attempting to download: {file_path}")
    if os.path.isfile(file_path):
        print(f"File exists: {file_path}")
        return send_from_directory(
            os.path.abspath(UPLOAD_FOLDER), filename, as_attachment=True
        )
    print(f"File not found: {file_path}")
    return f"File '{filename}' not found."


@app.route("/download_multiple_files")
def download_multiple_files():
    files = request.args.getlist("files")
    if not files:
        return "No files selected"

    valid_files = [
        file for file in files if os.path.isfile(os.path.join(UPLOAD_FOLDER, file))
    ]

    if not valid_files:
        return "Selected files not found on the server."

    print(f"Valid files for download: {valid_files}")

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Download Selected Files</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
          <div class="container mt-5">
            <h1>Downloading Selected Files...</h1>
            <div class="progress" style="height: 30px;">
              <div id="progress-bar" class="progress-bar" role="progressbar" style="width: 0%;"></div>
            </div>
          </div>
          <script>
            document.addEventListener('DOMContentLoaded', function() {
              var files = {{ files | tojson }};
              var progressBar = document.getElementById('progress-bar');
              var totalFiles = files.length;
              var downloadedFiles = 0;

              files.forEach(function(file, index) {
                setTimeout(function() {
                  var link = document.createElement('a');
                  link.href = '/download/' + encodeURIComponent(file);
                  link.download = file;
                  link.click();

                  downloadedFiles++;
                  var progressPercentage = (downloadedFiles / totalFiles) * 100;
                  progressBar.style.width = progressPercentage + '%';

                  if (downloadedFiles === totalFiles) {
                    setTimeout(function() {
                      progressBar.parentElement.innerHTML = '<h2>All files downloaded successfully!</h2>';
                      fetch('/clear_uploads_folder/', {method: 'POST'});
                    }, 500);
                  }
                }, index * 1000);
              });
            });
          </script>
          <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """,
        files=valid_files,
    )


@app.route("/generate_download_qr", methods=["POST"])
def generate_download_qr():
    files = request.form.getlist("files")
    if not files:
        return "No files selected"

    files_param = "&".join([f"files={file}" for file in files])
    download_url = request.host_url + "download_multiple_files?" + files_param
    qr_code = generate_qr(download_url)

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>QR Code for Downloading Selected Files</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
          <div class="container mt-5 text-center">
            <h1>QR Code Generated</h1>
            <p>Scan to download selected files:</p>
            <div id="qr-container">
              <h2 id="countdown">10</h2>
              <img id="qr-image" src="data:image/png;base64,{{ qr_code }}" class="img-fluid">
              <p id="qr-expired" class="text-danger" style="display: none;">QR expired</p>
            </div>
            <div class="mt-4">
              <a href="/" class="btn btn-primary">Go back</a>
            </div>
          </div>
          <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
          <script>
            let countdown = 10;
            const countdownElement = document.getElementById('countdown');
            const qrImage = document.getElementById('qr-image');
            const qrExpired = document.getElementById('qr-expired');

            const interval = setInterval(() => {
              countdown--;
              countdownElement.textContent = countdown;
              if (countdown <= 0) {
                clearInterval(interval);
                qrImage.src = '';
                qrExpired.style.display = 'block';
                countdownElement.style.display = 'none';
              }
            }, 1000);
          </script>
        </body>
        </html>
        """,
        qr_code=qr_code,
    )


@app.route("/clear_uploads_folder/", methods=["POST"])
def clear_uploads_folder_route():
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)
    return "Uploads folder cleared"


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8000)
