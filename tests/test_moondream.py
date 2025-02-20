import moondream as md
from PIL import Image

# Initialize with local model path. Can also read .mf.gz files, but we recommend decompressing
# up-front to avoid decompression overhead every time the model is initialized.
model = md.vl(model="/home/tests/vision_models/moondream-2b-int8.mf")

# Load and process image
print("ask")
image = Image.open("test_img.png")
encoded_image = model.encode_image(image)

# Generate caption
#caption = model.caption(encoded_image)["caption"]
#print("Caption:", caption)

# Ask questions

answer = model.query(encoded_image, "if this frame a good fit for a F1 video? answer with 'good' or 'bad'")["answer"]
print("Answer:", answer)