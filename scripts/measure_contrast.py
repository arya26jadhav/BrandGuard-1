from collections import Counter

from PIL import Image

from backend.services.image_validator import contrast_ratio

IMAGE_PATH = "test_data/images/low_contrast_ad.png"

img = Image.open(IMAGE_PATH).convert("RGB")
counts = Counter(img.getdata())

print("Most common colours:")
for colour, n in counts.most_common(8):
    print("  #%02X%02X%02X  x%d" % (*colour, n))

# Background: the most common colour overall (should be near-white)
background = counts.most_common(1)[0][0]

# Text: the most common colour that is clearly darker than the background.
# Anti-aliased edge pixels are rare, so the most common dark colour is the fill.
dark = [(c, n) for c, n in counts.most_common() if sum(c) < sum(background) - 60]
text = dark[0][0]

ratio = contrast_ratio(text, background)
print("\nBackground: #%02X%02X%02X" % background)
print("Text:       #%02X%02X%02X" % text)
print("Contrast:   %.2f:1" % ratio)
print("WCAG AA (4.5:1):", "PASS" if ratio >= 4.5 else "FAIL")