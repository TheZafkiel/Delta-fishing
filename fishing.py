"""台钓助手：基于画面识别和 Windows 输入的自动钓鱼工具。"""
import argparse
import ctypes
from ctypes import wintypes
import config_io
import json
from pathlib import Path
import time
from collections import deque
from statistics import median

BASE = Path(__file__).resolve().parent
DEFAULT = dict(region=[1120/2560, 580/1440, 360/2560, 280/1440],
               brightness=160, min_pixels=15, max_pixels=8000,
               confirm_frames=2, scan_interval=0.1, bite_timeout=25,
               cast_settle=2.0, zoom_settle=1.0, catch_wait=2.5, click_hold=0.1, max_cycles=0,
               first_click_wait=0.5, release_wait=0.2, final_click_wait=2.0,
               region_mode='screen', screen_region=[1120, 580, 360, 280],
               splash_value=100, splash_saturation=65, splash_min_fraction=0.02,
               splash_max_fraction=0.45, splash_growth=3.0, baseline_frames=6,
               splash_delta=12, splash_noise_factor=4.0,
               failure_region=[1160/2560, 840/1440, 240/2560, 120/1440],
               failure_retry_wait=3.0, failure_scan_interval=0.2)


DEFAULT.update({'detection_mode': 'float', 'float_region': [0.4375, 0.24305555555555555, 0.140625, 0.3819444444444444], 'float_saturation': 90, 'float_value': 40, 'float_upper_fraction': 0.85, 'float_red_pixels': 8, 'float_green_pixels': 4, 'float_min_pixels': 30, 'float_min_height': 30, 'float_lock_frames': 3, 'float_missing_frames': 2, 'timer_enabled': True, 'timer_alert_minutes': 7, 'timer_scan_interval': 1.0, 'timer_region': [0.0703125, 0.3138888888888889, 0.03125, 0.022916666666666665]})


DEFAULT.update({'health_enabled': True, 'health_region': [0.046875, 0.8944444444444445, 0.1328125, 0.03611111111111111], 'health_scan_interval': 0.5, 'health_confirm_frames': 2, 'health_x_hold': 2.0})


DEFAULT.update({'right_press_delay': 0.25, 'state_enabled': True, 'state_region': [2370/2560,840/1440,190/2560,230/1440], 'state_scan_interval': 0.5})

