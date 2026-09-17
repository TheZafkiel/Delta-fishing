"""Small fixed-font countdown reader using local digit templates."""
from pathlib import Path
from PIL import Image,ImageChops,ImageOps

ROOT=Path(__file__).resolve().parent
SIZE=(80,33)
SLOTS=((7,0,22,33),(22,0,37,33),(40,0,55,33),(55,0,70,33))


def timer_mask(image):
    image=image.resize(SIZE,Image.Resampling.LANCZOS).convert('RGB')
    r,g,b=image.split();_,sat,val=image.convert('HSV').split()
    red=ImageChops.multiply(ImageChops.subtract(r,g).point(lambda n:255 if n>60 else 0),
                            ImageChops.subtract(r,b).point(lambda n:255 if n>42 else 0))
    white=ImageChops.multiply(sat.point(lambda n:255 if n<50 else 0),val.point(lambda n:255 if n>205 else 0))
    return red if red.histogram()[255]>70 else white


def normalize(glyph):
    # Reject insignificant noise, preserve digit aspect ratio.
    box=glyph.getbbox()
    if not box or box[3]-box[1]<9 or glyph.histogram()[255]<14:return None
    im=glyph.crop(box);im.thumbnail((18,26),Image.Resampling.NEAREST)
    out=Image.new('L',(22,30));out.paste(im,((22-im.width)//2,(30-im.height)//2))
    return out


def sample_normalize(glyph):
    box=glyph.getbbox()
    if box is None:return None
    glyph=glyph.crop(box)
    if glyph.height<9 or glyph.width<3:return None
    width=round(glyph.width*26/glyph.height)
    if not 5<=width<=22:return None
    glyph=glyph.resize((width,26),Image.Resampling.NEAREST)
    out=Image.new('L',(26,30));out.paste(glyph,((26-width)//2,2))
    return out


def segmented_glyphs(image):
    """Find four digits and a two-dot colon independently of crop padding."""
    rgb=image.convert('RGB');r,g,b=rgb.split()
    _,sat,val=rgb.convert('HSV').split()
    histogram=val.histogram();target=sum(histogram)*.98;total=0
    for level,n in enumerate(histogram):
        total+=n
        if total>=target:break
    red=ImageChops.multiply(ImageChops.subtract(r,g).point(lambda n:255 if n>60 else 0),
                            ImageChops.subtract(r,b).point(lambda n:255 if n>42 else 0))
    masks=[red] if red.histogram()[255]>70 else [
        ImageChops.multiply(sat.point(lambda n:255 if n<50 else 0),val.point(lambda n:255 if n>threshold else 0))
        for threshold in (205,max(75,round(level*.86)),max(75,round(level*.75)))]
    for mask in masks:
        spans=[];start=None
        for x in range(mask.width+1):
            on=x<mask.width and mask.crop((x,0,x+1,mask.height)).getbbox()
            if on and start is None:start=x
            if not on and start is not None:
                spans.append((start,x));start=None
        if len(spans)!=5:continue
        glyphs=[mask.crop((a,0,b,mask.height)) for a,b in spans]
        boxes=[g.getbbox() for g in glyphs]
        digits=[glyphs[i] for i in (0,1,3,4)]
        heights=[boxes[i][3]-boxes[i][1] for i in (0,1,3,4)]
        if min(heights)<9 or min(heights)<max(heights)*.8:continue
        if spans[2][1]-spans[2][0]>min(g.width for g in digits)*.45:continue
        colon=glyphs[2];runs=0;previous=False
        for y in range(colon.height):
            on=colon.crop((0,y,colon.width,y+1)).getbbox() is not None
            if on and not previous:runs+=1
            previous=on
        if runs!=2:continue
        digit_boxes=[boxes[i] for i in (0,1,3,4)]
        tops=[box[1] for box in digit_boxes];bottoms=[box[3] for box in digit_boxes]
        if max(tops)-min(tops)>max(2,max(heights)*.15) or max(bottoms)-min(bottoms)>max(2,max(heights)*.15):continue
        if not (min(tops)<=boxes[2][1]<boxes[2][3]<=max(bottoms)):continue
        normalized=[sample_normalize(g) for g in digits]
        if all(g is not None for g in normalized):yield normalized


class TimerReader:
    def __init__(self):
        self.templates=[]
        for p in (ROOT/'assets'/'timer').glob('*.png'):
            with Image.open(p) as im:self.templates.append((int(p.name[0]),im.convert('L').copy()))
        if {n for n,_ in self.templates} != set(range(10)):raise ValueError('缺少倒计时数字模板')
        self.sample_templates=[]
        for p in (ROOT/'assets'/'timer_samples').glob('*.png'):
            with Image.open(p) as im:self.sample_templates.append((int(p.name[0]),im.convert('L').copy()))
        self.last_scores=[]

    def read(self,image,expected_seconds=None):
        values={}
        for glyphs in segmented_glyphs(image):
            digits=[];scores=[]
            for glyph in glyphs:
                best={}
                for n,template in self.sample_templates:
                    overlap=ImageChops.multiply(glyph,template).histogram()[255]
                    score=2*overlap/max(1,glyph.histogram()[255]+template.histogram()[255])
                    best[n]=max(score,best.get(n,0))
                rank=sorted(best.items(),key=lambda item:item[1],reverse=True)
                if len(rank)<2 or rank[0][1]<.78 or rank[0][1]-rank[1][1]<.045:break
                digits.append(rank[0][0]);scores.append(rank[0][1])
            if len(digits)!=4:continue
            minutes=digits[0]*10+digits[1];seconds=digits[2]*10+digits[3]
            if minutes<60 and seconds<60:values[minutes*60+seconds]=scores
        if len(values)>1:return None
        if values:
            value,self.last_scores=next(iter(values.items()))
            return value
        return self._read_legacy(image,expected_seconds)

    def _read_legacy(self,image,expected_seconds=None):
        mask=timer_mask(image);digits=[];ranks=[];self.last_scores=[]
        for slot in SLOTS:
            glyph=normalize(mask.crop(slot))
            if glyph is None:return None
            best={}
            for n,template in self.templates:
                overlap=ImageChops.multiply(glyph,template).histogram()[255]
                score=2*overlap/max(1,glyph.histogram()[255]+template.histogram()[255])
                best[n]=max(score,best.get(n,0))
            rank=sorted(best.items(),key=lambda x:x[1],reverse=True)
            self.last_scores.append(round(rank[0][1],3))
            if rank[0][1]<.60:return None
            ranks.append(rank)
            digits.append(rank[0][0])
        if any(rank[0][1]-rank[1][1]<.03 for rank in ranks):
            if expected_seconds is None:return None
            from itertools import product
            choices=[]
            for rank in ranks:
                choices.append([n for n,score in rank[:2] if score>=.60 and rank[0][1]-score<.05])
            candidates=[]
            for ds in product(*choices):
                minutes=ds[0]*10+ds[1];seconds=ds[2]*10+ds[3]
                value=minutes*60+seconds
                if minutes<60 and seconds<60 and abs(value-expected_seconds)<=2:
                    candidates.append((abs(value-expected_seconds),value))
            candidates.sort()
            if not candidates or (len(candidates)>1 and candidates[1][0]-candidates[0][0]<.75):return None
            return candidates[0][1]
        minutes=digits[0]*10+digits[1];seconds=digits[2]*10+digits[3]
        if seconds>=60 or minutes>59:return None
        return minutes*60+seconds
