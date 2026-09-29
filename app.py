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
    video_filters = []

    if zoom > 1:
        video_filters.append(
            f"scale=iw*{zoom}:ih*{zoom},"
            f"crop=iw/{zoom}:ih/{zoom}"
        )

    video_filters.append(
        f"eq=brightness={brightness}:contrast={contrast}"
    )

    normal_filter = ",".join(video_filters)

    if reverse:
        # Reverse estilo edit:
        # NORMAL -> REVERSE RÁPIDO -> NORMAL -> REVERSE RÁPIDO
        filter_complex = (
            f"[0:v]{normal_filter},split=4[v1][v2][v3][v4];"
            f"[v2]reverse,setpts=0.35*PTS[vr1];"
            f"[v4]reverse,setpts=0.35*PTS[vr2];"
            f"[0:a]asplit=4[a1][a2][a3][a4];"
            f"[a2]areverse,atempo=2,atempo=1.428571[a2r];"
            f"[a4]areverse,atempo=2,atempo=1.428571[a4r];"
            f"[v1][a1][vr1][a2r][v3][a3][vr2][a4r]"
            f"concat=n=4:v=1:a=1[outv][outa]"
        )

        command = [
            "ffmpeg",
            "-i", input_file,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
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

    else:
        # Edição normal sem reverse
        filter_complex = normal_filter

        command = [
            "ffmpeg",
            "-i", input_file,
            "-vf", filter_complex,
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

    subprocess.run(command, check=True)

    return FileResponse(
        output_file,
        media_type="video/mp4",
        filename="video_editado.mp4"
    )
