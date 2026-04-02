"""
Analysis Report Module
======================
Keeps track of multiple StockMetrics models over the course of a pipeline run.
"""
from typing import List
from core.stock_metrics import StockMetrics

# [Registry / State Pattern]: Keeps track of multiple StockMetrics models over the course of a pipeline run.
class AnalysisReport:
    """
    Manages and stores the results of multiple stock analyses during a single run.
    """
    def __init__(self, name: str):
        """
        Initializes the AnalysisReport.
        
        Args:
            name (str): The name of the session (e.g., 'Longing' or 'Shorting').
        """
        self.name = name
        self.results: List[StockMetrics] = []
        
    def add_result(self, result: StockMetrics):
        """
        Adds a single runtime data result to the session.
        
        Args:
            result (StockMetrics): The runtime data of a single stock to be added.
            
        Returns:
            None
        """
        self.results.append(result)
        
    def __repr__(self):
        """
        Returns a string representation of the AnalysisReport.
        
        Returns:
            str: The string representation.
        """
        lines = [f"Table Name: {self.name}", f"Rows: {len(self.results)}"]
        for row in self.results:
            lines.append(repr(row))
        return "\n".join(lines)
