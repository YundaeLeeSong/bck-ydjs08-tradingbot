"""
CLI Module
==========
Responsible for rendering information in the terminal.
"""
from rich.console import Console
from rich.table import Table

def display_summary_table(name, session):
    """
    Renders a formatted table of the analysis results to the console.
    
    Args:
        name (str): Strategy name (e.g. 'Longing', 'Shorting').
        session (AnalysisSession): The session containing the runtime data.
    """
    console = Console()
    table = Table(title=f"{name.upper()} SUMMARY")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Sector", style="magenta")
    table.add_column("Price", justify="right")
    table.add_column("% Change", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Market Cap", justify="right")
    table.add_column("R-Squared", justify="right")
    table.add_column("Slope", justify="right")
    table.add_column("Zeros", justify="right", style="green")
    table.add_column("MAD", justify="right", style="yellow")
    table.add_column("SD", justify="right", style="yellow")
    
    for model in session.results:
        mcap_billions = model.market_cap / 1_000_000_000
        vol_millions = model.volume / 1_000_000
        zeros_str = str(model.num_zero_crossings) if model.num_zero_crossings is not None else "N/A"
        mad_str = f"{model.mad:.2f}%" if model.mad is not None else "N/A"
        sd_str = f"{model.sd:.2f}%" if model.sd is not None else "N/A"
        r_sq_str = f"{model.r_squared:.4f}" if model.r_squared is not None else "N/A"
        slope_str = f"{model.slope:.4f}" if model.slope is not None else "N/A"
        
        change_style = "red" if model.change_pct < 0 else "green"
        
        table.add_row(
            model.ticker,
            model.sector or "N/A",
            f"{model.price:.2f}",
            f"[{change_style}]{model.change_pct:.2f}%[/{change_style}]",
            f"{vol_millions:.2f}M",
            f"{mcap_billions:.2f}B",
            r_sq_str,
            slope_str,
            zeros_str,
            mad_str,
            sd_str
        )
        
    console.print(table)