from typing import Literal
from fastapi import UploadFile, File, Form
from pydantic import BaseModel, validator


class Request(BaseModel):
    user_id: str
    typeReq: str = "swap"
    template_id: int = 1
    faceFrom: list
    faceTo: list


class Status(BaseModel):
    status: Literal["OK", "ERROR"] = "ERROR"


class TemplateUpload(BaseModel):
    thumb: UploadFile
    file: UploadFile
    preview_source: UploadFile
    premium: str
    categories: str

    @validator("thumb")
    def validate_thumb_format(cls, thumb: UploadFile):
        formats = ["jpeg", "png", "jpg", "mp4"]
        if thumb.filename.split(".")[-1] not in formats:
            raise ValueError(f"Your file must have one of such formats: {formats}")

        return thumb
    
    @validator("preview_source")
    def validate_preview_format(cls, preview_source: UploadFile):
        formats = ["jpeg", "png", "jpg", "mp4"]
        if preview_source.filename.split(".")[-1] not in formats:
            raise ValueError(f"Your file must have one of such formats: {formats}")

        return preview_source

    @validator("file")
    def validate_video_format(cls, file: UploadFile):
        formats = ["mp4", "jpg", "png", "jpeg"]

        if file.filename.split(".")[-1] not in formats:
            raise ValueError(f"Your file must have one of such formats: {formats}")
        return file

    @classmethod
    def as_form(cls,
                thumb: UploadFile = File(...),
                file: UploadFile = File(...),
                preview_source: UploadFile = File(...),
                premium: str = Form(...),
                categories: str = Form(...)):
        return cls(thumb=thumb,
                   file=file,
                   preview_source=preview_source,
                   premium=premium,
                   categories=categories)
    

class DetectFaceUpload(BaseModel):
    image: dict

    @validator("image")
    def validate_image_format(cls, image:dict):
        base64_png = "iVBORw0KGg"
        basee64_jpg = "/9j/4"

        if not (image["image"].startswith(base64_png) or image["image"].startswith(basee64_jpg)):
            raise ValueError(f"Your file must have one of such formats: {'.png', '.jpg'}")

        return image

    @classmethod
    def as_form(cls, image: dict):
        return cls(image=image)

      
# class TemplateImageUpload(BaseModel):
#     image: UploadFile
#     premium: bool
#     category_id: int

#     @validator("image")
#     def validate_image_format(cls, image: UploadFile):
#         formats = ["jpeg", "png", "jpg", "gif", "webp", "apng"]
#         if image.filename.split(".")[-1] not in formats:
#             raise ValueError(f"Your file must have one of such formats: {formats}")

#         return image

#     @classmethod
#     def as_form(cls,
#                 image: UploadFile = File(...),
#                 premium: bool = Form(...),
#                 category_id: int = Form(...)):
#         return cls(image=image,
#                    premium=premium,
#                    category_id=category_id)


# class FaceSwapCustom(BaseModel):
#     custom: UploadFile
#     image_face: str
#     user_id: str
#     app: str = None

#     @validator("custom")
#     def validate_custom_format(cls, custom: UploadFile):
#         formats = ["jpeg", "png", "jpg", "gif", "webp", "apng", "mp4"]

#         if custom.filename.split(".")[-1] not in formats:
#             raise ValueError(f"Your file must have one of such formats: {formats}")
#         return custom

#     @classmethod
#     def as_form(cls,
#                 custom: UploadFile = File(...),
#                 image_face: str = Form(...),
#                 user_id: str = Form(...),
#                 app: str = Form(...), ):
#         return cls(custom=custom,
#                    image_face=image_face,
#                    user_id=user_id,
#                    app=app)


# class CategoryUpload(BaseModel):
#     title: str


# class CategoryUpdate(BaseModel):
#     id: int
#     title: str


# class TemplateUses(BaseModel):
#     template_id: int
#     uses: int


# class DateFiltration(BaseModel):
#     date_from: str
#     date_to: str

#     @validator("date_from")
#     def validate_date_from(cls, date_from: str):
#         date_pattern = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$')
#         parts = date_from.split('-')
#         date_from = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"

#         if not date_pattern.match(date_from):
#             raise ValueError(f"Your date must have such pattern: YYYY-MM-DD")
#         return date_from

#     @validator("date_to")
#     def validate_date_to(cls, date_to: str):
#         date_pattern = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$')
#         parts = date_to.split('-')
#         date_to = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
#         if not date_pattern.match(date_to):
#             raise ValueError(f"Your date must have such pattern: YYYY-MM-DD")
#         return date_to

#     @validator("date_to", "date_from")
#     def validate_date_range(cls, value, values):
#         date_from = values.get('date_from')
#         if date_from and datetime.strptime(value, '%Y-%m-%d') < datetime.strptime(date_from, '%Y-%m-%d'):
#             raise ValueError("Your date_to must be greater than or equal than date_from")
#         return value


# class TemplateUploadStatus(BaseModel):
#     status: Literal["OK", "ERROR"] = "ERROR"
#     request_id: str = None


# class DetectFaceStatus(BaseModel):
#     faces: int


# class FaceSwapImageRequest(BaseModel):
#     user_id: str
#     template_id: int = 1
#     image_face: str
#     app: str = None