def config():
    c = DEFAULT.copy()
    p = BASE / 'config.py'
    example = BASE / 'config.example.py'
    if not p.exists() and example.exists():
        config_io.save(p, config_io.loads(example.read_text(encoding='utf-8-sig')))
    if p.exists():
        c.update(config_io.loads(p.read_text(encoding='utf-8-sig')))
    x,y,w,h = c['region']
    if not (0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x+w <= 1.00001 and y+h <= 1.00001):
        raise ValueError('region 比例必须在窗口内')
    for k in ('scan_interval','bite_timeout','click_hold','cast_settle','zoom_settle','catch_wait','first_click_wait','release_wait','final_click_wait'):
        if not 0 < c[k] <= 300:
            raise ValueError(k + ' 必须大于 0 且不超过 300 秒')
    for k in ('confirm_frames','min_pixels','max_pixels','brightness'):
        if type(c[k]) is not int or c[k] <= 0:
            raise ValueError(k + ' 必须为正整数')
    if c['brightness'] > 255 or c['max_pixels'] < c['min_pixels']:
        raise ValueError('像素阈值错误')
    if type(c['max_cycles']) is not int or c['max_cycles'] < 0:
        raise ValueError('max_cycles 必须为非负整数，0 表示持续循环')
    if c['region_mode'] not in ('screen', 'relative'):
        raise ValueError('region_mode 必须为 screen 或 relative')
    sx,sy,sw,sh = c['screen_region']
    if not all(type(v) is int for v in (sx,sy,sw,sh)) or sw <= 0 or sh <= 0:
        raise ValueError('screen_region 必须是整数坐标和正数宽高')
    for key in ('splash_value', 'splash_saturation'):
        if type(c[key]) is not int or not 0 <= c[key] <= 255:
            raise ValueError(key + ' 必须为 0 到 255 的整数')
    if not 0 < c['splash_min_fraction'] < c['splash_max_fraction'] <= 1:
        raise ValueError('水花面积比例设置错误')
    if not 1 < c['splash_growth'] <= 100:
        raise ValueError('splash_growth 必须大于 1 且不超过 100')
    if type(c['baseline_frames']) is not int or not 2 <= c['baseline_frames'] <= 60:
        raise ValueError('baseline_frames 必须为 2 到 60 的整数')
    if not 1 <= c['splash_delta'] <= 255 or not 1 <= c['splash_noise_factor'] <= 20:
        raise ValueError('水花增亮阈值或噪声倍率不正确')
    fx,fy,fw,fh = c['failure_region']
    if not (0 <= fx < 1 and 0 <= fy < 1 and fw > 0 and fh > 0 and fx+fw <= 1 and fy+fh <= 1):
        raise ValueError('failure_region 必须在游戏客户区内')
    for key in ('failure_retry_wait', 'failure_scan_interval'):
        if not 0 < c[key] <= 300:
            raise ValueError(key + ' 必须大于 0 且不超过 300')
    if c['detection_mode'] not in ('float','splash'):
        raise ValueError('detection_mode 必须是 float 或 splash')
    for key in ('float_region','timer_region','state_region'):
        x,y,w,h=c[key]
        if not (0<=x<1 and 0<=y<1 and w>0 and h>0 and x+w<=1 and y+h<=1):
            raise ValueError(key+' 必须在游戏客户区内')
    for key in ('float_red_pixels','float_green_pixels','float_min_pixels','float_min_height','float_lock_frames','float_missing_frames'):
        if type(c[key]) is not int or c[key]<1:raise ValueError(key+' 必须为正整数')
    for key in ('float_saturation','float_value'):
        if type(c[key]) is not int or not 0<=c[key]<=255:raise ValueError(key+' 必须为 0~255 整数')
    if not 0<c['float_upper_fraction']<=1:raise ValueError('float_upper_fraction 必须在 0~1 内')
    if type(c['timer_enabled']) is not bool:raise ValueError('timer_enabled 必须是 True 或 False')
    if not 0<c['timer_alert_minutes']<60 or not 0<c['timer_scan_interval']<=60:
        raise ValueError('倒计时阈值或检测间隔不正确')
    hx,hy,hw,hh=c['health_region']
    if not (0<=hx<1 and 0<=hy<1 and hw>0 and hh>0 and hx+hw<=1 and hy+hh<=1):
        raise ValueError('health_region 必须在游戏客户区内')
    if type(c['health_enabled']) is not bool:raise ValueError('health_enabled 必须是 True 或 False')
    if type(c['health_confirm_frames']) is not int or c['health_confirm_frames']<1:
        raise ValueError('health_confirm_frames 必须为正整数')
    if not 0<c['health_scan_interval']<=60 or not 0<c['health_x_hold']<=30:
        raise ValueError('血量检测间隔或 X 按住时间不正确')
    if type(c['state_enabled']) is not bool:raise ValueError('state_enabled 必须为 True 或 False')
    if not 0<=c['right_press_delay']<=30 or not 0<c['state_scan_interval']<=10:
        raise ValueError('右键延迟或状态识别间隔不正确')
    return c


def largest_blob(mask):
 w,h=mask.size;data=bytearray(mask.tobytes());best=0;best_box=None
 for start,value in enumerate(data):
  if not value:continue
  data[start]=0;todo=[start];count=0;x0=x1=start%w;y0=y1=start//w
  while todo:
   pos=todo.pop();y,x=divmod(pos,w);count+=1;x0=min(x0,x);x1=max(x1,x);y0=min(y0,y);y1=max(y1,y)
   for ny in range(max(0,y-1),min(h,y+2)):
    for nx in range(max(0,x-1),min(w,x+2)):
     j=ny*w+nx
     if data[j]:data[j]=0;todo.append(j)
  if count>best:best=count;best_box=(x0,y0,x1+1,y1+1)
 return best,best_box


