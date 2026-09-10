"""
SiteSync AI — Entry Point
"""
import sys
from rich.console import Console

console = Console()

def main():
    console.print("[bold cyan]SiteSync AI[/bold cyan] — Infrastructure Project Management")
    console.print("To run the web application, use:")
    console.print("  [green]streamlit run frontend/app.py[/green]")
    console.print("To seed the database, use:")
    console.print("  [green]python -m sitesync.db.seed[/green]")
    console.print("To run tests, use:")
    console.print("  [green]pytest tests/[/green]")

if __name__ == "__main__":
    main()
