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

    # Filtros normais
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

    # =========================================================
    # VÍDEO NORMAL
    # =========================================================
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

    # =========================================================
    # REVERSE ESTILO EDIT
    # =========================================================
    else:

        # Descobre a duração do vídeo
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

        # A cada 2 segundos:
        # normal -> reverse rápido
        INTERVAL = 2.0

        # Trecho usado para o reverse
        REVERSE_SOURCE = 0.6

        # O reverse fica 2x mais rápido
        REVERSE_SPEED = 2.0

        parts = []

        start = 0.0
        index = 0

        while start < duration - 0.01:

            end = min(start + INTERVAL, duration)
            length = end - start

            # Vídeos muito curtos
            if length <= 0.7:

                parts.append(
                    f"[0:v]{normal_filter},"
                    f"trim=start={start}:end={end},"
                    f"setpts=PTS-STARTPTS[v{index}]"
                )

            else:

                # Parte normal
                normal_end = max(start, end - 0.3)

                parts.append(
                    f"[0:v]{normal_filter},"
                    f"trim=start={start}:end={normal_end},"
                    f"setpts=PTS-STARTPTS[n{index}]"
                )

                # Últimos 0.6 segundos são invertidos
                reverse_start = max(start, end - REVERSE_SOURCE)

                parts.append(
                    f"[0:v]{normal_filter},"
                    f"trim=start={reverse_start}:end={end},"
                    f"setpts=PTS-STARTPTS,"
                    f"reverse,"
                    f"setpts=PTS/{REVERSE_SPEED}[r{index}]"
                )

                # Junta normal + reverse rápido
                parts.append(
                    f"[n{index}][r{index}]"
                    f"concat=n=2:v=1:a=0[v{index}]"
                )

            start += INTERVAL
            index += 1

        # Junta todos os pedaços
        video_inputs = "".join(
            f"[v{i}]" for i in range(index)
        )

        parts.append(
            f"{video_inputs}"
            f"concat=n={index}:v=1:a=0[outv]"
        )

        filter_complex = ";".join(parts)

        command = [
            "ffmpeg",
            "-i", input_file,

            "-filter_complex", filter_complex,

            "-map", "[outv]",
            "-map", "0:a?",

            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-profile:v", "main",
            "-level", "4.0",

            "-c:a", "aac",
            "-b:a", "128k",

            "-movflags", "+faststart",
            "-preset", "fast",

            "-shortest",
            "-y",
            output_file
        ]

    subprocess.run(command, check=True)

    return FileResponse(
        output_file,
        media_type="video/mp4",
        filename="video_editado.mp4"
    )
