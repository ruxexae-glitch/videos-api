from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import uuid
import subprocess
import os

app = FastAPI()

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)


@app.get("/")
def home():
    return {"status": "API funcionando"}


@app.post("/edit")
async def edit_video(
    video: UploadFile = File(...),
    reverse: bool = Form(False),
    zoom: float = Form(1.0),
    brightness: float = Form(0.0),
    contrast: float = Form(1.0)
):
    video_id = str(uuid.uuid4())

    input_file = f"uploads/{video_id}_{video.filename}"
    output_file = f"outputs/{video_id}.mp4"

    with open(input_file, "wb") as f:
        f.write(await video.read())

    filters = []

    if zoom > 1:
        filters.append(
            f"scale=iw*{zoom}:ih*{zoom},"
            f"crop=iw/{zoom}:ih/{zoom}"
        )

    filters.append(
        f"eq=brightness={brightness}:contrast={contrast}"
    )

    normal_filter = ",".join(filters)

    # ==================================================
    # MODO NORMAL
    # ==================================================

    if not reverse:

        command = [
            "ffmpeg",
            "-i", input_file,

            "-vf", normal_filter,

            "-map", "0:v:0",
            "-map", "0:a?",

            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-profile:v", "main",
            "-level", "4.0",

            "-c:a", "aac",
            "-b:a", "128k",

            "-movflags", "+faststart",
            "-preset", "fast",

            "-y",
            output_file
        ]

    # ==================================================
    # REVERSE ESTILO EDIT
    # ==================================================

    else:

        # Descobre duração
        probe = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_file
            ],
            capture_output=True,
            text=True,
            check=True
        )

        duration = float(probe.stdout.strip())

        # Tamanho de cada "puxada"
        # 0.33s normal + 0.33s voltando
        STEP = 0.33

        parts = []
        labels = []

        start = 0.0
        index = 0

        while start < duration - 0.001:

            end = min(start + STEP, duration)

            # ==========================================
            # TRECHO NORMAL
            # ==========================================

            parts.append(
                f"[0:v]"
                f"{normal_filter},"
                f"trim=start={start}:end={end},"
                f"setpts=PTS-STARTPTS"
                f"[f{index}]"
            )

            # ==========================================
            # MESMO TRECHO AO CONTRÁRIO
            # ==========================================

            parts.append(
                f"[0:v]"
                f"{normal_filter},"
                f"trim=start={start}:end={end},"
                f"setpts=PTS-STARTPTS,"
                f"reverse"
                f"[r{index}]"
            )

            # ==========================================
            # NORMAL + REVERSE
            # ==========================================

            parts.append(
                f"[f{index}][r{index}]"
                f"concat=n=2:v=1:a=0"
                f"[v{index}]"
            )

            labels.append(f"[v{index}]")

            start = end
            index += 1

        # Junta todos os ciclos
        parts.append(
            "".join(labels) +
            f"concat=n={len(labels)}:v=1:a=0"
            f"[outv]"
        )

        filter_complex = ";".join(parts)

        command = [
            "ffmpeg",
            "-i", input_file,

            "-filter_complex", filter_complex,

            "-map", "[outv]",
            "-an",

            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-profile:v", "main",
            "-level", "4.0",

            "-movflags", "+faststart",
            "-preset", "fast",

            "-y",
            output_file
        ]

    subprocess.run(command, check=True)

    return FileResponse(
        output_file,
        media_type="video/mp4",
        filename="video_editado.mp4"
    )
 
            
