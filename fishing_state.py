"""Recognize pairs of right-hand action hints. Unknown never implies a bite."""
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter
from failure_text import text_mask

SIZE = (190, 230)
ROOT = Path(__file__).resolve().parent


def similarity(patch, template, wide, total):
    pixels = patch.histogram()[255]
    if pixels < total*.45 or pixels > total*2.5:
        return 0.0
    overlap = ImageChops.multiply(patch, template).histogram()[255]
    exact = 2*overlap/max(1,pixels+total)
    if exact < .40:
        return 0.0
    recall = ImageChops.multiply(patch.filter(ImageFilter.MaxFilter(3)), template).histogram()[255]/total
    precision = ImageChops.multiply(patch, wide).histogram()[255]/pixels
    return (exact+min(recall,precision))/2


class FishingStateReader:
    def __init__(self):
        self.groups = {}
        # The second line's relative position comes from the supplied screenshots.
        for state, specs in {'idle': [('idle_cast',32,0),('idle_bait',0,38)],
                             'fishing': [('fishing_exit',0,0),('fishing_strike',36,40)]}.items():
            items=[]
            for name,dx,dy in specs:
                with Image.open(ROOT/'assets'/('hud_'+name+'.png')) as im:
                    mask=im.convert('L').copy()
                items.append((dx,dy,mask,mask.filter(ImageFilter.MaxFilter(3)),mask.histogram()[255]))
            self.groups[state]=items
        self.last_scores={}

    def read(self, image):
        mask=text_mask(image.resize(SIZE,Image.Resampling.LANCZOS))
        scores={}
        for state,items in self.groups.items():
            best=0.0
            # Text is aligned near the right edge. Search vertical position because
            # idle and fishing menus start on different rows.
            for y in range(0,165,2):
                for x in range(40,80):
                    values=[]
                    for dx,dy,template,wide,total in items:
                        patch=mask.crop((x+dx,y+dy,x+dx+template.width,y+dy+template.height))
                        score=similarity(patch,template,wide,total)
                        values.append(score)
                        if score < .63:break
                    if len(values)==2:best=max(best,min(values))
            scores[state]=best
        self.last_scores=scores
        ranked=sorted(scores,key=scores.get,reverse=True)
        return ranked[0] if scores[ranked[0]]>=.67 and scores[ranked[0]]-scores[ranked[1]]>=.06 else None
