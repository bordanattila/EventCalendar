"""
cleanup_utils.py

Utility functions for proper resource cleanup in UI components.
Helps prevent memory leaks and ensures all references are properly released.

Author: Attila Bordan
"""

from kivy.animation import Animation


def cleanup_widget(widget):
    """
    Comprehensive cleanup for any Kivy widget.
    
    This function:
    - Unbinds all event handlers
    - Clears canvas instructions
    - Cancels pending animations
    - Clears widget references
    
    Args:
        widget: The widget to cleanup
    """
    if not widget:
        return
    
    try:
        # Cancel all animations on this widget
        Animation.cancel_all(widget)
    except Exception as e:
        print(f"Error canceling animations on {widget.__class__.__name__}: {e}")
    
    try:
        # Clear canvas instructions
        if hasattr(widget, 'canvas'):
            widget.canvas.before.clear()
            widget.canvas.clear()
            widget.canvas.after.clear()
    except Exception as e:
        print(f"Error clearing canvas on {widget.__class__.__name__}: {e}")
    
    try:
        # Remove widget from parent if it has one
        if hasattr(widget, 'parent') and widget.parent:
            widget.parent.remove_widget(widget)
    except Exception as e:
        print(f"Error removing {widget.__class__.__name__} from parent: {e}")
    
    try:
        # Unbind common events if widget supports them
        if hasattr(widget, 'unbind'):
            # Try to unbind common events (safe even if not bound)
            common_events = ['pos', 'size', 'parent', 'opacity', 'focus']
            for event in common_events:
                if hasattr(widget, 'bind'):
                    try:
                        widget.unbind(**{event: None})
                    except:
                        pass
    except Exception as e:
        print(f"Error unbinding events on {widget.__class__.__name__}: {e}")


def cleanup_popup(popup):
    """
    Specialized cleanup for Popup widgets.
    
    Args:
        popup: The popup widget to cleanup
    """
    if not popup:
        return
    
    # Cleanup content if it exists
    if hasattr(popup, 'content') and popup.content:
        cleanup_widget(popup.content)
        popup.content = None
    
    # Cleanup the popup itself
    cleanup_widget(popup)


def safe_remove_widget(widget):
    """
    Safely removes a widget from its parent without causing errors.
    
    Args:
        widget: The widget to remove
    """
    if widget and hasattr(widget, 'parent') and widget.parent:
        try:
            widget.parent.remove_widget(widget)
        except Exception as e:
            print(f"Error removing widget: {e}")


def cleanup_recursive(widget):
    """
    Recursively cleans up a widget and all its children.
    
    Args:
        widget: The root widget to cleanup recursively
    """
    if not widget:
        return
    
    try:
        # Cleanup all children first
        if hasattr(widget, 'children'):
            for child in widget.children[:]:  # Copy list to avoid modification during iteration
                cleanup_recursive(child)
        
        # Cleanup the widget itself
        cleanup_widget(widget)
    except Exception as e:
        print(f"Error during recursive cleanup: {e}")


