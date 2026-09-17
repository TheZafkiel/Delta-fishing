"""Track the striped colored float, then detect its complete disappearance."""
from PIL import Image, ImageChops


class FloatDetector:
    def __init__(self, c):
        self.c=c
        self.lock_x=None
        self.lock_hits=0
        self.missing=0
        self.ready=False
        self.mask=None
        self.baseline=0
        self.total_pixels=0
        self.required_pixels=0
        self.threshold=0
        self.reason='寻找红绿漂尾'
        self.frame_size=None

    def update(self, frame):
        frame=frame.convert('RGB')
        if self.frame_size != frame.size:
            self.__init__(self.c)
            self.frame_size=frame.size
        hue,sat,val=frame.convert('HSV').split()
        colorful=ImageChops.multiply(sat.point(lambda n:255 if n>=self.c['float_saturation'] else 0),
                                    val.point(lambda n:255 if n>=self.c['float_value'] else 0))
        red=ImageChops.multiply(colorful,hue.point(lambda n:255 if n<=10 or n>=240 else 0))
        green=ImageChops.multiply(colorful,hue.point(lambda n:255 if 42<=n<=112 else 0))
        self.mask=ImageChops.lighter(red,green)
        w,h=frame.size
        # Ignore the very bottom where colored reflections tend to occur.
        height=round(h*self.c['float_upper_fraction'])
        candidates=[]
        radius=max(2,round(w/120))
        start=max(radius,round(w*.25));end=min(w-radius,round(w*.75))
        if self.ready and self.lock_x is not None:
            start=max(start,round(self.lock_x-w*.12));end=min(end,round(self.lock_x+w*.12))
        for x in range(start,end,2):
            box=(x-radius,0,x+radius+1,height)
            r=red.crop(box);g=green.crop(box)
            rc=r.histogram()[255];gc=g.histogram()[255]
            bounds=ImageChops.lighter(r,g).getbbox()
            span=bounds[3]-bounds[1] if bounds else 0
            if rc>=self.c['float_red_pixels'] and gc>=self.c['float_green_pixels'] and rc+gc>=max(self.c['float_min_pixels'], 120 if not self.ready else self.c['float_min_pixels']) and span>=self.c['float_min_height']:
                score=min(rc,gc)*2+rc+gc
                if self.ready and self.lock_x is not None:score-=abs(x-self.lock_x)*5
                candidates.append((score,x,rc+gc))
        if candidates:
            _,x,count=max(candidates)
            if self.lock_x is None or abs(x-self.lock_x)<=w*.03:
                self.lock_hits+=1
            else:self.lock_hits=1
            self.lock_x=x
            self.missing=0
            self.baseline=count
            self.ready=self.ready or self.lock_hits>=self.c['float_lock_frames']
            self.reason='漂尾可见，等待全部入水' if self.ready else '正在确认漂尾'
            self.total_pixels=count
            return False,count
        self.total_pixels=0
        if not self.ready:
            self.lock_hits=0
            self.lock_x=None
            self.reason='未锁定漂尾，不提竿；检查浮漂框'
            return False,0
        self.missing+=1
        self.reason=f'漂尾消失 {self.missing}/{self.c["float_missing_frames"]} 帧'
        return self.missing>=self.c['float_missing_frames'],0
