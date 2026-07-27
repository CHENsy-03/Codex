"""UI utilities - mousewheel support."""

from __future__ import annotations


def bind_mousewheel(canvas) -> None:
    def _on_wheel(event):
        delta = getattr(event, "delta", 0)
        num = getattr(event, "num", 0)
        if num == 4 or (num == 0 and delta > 0):
            canvas.yview_scroll(-1, "units")
        elif num == 5 or (num == 0 and delta < 0):
            canvas.yview_scroll(1, "units")
    def _on_enter(event):
        canvas.bind_all("<MouseWheel>", _on_wheel)
        canvas.bind_all("<Button-4>", _on_wheel)
        canvas.bind_all("<Button-5>", _on_wheel)
    def _on_leave(event):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")
    canvas.bind("<Enter>", _on_enter)
    canvas.bind("<Leave>", _on_leave)

def unbind_mousewheel(canvas) -> None:
    try:
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")
    except Exception:
        pass
