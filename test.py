from captcha.image import ImageCaptcha
import random

image = ImageCaptcha()
data = image.generate("1234")
image.write(str(random.randint(1000, 9999)), "./out.png")

# import time

# localtime = time.localtime(time.time())
# print(localtime.tm_year)