class SplashDetector:
    """Local brightening against an adaptive background, not absolute water color."""
    def __init__(self, c):
        self.c = c
        self.history = deque(maxlen=max(20, c['baseline_frames']))
        self.baseline = 0
        self.ready = False
        self.mask = None
        self.background = None
        self.background_saturation = None
        self.frames = 0
        self.threshold = 0
        self.total_pixels = 0
        self.required_pixels = 0
        self.reason = "采集背景"

    @staticmethod
    def percentile(hist, fraction):
        target = sum(hist)*fraction
        total = 0
        for value, count in enumerate(hist):
            total += count
            if total >= target:
                return value
        return 255

    def update(self, frame):
        from PIL import Image, ImageChops, ImageFilter, ImageOps
        gray = ImageOps.grayscale(frame)
        saturation = frame.convert("RGB").convert("HSV").getchannel("S")
        if self.background is None or self.background.size != gray.size:
            self.background = gray.copy()
            self.background_saturation = saturation.copy()
            self.frames = 0
            self.history.clear()
        # Offset 128 retains signed changes. Subtract median exposure shift,
        # so a uniform scene brightening/dimming is not a bite.
        delta = ImageChops.subtract(gray, self.background, 1, 128)
        histogram = delta.histogram()
        center = self.percentile(histogram, 0.5)
        deviations = [0]*256
        for value, count in enumerate(histogram):
            deviations[abs(value-center)] += count
        noise = self.percentile(deviations, 0.5)
        self.threshold = max(self.c['splash_delta'], noise*self.c['splash_noise_factor'])
        mask = delta.point(lambda x: 255 if x-center >= self.threshold else 0)
        # Accept neutral foam OR foam less saturated than its local water.
        # This excludes colorful float reflections without fixing water color.
        neutral = saturation.point(lambda x: 255 if x <= 100 else 0)
        less_color = ImageChops.subtract(self.background_saturation, saturation).point(lambda x: 255 if x >= 20 else 0)
        mask = ImageChops.multiply(mask, ImageChops.lighter(neutral, less_color))
        mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
        self.mask = mask
        self.total_pixels = mask.histogram()[255]
        count, box = largest_blob(mask)
        self.ready = self.frames >= self.c['baseline_frames']
        self.baseline = median(self.history) if self.history else count
        if not self.ready:
            self.frames += 1
            self.history.append(count)
            self.background = Image.blend(self.background, gray, 1/self.frames)
            self.background_saturation = Image.blend(self.background_saturation, saturation, 1/self.frames)
            return False, count
        area = frame.width * frame.height
        broad = box is not None and box[2]-box[0] >= max(12, frame.width*0.08)
        hit = (broad and self.c['splash_min_fraction']*area <= count
               <= self.c['splash_max_fraction']*area
               and count >= max(1, self.baseline)*self.c['splash_growth'])
        self.required_pixels = max(self.c['splash_min_fraction']*area,
                                   max(1, self.baseline)*self.c['splash_growth'])
        self.reason = ('候选水花' if hit else '水花面积不足' if count < self.required_pixels
                       else '区域变化过大' if count > self.c['splash_max_fraction']*area
                       else '形状过细')
        if not hit:
            self.history.append(count)
            self.background = Image.blend(self.background, gray, 0.15)
            self.background_saturation = Image.blend(self.background_saturation, saturation, 0.15)
        return bool(hit), count


class Paused(Exception):
    pass


class FishingTimeout(Exception):
    pass


class FishingNotCast(Exception):
    pass


class FishingFailed(Exception):
    pass


