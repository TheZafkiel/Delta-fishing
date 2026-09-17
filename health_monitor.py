"""Read full/non-full HP from the HUD, with unknown state and episode debounce."""
from pathlib import Path
from statistics import median
from PIL import Image,ImageChops

ROOT=Path(__file__).resolve().parent


def health_mask(im):
    _,s,v=im.convert('RGB').convert('HSV').split()
    histogram=v.crop((0,0,125,34)).histogram()
    total=0;target=sum(histogram)*.98;level=255
    for level,count in enumerate(histogram):
        total+=count
        if total>=target:break
    threshold=max(45,level*.70)
    return ImageChops.multiply(s.point(lambda x:255 if x<85 else 0),v.point(lambda x:255 if x>threshold else 0))


class HealthReader:
    def __init__(self):
        self.labels=[]
        for path in (ROOT/'assets').glob('health_max100*.png'):
            with Image.open(path) as im:
                label=im.convert('L').copy()
                self.labels.append((label,label.histogram()[255]))
        if not self.labels:raise ValueError("缺少血量识别模板")
        self.last_score=0
        self.fill_fraction=None

    def read(self, image):
        im=image.resize((340,52),Image.Resampling.LANCZOS).convert('RGB')
        mask=health_mask(im)
        # Require the /100 suffix before interpreting an empty/dark bar.
        best=0
        for label,label_count in self.labels:
            for x in range(8,68):
                for y in range(7,16):
                    patch=mask.crop((x,y,x+label.width,y+label.height))
                    pixels=patch.histogram()[255]
                    overlap=ImageChops.multiply(patch,label).histogram()[255]
                    best=max(best,2*overlap/max(1,label_count+pixels))
        self.last_score=best
        self.fill_fraction=None
        if best<.72:return None
        # Read several rows through the middle, avoiding border and aliasing.
        gray=im.convert('L');rgb=im.load()
        columns=[]
        for x in range(6,334):
            values=[gray.getpixel((x,y)) for y in range(38,44)]
            neutral=sum(max(rgb[x,y])-min(rgb[x,y])<35 for y in range(38,44))>=4
            columns.append(median(values) if neutral else 0)
        reference=max(80, sorted(columns)[int(len(columns)*.85)]*.65)
        filled=[v>=reference for v in columns]
        # A health bar fills from left to right; reject irregular background patterns.
        end=max((i for i,v in enumerate(filled) if v),default=-1)+1
        if end and sum(filled[:end])/end<.97:return None
        self.fill_fraction=end/len(filled)
        return 'full' if end>=len(filled)-1 else 'low'


class HealthAlert:
    def __init__(self, confirm_frames=2):
        self.confirm_frames=confirm_frames
        self.candidate=None
        self.count=0
        self.alerted=False
        self.pending_x=False
        self.episode=0

    def update(self, state):
        if state is None:
            self.candidate=None;self.count=0
            return False
        self.count=self.count+1 if state==self.candidate else 1
        self.candidate=state
        if self.count<self.confirm_frames:return False
        if state=='full':
            self.alerted=False;self.pending_x=False
            return False
        if not self.alerted:
            self.alerted=True;self.pending_x=True;self.episode+=1
            return True
        return False
