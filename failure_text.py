"""Classify supplied toasts locally, including the non-actionable backpack notice."""
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
CANONICAL_SIZE = (240, 120)
TEXT_BOX = (68, 34, 174, 67)


def text_mask(image):
    gray = ImageOps.grayscale(image)
    contrast = ImageChops.subtract(gray, gray.filter(ImageFilter.GaussianBlur(2)), 1, 128)
    # Local contrast tolerates dark/light backgrounds better than absolute white.
    mask = contrast.point(lambda v: 255 if v >= 139 else 0)
    saturation = image.convert('RGB').convert('HSV').getchannel('S')
    return ImageChops.multiply(mask, saturation.point(lambda v: 255 if v <= 100 else 0))


class FailureTextDetector:
    def __init__(self):
        self.templates = []
        for name, label in [('early', '提竿过早'), ('escaped', '鱼已逃离'), ('backpack', '背包已满')]:
            with Image.open(ROOT/'assets'/f'failure_{name}.png') as im:
                mask = im.convert('L').copy()
            self.templates.append((label, mask, mask.filter(ImageFilter.MaxFilter(3)), mask.histogram()[255]))
        self.last_score = 0.0

    def detect(self, image):
        image = image.resize(CANONICAL_SIZE, Image.Resampling.LANCZOS)
        mask = text_mask(image)
        scores = {}
        x1,y1,x2,y2 = TEXT_BOX
        for dy in range(-6, 7, 2):
            for dx in range(-10, 11, 2):
                patch = mask.crop((x1+dx,y1+dy,x2+dx,y2+dy))
                pixels = patch.histogram()[255]
                if pixels < 80:
                    continue
                expanded = patch.filter(ImageFilter.MaxFilter(3))
                for text, template, wide, total in self.templates:
                    recall = ImageChops.multiply(expanded, template).histogram()[255] / total
                    precision = ImageChops.multiply(patch, wide).histogram()[255] / pixels
                    exact = 2*ImageChops.multiply(patch, template).histogram()[255]/max(1, total+pixels)
                    score = 0.5*min(recall, precision)+0.5*exact
                    scores[text] = max(score, scores.get(text, 0))
        rank = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        self.last_scores = scores
        self.last_score = rank[0][1] if rank else 0.0
        if len(rank)<2 or rank[0][1]<0.70 or rank[0][1]-rank[1][1]<0.045:
            return None
        return rank[0][0]
