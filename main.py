import json
import requests
import cv2
import time
from ast import literal_eval

img = cv2.imread("assets/images/1.jpg")
server_url = "http://4.240.46.255:1337/upload"
_, encoded_image = cv2.imencode('.jpg', img)
image_bytes = encoded_image.tobytes()
files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
# text = {"query": "Is there accident in the image? Return in form of a json, if accident is true or false and description"}
# text = {"query": "Is there accident in the image? Return TRUE if accident occurred otherwise return FALSE"}
text = {"query": "I am providing business cards, What I want is to get json output of some keys like name, Company name, Mob. Number, e-mail id, address,. I want it all to be in a json output in a structured manner"}
response = requests.post(server_url, files=files, data=text, timeout=30).json()
# print(response.status_code, response.text)
st = time.perf_counter()
print("RES", response)
op = time.perf_counter() - st
print(op)
# val = literal_eval(response.strip())
print(response.strip())