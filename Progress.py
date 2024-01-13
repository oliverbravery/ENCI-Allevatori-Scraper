import time 
import sys
from multiprocessing import Manager
from ctypes import c_int

class Counter(object):
    """
    A class for a counter that can be shared between processes.
    """
    def __init__(self, manager: Manager, initval=0):
        """
        Initializes the counter.
        """
        self.val = manager.Value(c_int, initval)
        self.lock = manager.Lock()
        
    def increment(self):
        """
        Increments the counter by 1.
        """
        with self.lock:
            self.val.value += 1
            
    def decrement(self):
        """
        Decrements the counter by 1.
        """
        with self.lock:
            self.val.value -= 1
            
    @property
    def value(self):
        """
        Returns the value of the counter.
        """
        return self.val.value

class Progress(object):
    """
    A class for tracking progress accross processes.
    """
    start_time: float
    amount_completed: Counter
    total_amount: int
    
    def __init__(self, start_time: float, total_amount: int, manager: Manager):
        """
        Initializes the progress tracker.
        
        Args:
            start_time (float): The time the progress tracker was started.
            total_amount (int): The total amount of tasks to be completed.
            manager (Manager): The multiprocessing manager used to share the counter accross processes.
        """
        self.start_time = start_time
        self.total_amount = total_amount
        self.amount_completed = Counter(manager, 0)
        
    def increment_amount_completed(self) -> None:
        """
        Increments the amount of completed tasks by 1. Shadows the Counter classes increment method.
        """
        self.amount_completed.increment()
    
    def calculate_percentage_complete(self, decimal_places: int = 1) -> float:
        """
        Calculates the percentage of tasks completed

        Args:
            decimal_places (int): Number of decimal places the percentage should be calculated to. Defaults to 1.
            
        Returns:
            float: The percentage of tasks completed.
        """
        return round((float(self.amount_completed.value)/float(self.total_amount))*100.0, decimal_places)
    
    def display_progress(self) -> None:
        """
        Displays the progress of the tasks in the console in the format: [##########..........] 5/10 - (50.0% 00:06)
        """
        # get the time elapsed since the progress tracker was started
        sec: float = time.time()-self.start_time
        percentage: float = self.calculate_percentage_complete()
        stat_string: str = f'{self.amount_completed.value}/{self.total_amount} - ({percentage}% {sec//60:02.0f}:{sec%60:02.0f}) '
        bar_width: int = 20
        full_width: int = int(bar_width*percentage/100.0)
        empty_width: int = bar_width - full_width
        sys.stdout.write('\r'+'['+full_width*'#'+empty_width*'.'+'] '+stat_string)
        sys.stdout.flush()   
