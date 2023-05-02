from PIL import Image
from io import BytesIO
import requests
import os

from tqdm import tqdm
from fastapi_project.libs import s3_main_lib


def get_image_from_url(url):
    response = requests.get(url)
    img_bytes = BytesIO(response.content)
    img = Image.open(img_bytes)
    temp_file = "../temp.jpg"
    if img.mode in ("RGBA", "P"):
        img = thumbnail.convert("RGB")
    img.save(temp_file)


def resize_image(file_path, max_size, quality=80):
    with Image.open(file_path) as img:
        img_bytes = BytesIO()
        img.save(img_bytes, format=img.format)
        img_byte_size = img_bytes.tell()

        if img_byte_size <= max_size:
            return img

        while img_byte_size > max_size:         
            quality -= 5
            if quality < 5:
                return None
            
            temp_file = "../temp.jpg"
            img.save(temp_file, optimize=True, quality=quality)
            img_byte_size = os.path.getsize(temp_file)
            print(img_byte_size, img.size)

        return img


if __name__ == "__main__":
    s3_url_list = list(filter(lambda x: "hashed_name_image" in x, s3_main_lib.get_obj_url_list()))
    pbar = tqdm(s3_url_list[3005:])
    for s3_url in pbar:
        name = s3_url.split("https://jjmeme-bucket-2.s3.amazonaws.com/hashed_name_image/")[1]
        print(s3_url, name)
        get_image_from_url(s3_url)
        resize_image("../temp.jpg", 480000)

        thumbnail = Image.open("../temp.jpg")
        img_byte_arr = BytesIO()
        thumbnail.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        s3_main_lib.upload_image(img_bytes, name, "thumbnail")

    # resize_image("./test2.jpg", 480000)
    # get_image_from_url("https://jjmeme-bucket-2.s3.amazonaws.com/hashed_name_image/00097ce7ae25caa128cb7bd1c24708143b643f0608bc51c851cc8a527022701e.jpg")
