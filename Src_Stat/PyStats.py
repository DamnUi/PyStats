"""PyStats - A Python Code Statistics Visualization Tool.

This module serves as the entry point for the PyStats tool, which analyzes and visualizes
statistics about Python codebases.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Tuple, Union

from rich.console import Console

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PyStatsApp:
    """Main application class for PyStats."""
    
    def __init__(self):
        """Initialize PyStats application with console setup."""
        self.console = Console(record=True)
        self._pystat_print = self.console.print
        self._stats_wrapper = None
    
    def initialize(self) -> bool:
        """Initialize PyStats and its dependencies.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            import _PyStats
            self._PyStats = _PyStats
            return True
        except ImportError as e:
            self._handle_import_error(e)
            return False
    
    def _handle_import_error(self, error: ImportError) -> None:
        """Handle import errors with helpful messages.
        
        Args:
            error: The ImportError that occurred
        """
        self.console.print("[red]PyStats is not installed correctly[/]")
        self.console.print("[yellow]Please ensure all dependencies are installed[/]")
        logger.error(f"Import error: {error}")
    
    def create_stats_wrapper(self, working_path: Union[str, Path]) -> None:
        """Create the statistics wrapper for analysis.
        
        Args:
            working_path: Path to analyze
        """
        self._stats_wrapper = self._PyStats.VisualWrapper(self._PyStats.working_path)
    
    def render_image(self) -> Tuple[bool, Optional[str]]:
        """Render statistics as an image if configured.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not self._stats_wrapper:
            return False, "Statistics wrapper not initialized"
            
        try:
            result = self._stats_wrapper.img_render(
                remove_check=True,
                force_show=False,
                clear_screen=False
            )
            return result[0], None
        except Exception as e:
            logger.error(f"Error rendering image: {e}")
            return False, str(e)
    
    def display_statistics(self) -> None:
        """Display the statistics based on current configuration."""
        if not self._stats_wrapper:
            logger.error("Statistics wrapper not initialized")
            return
            
        try:
            if self._PyStats.args.adhd:
                # Recreate wrapper for ADHD mode
                self._stats_wrapper = self._PyStats.VisualWrapper(self._PyStats.working_path)
            self._pystat_print(self._stats_wrapper.get_all(True))
        except Exception as e:
            logger.error(f"Error displaying statistics: {e}")
            self.console.print(f"[red]Error displaying statistics: {e}[/]")

def main() -> int:
    """Main entry point for PyStats.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    app = PyStatsApp()
    
    if not app.initialize():
        return 1
        
    app.create_stats_wrapper(app._PyStats.working_path)
    
    # Try to render image first
    success, error = app.render_image()
    if success:
        return 0
    elif error:
        logger.warning(f"Image rendering failed: {error}")
    
    # Fall back to displaying statistics
    app.display_statistics()
    return 0

if __name__ == "__main__":
    sys.exit(main())

        