class Windows:
    def __init__(self):
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        try:
            self.u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            self.u.SetProcessDPIAware()
        self.u.GetForegroundWindow.restype = wintypes.HWND
        self.u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.u.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.u.IsWindow.argtypes = [wintypes.HWND]
        self.u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.last = {}
        self.handle = None
        self.pid = None

    def key(self, code):
        down = bool(self.u.GetAsyncKeyState(code) & 0x8000)
        old = self.last.get(code, False)
        self.last[code] = down
        return down and not old

    def process(self, handle):
        pid = wintypes.DWORD()
        self.u.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        return pid.value

    def bind(self):
        handle = self.u.GetForegroundWindow()
        title = ctypes.create_unicode_buffer(1024)
        self.u.GetWindowTextW(handle, title, len(title))
        if not any(n in title.value.lower() for n in ('三角洲','delta force','deltaforce')):
            print('绑定失败：请切到三角洲游戏再按 F6。当前：', title.value)
            return
        self.handle, self.pid = handle, self.process(handle)
        print('已绑定：', title.value)

    def focused(self):
        return (self.handle and self.u.IsWindow(self.handle)
                and self.u.GetForegroundWindow() == self.handle
                and self.process(self.handle) == self.pid)

    def bounds(self):
        r, p = wintypes.RECT(), wintypes.POINT()
        if not self.u.GetClientRect(self.handle, ctypes.byref(r)) or not self.u.ClientToScreen(self.handle, ctypes.byref(p)):
            raise Paused('无法读取游戏窗口')
        if r.right < 100 or r.bottom < 100:
            raise Paused('游戏窗口过小或最小化')
        return p.x, p.y, r.right, r.bottom

    def button(self, down, name='left'):
        flags = (2 if down else 4) if name == 'left' else (8 if down else 16)
        self.u.mouse_event(flags, 0, 0, 0, 0)

    def set_key(self, vk, down):
        self.u.keybd_event(vk, 0, 0 if down else 2, 0)

    def calibrate(self, c):
        import tkinter as tk
        x,y,w,h = self.bounds()
        root = tk.Tk()
        root.overrideredirect(True)
        root.geometry(f'{w}x{h}{x:+d}{y:+d}')
        root.attributes('-topmost', True)
        root.attributes('-alpha', 0.4)
        canvas = tk.Canvas(root, bg='black', cursor='cross', highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        canvas.create_text(20,20,anchor='nw',fill='white',font=('Microsoft YaHei',16),
                           text=('框选完整红绿漂尾及上下活动范围，少包含下方倒影。Esc 取消，F9 退出。' if c['detection_mode']=='float' else '框选水花区域。Esc 取消，F9 退出。'))
        start, box = [], []
        def begin(e):
            start[:] = [e.x,e.y]
            if box:
                canvas.delete(box.pop())
            box.append(canvas.create_rectangle(e.x,e.y,e.x,e.y,outline='red',width=3))
        def drag(e):
            if start:
                canvas.coords(box[0],*start,e.x,e.y)
        def finish(e):
            if not start:
                return
            x1,x2 = sorted((max(0,min(w,start[0])),max(0,min(w,e.x))))
            y1,y2 = sorted((max(0,min(h,start[1])),max(0,min(h,e.y))))
            if x2-x1 < 8 or y2-y1 < 8:
                return
            if c['detection_mode']=='float':
                c['float_region']=[x1/w,y1/h,(x2-x1)/w,(y2-y1)/h]
            else:
                c['region'] = [x1/w,y1/h,(x2-x1)/w,(y2-y1)/h]
                c['region_mode'] = 'relative'
            config_io.save(BASE/'config.py', c)
            root.destroy()
            print('区域已保存。切回游戏，F8 开始。')
        quit_requested = []
        def quit_all(e):
            quit_requested.append(True)
            root.destroy()
        canvas.bind('<ButtonPress-1>',begin)
        canvas.bind('<B1-Motion>',drag)
        canvas.bind('<ButtonRelease-1>',finish)
        root.bind('<Escape>',lambda e: root.destroy())
        root.bind('<F9>',quit_all)
        root.after(100,root.focus_force)
        root.mainloop()
        if quit_requested:
            raise KeyboardInterrupt


class Runner:
    def __init__(self, win, c, live=False):
        self.win, self.c, self.live = win,c,live
        self.held = set()
        self.held_keys = set()
        self.state_reader = None
        self.state_next_scan = 0
        self.state_idle_hits = 0
        self.health_reader = None
        self.health_alert = None
        self.health_next_scan = 0
        self.health_next_notice = 0
        self.detector = self.make_detector()
        self.timer_reader = None
        self.timer_alert = None
        self.timer_next_scan = 0
        self.timer_next_notice = 0
        self.debug_next = 0
        self.debug_best = -1
        self.failure_detector = None
        self.monitor_failures = False
        self.failure_next_scan = 0
        self.failure_candidate = None
        self.failure_hits = 0
        self.failure_latched = False
        self.failure_clear_frames = 0

    def make_detector(self):
        if self.c['detection_mode']=='float':
            from float_detector import FloatDetector
            return FloatDetector(self.c)
        return SplashDetector(self.c)

    def poll_timer(self):
        if not self.c['timer_enabled'] or self.timer_reader is None:return
        now=time.monotonic()
        if now<self.timer_next_scan:return
        self.timer_next_scan=now+self.c['timer_scan_interval']
        from PIL import ImageGrab
        x,y,w,h=self.win.bounds();rx,ry,rw,rh=self.c['timer_region']
        frame=ImageGrab.grab(bbox=(x+round(rx*w),y+round(ry*h),x+round((rx+rw)*w),y+round((ry+rh)*h)),all_screens=True)
        self.check(monitor=False)
        seconds=self.timer_reader.read(frame,expected_seconds=self.timer_alert.expected(now))
        alert=self.timer_alert.update(seconds,now)
        if now>=self.timer_next_notice:
            folder=BASE/'work'/'detection_debug';folder.mkdir(parents=True,exist_ok=True)
            frame.save(folder/'timer.png')
            value=(f'{seconds//60:02d}:{seconds%60:02d}' if seconds is not None else '未确认数字')
            accepted=self.timer_alert.confirmed_at==now
            print('[时间] '+value+('（已通过倒计时校验）' if accepted else '（未通过校验，本次不提醒）'))
            self.timer_next_notice=now+10
        if alert:
            from countdown_alert import play_warning
            print(f"[提醒] 对局剩余时间已到 {self.c['timer_alert_minutes']:g} 分钟以内")
            try:play_warning()
            except RuntimeError as exc:print('提示音播放失败：',exc)

    def poll_health(self):
        if not self.c['health_enabled'] or self.health_reader is None:return
        now=time.monotonic()
        if now<self.health_next_scan:return
        self.health_next_scan=now+self.c['health_scan_interval']
        from PIL import ImageGrab
        x,y,w,h=self.win.bounds();rx,ry,rw,rh=self.c['health_region']
        frame=ImageGrab.grab(bbox=(x+round(rx*w),y+round(ry*h),x+round((rx+rw)*w),y+round((ry+rh)*h)),all_screens=True)
        self.check(monitor=False)
        state=self.health_reader.read(frame)
        self.check(monitor=False)
        alert=self.health_alert.update(state)
        if now>=self.health_next_notice or alert:
            folder=BASE/'work'/'detection_debug';folder.mkdir(parents=True,exist_ok=True)
            frame.save(folder/'health.png')
            print('[血量] '+{'full':'满血','low':'非满血',None:'无法确认，本次不触发'}[state])
            self.health_next_notice=now+10
        if alert:
            print(f"[提醒] 连续确认非满血，下一轮抛竿前按住 X {self.c['health_x_hold']:g} 秒")
            from countdown_alert import play_warning
            try:play_warning()
            except RuntimeError as exc:print('提示音播放失败：',exc)

    def prepare_round(self):
        self.check()
        if not self.health_alert or not self.health_alert.pending_x:return
        episode=self.health_alert.episode
        print(f"[血量处理] 本轮抛竿前长按 X {self.c['health_x_hold']:g} 秒")
        self.check()
        self.held_keys.add(0x58)
        try:
            self.win.set_key(0x58,True)
            self.wait(self.c['health_x_hold'])
        finally:
            self.win.set_key(0x58,False)
            self.held_keys.discard(0x58)
        # Interrupted waits leave the action pending for an explicit resume.
        if self.health_alert.episode==episode:self.health_alert.pending_x=False

    def release(self):
        for vk in tuple(self.held_keys):
            self.win.set_key(vk,False)
            self.held_keys.discard(vk)
        for name in tuple(self.held):
            self.win.button(False, name)
            self.held.discard(name)

    def down(self, name):
        self.check()
        if self.live:
            self.held.add(name)
            self.win.button(True, name)

    def up(self, name):
        if name in self.held:
            self.win.button(False, name)
            self.held.discard(name)

    def check(self, monitor=True):
        if self.win.key(0x78):
            raise KeyboardInterrupt
        if self.win.key(0x77):
            raise Paused('手动暂停')
        if not self.win.focused():
            raise Paused('已切出游戏，自动暂停')
        if monitor and self.monitor_failures and 'left' not in self.held:
            self.poll_health()
            self.poll_timer()
            self.poll_failure()

    def capture_failure_region(self):
        from PIL import ImageGrab
        x,y,w,h = self.win.bounds()
        rx,ry,rw,rh = self.c['failure_region']
        frame = ImageGrab.grab(bbox=(x+round(rx*w),y+round(ry*h),
                                    x+round((rx+rw)*w),y+round((ry+rh)*h)),all_screens=True)
        self.check(monitor=False)
        return frame

    def poll_failure(self):
        now = time.monotonic()
        if now < self.failure_next_scan:
            return
        self.failure_next_scan = now+self.c['failure_scan_interval']
        label = self.failure_detector.detect(self.capture_failure_region())
        self.check(monitor=False)
        if not label:
            self.failure_candidate = None
            self.failure_hits = 0
            self.failure_clear_frames += 1
            if self.failure_clear_frames >= 3:
                self.failure_latched = False
            return
        self.failure_clear_frames = 0
        if self.failure_latched == label:
            return
        self.failure_hits = self.failure_hits+1 if label == self.failure_candidate else 1
        self.failure_candidate = label
        if self.failure_hits >= 2:
            self.failure_latched = label
            self.failure_hits = 0
            if label == '背包已满':
                print("[提示] 背包已满（仅记录，暂不处理）")
                return
            raise FishingFailed(label)

    def wait(self, seconds, monitor=True):
        end = time.monotonic()+seconds
        while True:
            self.check(monitor=monitor)
            remain = end-time.monotonic()
            if remain <= 0:
                return
            time.sleep(min(0.02,remain))

    def click(self):
        self.down('left')
        try:
            self.wait(self.c['click_hold'])
        finally:
            self.up('left')

    def scan(self):
        from PIL import ImageGrab
        self.check()
        x,y,w,h = self.win.bounds()
        rx,ry,rw,rh = self.c['region']
        bbox = (x+round(rx*w),y+round(ry*h),x+round((rx+rw)*w),y+round((ry+rh)*h))
        if self.c['region_mode'] == 'screen':
            sx,sy,sw,sh = self.c['screen_region']
            bbox = (sx,sy,sx+sw,sy+sh)
        if self.c['detection_mode']=='float':
            rx,ry,rw,rh=self.c['float_region']
            bbox=(x+round(rx*w),y+round(ry*h),x+round((rx+rw)*w),y+round((ry+rh)*h))
        frame = ImageGrab.grab(bbox=bbox,all_screens=True)
        self.check()
        hit,count = self.detector.update(frame)
        return hit,count,frame

    def save_detection_debug(self, frame, count, hit):
        now = time.monotonic()
        d = self.detector
        strength = (d.missing if self.c['detection_mode']=='float' else count/max(1, d.required_pixels)) if d.ready else 0
        best = d.ready and strength > self.debug_best
        if now < self.debug_next and not hit and not best:
            return
        folder = BASE/'work'/'detection_debug'
        folder.mkdir(parents=True, exist_ok=True)
        frame.save(folder/'latest.png')
        d.mask.save(folder/'latest_mask.png')
        state = dict(mode=self.c['detection_mode'], ready=d.ready, largest_splash=count, total_pixels=d.total_pixels,
                     background=d.baseline, required_pixels=round(d.required_pixels,1),
                     brightness_delta=d.threshold, candidate=hit, reason=d.reason,
                     frame_size=list(frame.size))
        if self.c['detection_mode']=='float':
            state.update(float_x=d.lock_x, missing_frames=d.missing)
        (folder/'latest.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        if best:
            self.debug_best = strength
            frame.save(folder/'best.png')
            d.mask.save(folder/'best_mask.png')
            (folder/'best.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        if hit:
            frame.save(folder/'candidate.png')
        if now >= self.debug_next:
            print(f"[识别] {d.reason}，漂尾颜色像素={count}" if self.c['detection_mode']=='float' else f"[识别] {d.reason}，连续水花={count}，背景={d.baseline:.0f}，需达到={d.required_pixels:.0f}")
            self.debug_next = now+1

    def observe(self):
        self.detector = self.make_detector()
        self.debug_best = -1
        print('仅观察：先右键放大并稳定画面再按 F8；当前模式：'+self.c['detection_mode'])
        last = 0
        while True:
            hit,count,frame = self.scan()
            self.save_detection_debug(frame, count, hit)
            if time.monotonic()-last >= 1:
                print(f'水花像素={count} 背景={self.detector.baseline:.0f} 就绪={self.detector.ready} 候选水花={hit}')
                frame.save(BASE/'preview.png')
                self.detector.mask.save(BASE/'splash_mask.png')
                last = time.monotonic()
            self.wait(self.c['scan_interval'])

    def read_fishing_state(self):
        if not self.c['state_enabled'] or self.state_reader is None:return None
        from PIL import ImageGrab
        self.check()
        x,y,w,h=self.win.bounds();rx,ry,rw,rh=self.c['state_region']
        frame=ImageGrab.grab(bbox=(x+round(rx*w),y+round(ry*h),x+round((rx+rw)*w),y+round((ry+rh)*h)),all_screens=True)
        self.check()
        return self.state_reader.read(frame)

    def confirmed_fishing_state(self):
        first=self.read_fishing_state()
        if first is None:return None
        self.wait(.12)
        return first if self.read_fishing_state()==first else None

    def prepare_cast_state(self):
        state=self.confirmed_fishing_state()
        if state!='fishing':return
        print('[状态] 仍在钓鱼中，按空格退出后重新抛竿')
        self.check()
        self.held_keys.add(0x20)
        try:
            self.win.set_key(0x20,True)
            self.wait(self.c['click_hold'])
        finally:
            self.win.set_key(0x20,False)
            self.held_keys.discard(0x20)
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            self.wait(.2)
            if self.confirmed_fishing_state()=='idle':return
        raise Paused('退出钓鱼后未确认抛竿界面，请检查画面后按 F8 继续')

    def check_fishing_state(self):
        now=time.monotonic()
        if now<self.state_next_scan:return
        self.state_next_scan=now+self.c['state_scan_interval']
        state=self.read_fishing_state()
        self.state_idle_hits=self.state_idle_hits+1 if state=='idle' else 0
        if self.state_idle_hits>=2:
            raise FishingNotCast()

    def cycle(self):
        self.prepare_cast_state()
        print('左键第一次')
        self.click()
        self.wait(self.c['first_click_wait'])
        print('左键第二次')
        self.click()
        self.wait(self.c['right_press_delay'])
        print(f"第二次左键后等待 {self.c['right_press_delay']:g} 秒，按住右键")
        self.down('right')
        found, hits = False, 0
        try:
            settle = self.c['cast_settle'] + self.c['zoom_settle']
            print(f"保持右键，等待 {settle:g} 秒，暂不识别漂尾/水花（失败提示仍监测）")
            self.wait(settle)
            self.detector = self.make_detector()
            self.debug_best = -1
            self.state_idle_hits = 0
            self.state_next_scan = 0
            deadline = time.monotonic()+self.c['bite_timeout']
            print('动画等待结束，开始'+('锁定漂尾' if self.c['detection_mode']=='float' else '采集水面背景'))
            while time.monotonic() < deadline:
                self.check_fishing_state()
                hit,count,frame = self.scan()
                self.save_detection_debug(frame, count, hit)
                hits = hits+1 if hit else 0
                if (hit if self.c['detection_mode']=='float' else hits >= self.c['confirm_frames']):
                    # A vanished float is not a bite after fishing mode has ended.
                    if self.confirmed_fishing_state()=='idle':raise FishingNotCast()
                    found = True
                    break
                self.wait(self.c['scan_interval'])
        finally:
            self.up('right')
        if not found:
            raise FishingTimeout('等待咬钩超时')
        self.wait(self.c['release_wait'])
        print('确认咬钩，左键提竿')
        self.click()
        self.wait(self.c['final_click_wait'])
        print('最后一次左键')
        self.click()
        self.wait(self.c['catch_wait'])

    def run(self):
        try:
            if not self.live:
                self.observe()
            else:
                from failure_text import FailureTextDetector
                self.failure_detector = FailureTextDetector()
                if self.c['state_enabled'] and self.state_reader is None:
                    from fishing_state import FishingStateReader
                    self.state_reader = FishingStateReader()
                if self.c['timer_enabled'] and self.timer_reader is None:
                    from timer_reader import TimerReader
                    from countdown_alert import CountdownAlert
                    self.timer_reader=TimerReader()
                    self.timer_alert=CountdownAlert(self.c['timer_alert_minutes'])
                if self.c['health_enabled'] and self.health_reader is None:
                    from health_monitor import HealthReader, HealthAlert
                    self.health_reader=HealthReader()
                    self.health_alert=HealthAlert(self.c['health_confirm_frames'])
                self.monitor_failures = True
                self.failure_next_scan = 0
                i = 0
                while self.c['max_cycles'] == 0 or i < self.c['max_cycles']:
                    i += 1
                    limit = self.c['max_cycles'] or '不限'
                    print(f"第 {i}/{limit} 轮（不代表成功渔获数）")
                    try:
                        self.prepare_round()
                        self.cycle()
                    except FishingNotCast:
                        self.release()
                        print('[状态] 已回到未抛竿界面，重新开始抛竿')
                        continue
                    except FishingTimeout:
                        self.release()
                        print('等待咬钩超时，已松键，直接重新开始抛竿')
                        continue
                    except FishingFailed as exc:
                        self.release()
                        print(f"检测到『{exc}』，等待 {self.c['failure_retry_wait']:g} 秒后重新抛竿")
                        self.wait(self.c['failure_retry_wait'], monitor=False)
                        self.detector = self.make_detector()
                raise Paused('已达到本次轮数上限')
        finally:
            self.monitor_failures = False
            self.release()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='发送鼠标点击；默认仅观察')
    args = parser.parse_args(argv)
    win,c = Windows(),config()
    runner = Runner(win,c,args.live)
    print('台钓助手 | '+('自动点击模式' if args.live else '仅观察模式'))
    print('F6 绑定前台游戏 / F7 框选当前模式识别区域 / F8 开始或暂停 / F9 退出')
    print('先手动拿出台钓杆，停在可以抛竿的状态；启动后不会自动点击。')
    try:
        while True:
            if win.key(0x78):
                break
            if win.key(0x75):
                win.bind()
            if win.key(0x76) and win.focused():
                win.calibrate(c)
            if win.key(0x77):
                if not win.focused():
                    print('请切到游戏，先按 F6 绑定。')
                else:
                    try:
                        runner.run()
                    except Paused as e:
                        print('暂停：',e)
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        runner.release()
    print('已退出')


if __name__ == '__main__':
    main()
