"""Validate countdown readings and play one asynchronous warning per match."""
from pathlib import Path
import time


class CountdownAlert:
    def __init__(self, minutes):
        self.limit=round(minutes*60)
        self.previous=None
        self.previous_at=None
        self.confirmations=0
        self.alerted=False
        self.last_confirmed=None
        self.confirmed_at=None
        self.candidate_start=None

    def expected(self, now):
        # A prediction only helps resolve visually ambiguous digits. It never
        # triggers a warning or replaces a missing screenshot reading.
        if self.confirmed_at is None or now-self.confirmed_at>20:return None
        return max(0,self.last_confirmed-(now-self.confirmed_at))

    def update(self, seconds, now=None):
        now=time.monotonic() if now is None else now
        if seconds is None or not 0<=seconds<3600:
            self.previous=None
            self.confirmations=0
            return False
        anchored=self.confirmed_at is not None
        follows=(anchored and seconds<=self.last_confirmed and
                 abs((self.last_confirmed-seconds)-(now-self.confirmed_at))<=2.2)
        # Ignore impossible downward jumps while the last reliable reading is
        # recent. A new, larger match clock needs a fresh decreasing sequence.
        restart=(anchored and seconds>self.last_confirmed+90)
        stale=anchored and now-self.confirmed_at>30
        if anchored and not follows and not restart and not stale:
            self.previous=None
            self.confirmations=0
            return False
        consistent=(self.previous is not None and seconds<=self.previous and
                    abs((self.previous-seconds)-(now-self.previous_at))<=1.5)
        if consistent:
            self.confirmations+=1
        else:
            self.confirmations=1
            self.candidate_start=seconds
        self.previous,self.previous_at=seconds,now
        if not follows and (self.confirmations<3 or seconds>=self.candidate_start):return False
        if restart and not follows:self.alerted=False
        self.last_confirmed,self.confirmed_at=seconds,now
        if seconds<=self.limit and not self.alerted:
            self.alerted=True
            return True
        return False


def play_warning():
    import winsound
    path=Path(__file__).resolve().parent/'assets'/'time_warning.wav'
    winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
