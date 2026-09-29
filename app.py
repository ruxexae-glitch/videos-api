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

    if reverse:
        filters.append("reverse")

    filter_complex = ",".join(filters)

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
