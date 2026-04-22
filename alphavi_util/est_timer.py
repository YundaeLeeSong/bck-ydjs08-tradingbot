"""
EST Timer module for Alpaca API.

Provides a Singleton class to calculate extended hours trading periods
without reallocating timezone and time boundary objects repeatedly.
"""

import pytz
from datetime import datetime, time as dtime

class ESTTimer:
    """
    Singleton EST Timer to optimize timezone and time bounds allocation.
    """
    _instance = None

    def __new__(cls):
        # [Singleton] (1): Allocate the single instance if it doesn't exist.
        if cls._instance is None:
            cls._instance = super(ESTTimer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # [Singleton] (2): Initialize configuration once.
        if self._initialized:
            return
            
        self.est_tz = pytz.timezone('US/Eastern')
        self.pre_start = dtime(4, 0, 1)      # 4:00 AM ET
        self.pre_end = dtime(9, 29, 59)      # 9:30 AM ET
        self.post_start = dtime(16, 0, 1)    # 4:00 PM ET
        self.post_end = dtime(19, 59, 59)    # 8:00 PM ET 
        
        self._initialized = True

    def is_extended_hours(self) -> bool:
        """
        Determines if the current US/Eastern time falls within extended trading hours.
        """
        t = datetime.now(self.est_tz).time()
        return (self.pre_start <= t <= self.pre_end) or (self.post_start <= t <= self.post_end)
