"""KivyMD compatibility helpers for mobile screens."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.label import Label
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.textfield import MDTextField


def box_layout(**kwargs):
    return MDBoxLayout(**kwargs)


def title_label(text: str):
    return MDLabel(
        text=text,
        halign="left",
        theme_text_color="Custom",
        text_color=(0.06, 0.12, 0.24, 1),
        size_hint_y=None,
        height=dp(30),
    )


def status_label(text: str):
    return MDLabel(
        text=text,
        halign="left",
        theme_text_color="Custom",
        text_color=(0.29, 0.36, 0.48, 1),
        size_hint_y=None,
        height=dp(24),
    )


def body_label(text: str = ""):
    # Keep a plain Kivy Label for predictable multiline rendering.
    label = Label(
        text=text,
        halign="left",
        valign="top",
        size_hint_y=None,
        color=(0.09, 0.13, 0.22, 1),
    )
    label.bind(
        width=lambda inst, w: setattr(inst, "text_size", (w, None)),
        texture_size=lambda inst, _sz: setattr(inst, "height", inst.texture_size[1]),
    )
    return label


def text_field(
    hint_text: str,
    *,
    text: str = "",
    numeric: bool = False,
):
    kwargs = {
        "hint_text": hint_text,
        "text": text,
        "mode": "outlined",
        "size_hint_y": None,
        "height": dp(56),
    }
    if numeric:
        kwargs["input_filter"] = "int"
    return MDTextField(**kwargs)


def button(text: str, *, outlined: bool = False):
    style = "outlined" if outlined else "filled"
    return MDButton(
        MDButtonText(text=text),
        style=style,
        size_hint_y=None,
        height=dp(46),
    )


def icon_button(icon: str):
    return MDIconButton(icon=icon, size_hint=(None, None), size=(dp(42), dp(42)))


def progress_bar(max_value: float = 100, value: float = 0):
    bar = MDLinearProgressIndicator()
    bar.max = max_value
    bar.value = value
    bar.indicator_color = (0.10, 0.37, 0.83, 1)
    bar.track_color = (0.84, 0.90, 0.98, 1)
    bar.size_hint_y = None
    bar.height = dp(12)
    return bar


def notify(message: str) -> None:
    MDSnackbar(
        MDSnackbarText(text=message),
        y=dp(24),
        pos_hint={"center_x": 0.5},
        size_hint_x=0.9,
    ).open()


def card_container():
    card = MDCard(
        orientation="vertical",
        padding=dp(14),
        spacing=dp(10),
        radius=[20, 20, 20, 20],
        elevation=3,
        ripple_behavior=True,
        md_bg_color=(0.99, 0.995, 1, 1),
        size_hint_y=None,
    )
    card.bind(minimum_height=card.setter("height"))
    return card


def kpi_card(label: str, value: str, r: float = 0.10, g: float = 0.37, b: float = 0.83):
    """Create a prominent KPI card with large value display and accent color."""
    card = MDCard(
        orientation="vertical",
        padding=dp(16),
        spacing=dp(6),
        radius=[16, 16, 16, 16],
        elevation=2,
        md_bg_color=(r, g, b, 0.08),
        size_hint_y=None,
        height=dp(110),
    )
    value_label = MDLabel(
        text=value,
        halign="left",
        theme_text_color="Custom",
        text_color=(r, g, b, 1),
        size_hint_y=None,
        height=dp(56),
    )
    label_label = MDLabel(
        text=label,
        halign="left",
        theme_text_color="Custom",
        text_color=(0.40, 0.48, 0.60, 1),
        size_hint_y=None,
        height=dp(20),
    )
    card.add_widget(value_label)
    card.add_widget(label_label)
    return card
