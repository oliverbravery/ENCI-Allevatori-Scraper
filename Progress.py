import time 
import sys
from multiprocessing import Manager
from ctypes import c_int

class Counter(object):
    def __init__(self, manager: Manager, initval=0):
        self.val = manager.Value(c_int, initval)
        self.lock = manager.Lock()
    def increment(self):
        with self.lock:
            self.val.value += 1
    def decrement(self):
        with self.lock:
            self.val.value -= 1
    @property
    def value(self):
        return self.val.value

class Progress(object):
    start_time: float
    amount_completed: Counter
    total_amount: int
    
    def __init__(self, start_time: float, total_amount: int, manager: Manager):
        self.start_time = start_time
        self.total_amount = total_amount
        self.amount_completed = Counter(manager, 0)
        
    def increment_amount_completed(self) -> None:
        self.amount_completed.increment()
    
    def calculate_percentage_complete(self) -> float:
        return round((float(self.amount_completed.value)/float(self.total_amount))*100.0, 1)
    
    def display_progress(self) -> None:
        sec: float = time.time()-self.start_time
        percentage: float = self.calculate_percentage_complete()
        title: str = f'{self.amount_completed.value}/{self.total_amount} - ({percentage}% {sec//60:02.0f}:{sec%60:02.0f}) '
        bar_width: int = 20
        full_width: int = int(bar_width*percentage/100.0)
        empty_width: int = bar_width - full_width
        sys.stdout.write('\r'+'['+full_width*'#'+empty_width*'.'+'] '+title)
        sys.stdout.flush()   
