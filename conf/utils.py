import base64


def imagen_base64(path: str):
    with open(path, "rb") as f:
        base64_img = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{base64_img}"