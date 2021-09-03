from typing import Any, Dict, List
from pydantic import BaseModel
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import ORJSONResponse
from fastapi.responses import Response, StreamingResponse
from typing import Optional
import aiofiles
from pydantic.fields import T

from starlette.responses import JSONResponse
from uuid import uuid4
import base64
import asyncio
import os
from starlette.responses import FileResponse


router = APIRouter()


@router.post(
    "/sign-pdf",
    description="""
    Call this API for PDF Document Signing
    """,
)
async def sign_view(
    output_format: str = Form(
        "file", description='Output format either "file" or "base64"'
    ),
    pdf_to_sign: Optional[UploadFile] = File(None, description="PDF File to be signed"),
    pdf_to_sign_base64: Optional[str] = Form(
        None, description="PDF File to be signed (Base64)"
    ),
    bg: Optional[UploadFile] = File(None, description="Background Graphics"),
    bg_ext: Optional[str] = File(
        None, description="Background Graphics File Extension like png, jpg etc"
    ),
    bg_base64: Optional[str] = Form(None, description="Background Graphics (Base64)"),
    l2_text: Optional[str] = Form("", description="Signature text"),
    page_no: Optional[int] = Form(1, description="Page No where signature to be shown"),
    llx: Optional[float] = Form(
        78, description="lower left corner postion on X-axis of a visible signature"
    ),
    lly: Optional[float] = Form(
        66, description="lower left corner postion on Y-axis of a visible signature"
    ),
    urx: Optional[float] = Form(
        255, description="upper right corner postion on X-axis of a visible signature"
    ),
    ury: Optional[float] = Form(
        136, description="upper right corner postion on Y-axis of a visible signature"
    ),
):
    if pdf_to_sign and pdf_to_sign_base64:
        return JSONResponse(
            {"error": "Any one of pdf_to_sign or pdf_to_sign_base64 requried"},
            status_code=400,
        )

    if bg and bg_base64:
        return JSONResponse(
            {"error": "Any one of bg or bg_base64 requried"},
            status_code=400,
        )

    pdf_file_id = uuid4().hex
    pdf_file_path = f"/tmp/{pdf_file_id}.pdf"
    pdf_out_file_path = f"/tmp/{pdf_file_id}_signed.pdf"
    if pdf_to_sign_base64:
        async with aiofiles.open(pdf_file_path, "wb") as f:
            await f.write(base64.decodebytes(pdf_to_sign_base64.encode("ASCII")))
    else:
        async with aiofiles.open(pdf_file_path, "wb") as f:
            await f.write(pdf_to_sign.file.read())

    bg_file_path = f"/tmp/{uuid4().hex}.{bg_ext}"
    has_bg = False
    if bg_base64:
        has_bg = True
        async with aiofiles.open(bg_file_path, "wb") as f:
            await f.write(base64.decodebytes(bg_base64.encode("ASCII")))
    if bg:
        has_bg = True
        async with aiofiles.open(bg_file_path, "wb") as f:
            await f.write(bg.file.read())

    cert_path = os.environ.get("PFX_PATH", "/app/cert.pfx")
    cert_passcode = os.environ.get("PFX_PASSCODE")
    cmd = [
        "java",
        "-jar",
        "/jsignpdf/JSignPdf.jar",
        pdf_file_path,
        "--out-directory",
        "/tmp",
        "-ksf",
        cert_path,
        "-ksp",
        cert_passcode,
        # "--visible-signature",
        # "--render-mode",
        # "GRAPHIC_AND_DESCRIPTION",
        "-cl",
        "CERTIFIED_NO_CHANGES_ALLOWED",
        "--disable-acrobat6-layer-mode",
    ]

    if not has_bg:
        render_mode = "DESCRIPTION_ONLY"
    else:
        render_mode = "GRAPHIC_AND_DESCRIPTION"

    if render_mode == "DESCRIPTION_ONLY":
        cmd += [
            "--visible-signature",
            "--render-mode",
            render_mode,
            "-pg",
            str(page_no),
            "-llx",
            str(llx),
            "-lly",
            str(lly),
            "-urx",
            str(urx),
            "-ury",
            str(ury),
        ]
        if l2_text:
            cmd += ["--l2-text", f"$'{l2_text}'"]

    if render_mode == "GRAPHIC_AND_DESCRIPTION":
        cmd += [
            "--visible-signature",
            "--render-mode",
            render_mode,
            "-pg",
            str(page_no),
            "-llx",
            str(llx),
            "-lly",
            str(lly),
            "-urx",
            str(urx),
            "-ury",
            str(ury),
            "--bg-path",
            str(bg_file_path),
        ]
        if l2_text:
            cmd += ["--l2-text", f"$'{l2_text}'"]

    cmd = '/bin/bash -c "' + " ".join(cmd) + '"'
    print(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    # stdout, stderr = await proc.communicate()
    await proc.wait()

    if proc.returncode == 0:
        if output_format == "file":
            return FileResponse(pdf_out_file_path)
        else:
            output_b64 = ""
            async with aiofiles.open(pdf_out_file_path, "rb") as f:
                output_b64 = base64.b64encode(await f.read())
            return Response(
                content=output_b64, status_code=200, media_type="text/plain"
            )
