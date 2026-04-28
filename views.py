# views.py — Quad8 Gym System UI
# Full PyQt6 desktop application with dark blue cinematic theme

import os
import sys
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QScrollArea, QGridLayout,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QSpacerItem, QSizePolicy, QAbstractItemView, QTextEdit,
    QSplitter, QListWidget, QListWidgetItem, QGroupBox, QGraphicsDropShadowEffect,
    QSpinBox, QSpinBox, QDoubleSpinBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPropertyAnimation,
    QEasingCurve, QPoint, QRect, pyqtProperty
)
from PyQt6.QtGui import (
    QPixmap, QFont, QFontDatabase, QPalette, QColor, QIcon,
    QPainter, QBrush, QLinearGradient, QRadialGradient,
    QPen, QCursor, QMovie, QPainterPath
)

# ─── ASSET PATHS ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
BACKGROUND_IMG = str(BASE_DIR / "QUAD8_LOG-IN_BG.png")
LOGO_IMG = str(BASE_DIR / "quad8_logo.png")
SIDEBAR_BG = str(BASE_DIR / "sidebar_or_any.png")

# ─── COLOUR PALETTE ─────────────────────────────────────────────────────────
C = {
    # ── Neon Glass palette (softened, easy on the eyes) ──
    # Surfaces are neutral near-black with a faint cool tint so the
    # neon accents pop without straining the eyes.
    "bg":          "#0a0b14",
    "surface":     "#13162a",
    "surface2":    "#1a1d33",
    "surface3":    "#222644",
    "sidebar":     "#0d0f1c",
    # Border colors must be valid Qt QSS — use solid hex, not rgba floats.
    "border":      "#262a44",
    "border2":     "#1d2138",
    "text":        "#eef0ff",
    "text2":       "#a0a8c8",
    "text3":       "#6c7396",
    # Neon gradient stops (kept exactly per the reference)
    "purple":      "#af40ff",
    "indigo":      "#5b42f3",
    "cyan":        "#00ddeb",
    # Primary accent maps to indigo so existing single-color widgets glow
    "accent":      "#5b42f3",
    "accent_h":    "#af40ff",
    "accent_dim":  "rgba(91,66,243,0.22)",
    # Neon green (kept exactly per the reference)
    "green":       "#1BFD9C",
    "green_h":     "#82ffc9",
    "green_dim":   "rgba(27,253,156,0.16)",
    "red":         "#ff5577",
    "red_dim":     "rgba(255,85,119,0.16)",
    "yellow":      "#ffd166",
    "yellow_dim":  "rgba(255,209,102,0.16)",
    "white":       "#ffffff",
}

def qc(key): return QColor(C[key])

# ─── NEON GLOWS (used by buttons & shadows) ──────────────────────────────────
PURPLE_GLOW = QColor(151, 65, 252, int(0.35 * 255))
GREEN_GLOW  = QColor(27, 253, 156, int(0.45 * 255))


# ─── ANIMATED BUTTONS (drop-in QPushButton subclasses) ───────────────────────
# Both are real QPushButtons so .clicked, .setEnabled, .setText, .setFont,
# .setMinimumWidth, etc. all keep working in the existing pages.
class _AnimatedGradientBtn(QPushButton):
    """Purple→indigo→cyan gradient border. Inner fades on hover, scales on press.
    CSS-spec: 300ms hover fade, 150ms press scale, InOutCubic easing."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(44)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # We paint everything ourselves over a transparent button.
        self.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:white;"
            "font:700 11pt 'Segoe UI';letter-spacing:1px;padding:8px 22px;}"
            "QPushButton:disabled{color:#7f88d6;}"
        )
        self._fill_opacity = 1.0   # 1=solid bg, 0=transparent (gradient shows through)
        self._scale = 1.0
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(34); glow.setOffset(0, 0); glow.setColor(PURPLE_GLOW)
        self.setGraphicsEffect(glow)
        self._fill_anim = QPropertyAnimation(self, b"fillOpacity", self)
        self._fill_anim.setDuration(300); self._fill_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._scale_anim = QPropertyAnimation(self, b"scaleFactor", self)
        self._scale_anim.setDuration(150); self._scale_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def getFillOpacity(self): return self._fill_opacity
    def setFillOpacity(self, v): self._fill_opacity = max(0.0, min(1.0, v)); self.update()
    fillOpacity = pyqtProperty(float, fget=getFillOpacity, fset=setFillOpacity)
    def getScaleFactor(self): return self._scale
    def setScaleFactor(self, v): self._scale = v; self.update()
    scaleFactor = pyqtProperty(float, fget=getScaleFactor, fset=setScaleFactor)

    def _run(self, anim, current, target):
        anim.stop(); anim.setStartValue(current); anim.setEndValue(target); anim.start()

    def enterEvent(self, e):
        if self.isEnabled():
            self._run(self._fill_anim, self._fill_opacity, 0.0)
        super().enterEvent(e)
    def leaveEvent(self, e):
        self._run(self._fill_anim, self._fill_opacity, 1.0)
        self._run(self._scale_anim, self._scale, 1.0)
        super().leaveEvent(e)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._run(self._scale_anim, self._scale, 0.92)
        super().mousePressEvent(e)
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._run(self._scale_anim, self._scale, 1.0)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width()/2, self.height()/2
        p.translate(cx, cy); p.scale(self._scale, self._scale); p.translate(-cx, -cy)
        rect = self.rect().adjusted(1, 1, -1, -1)
        outer = QPainterPath(); outer.addRoundedRect(float(rect.x()), float(rect.y()),
            float(rect.width()), float(rect.height()), 8, 8)
        if self.isEnabled():
            grad = QLinearGradient(rect.topLeft().toPointF(), rect.bottomRight().toPointF())
            grad.setColorAt(0.0, QColor(C["purple"]))
            grad.setColorAt(0.5, QColor(C["indigo"]))
            grad.setColorAt(1.0, QColor(C["cyan"]))
            p.fillPath(outer, QBrush(grad))
        else:
            p.fillPath(outer, QBrush(QColor(C["surface3"])))
        inner_r = rect.adjusted(2, 2, -2, -2)
        inner = QPainterPath(); inner.addRoundedRect(float(inner_r.x()), float(inner_r.y()),
            float(inner_r.width()), float(inner_r.height()), 6, 6)
        fill = QColor(C["bg"]); fill.setAlphaF(self._fill_opacity if self.isEnabled() else 1.0)
        p.fillPath(inner, QBrush(fill))
        p.setPen(QPen(QColor(C["white"] if self.isEnabled() else C["text3"])))
        p.setFont(self.font())
        p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.text())
        p.end()


class _SweepOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath(); clip.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 10, 10)
        p.setClipPath(clip)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0.0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(130, 255, 201, 120))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(self.rect(), QBrush(g)); p.end()


class _AnimatedSweepBtn(QPushButton):
    """Transparent neon-green outline button with a 400ms light sweep on hover."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(44)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 2px solid {C['green']};
                border-radius: 10px;
                color: {C['green']};
                font: 700 11pt 'Segoe UI';
                padding: 8px 22px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ color: {C['green_h']}; border-color: {C['green_h']}; }}
            QPushButton:disabled {{ color: {C['text3']}; border-color: {C['text3']}; }}
        """)
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(20); self._glow.setOffset(0, 0); self._glow.setColor(GREEN_GLOW)
        self.setGraphicsEffect(self._glow)
        self._sweep = _SweepOverlay(self); self._sweep.hide()
        self._sweep_anim = QPropertyAnimation(self._sweep, b"pos", self)
        self._sweep_anim.setDuration(400); self._sweep_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._sweep.resize(int(self.width() * 0.45), self.height())

    def enterEvent(self, e):
        if self.isEnabled():
            self._glow.setBlurRadius(34)
            self._sweep.move(-self._sweep.width(), 0)
            self._sweep.show(); self._sweep.raise_()
            self._sweep_anim.stop()
            self._sweep_anim.setStartValue(QPoint(-self._sweep.width(), 0))
            self._sweep_anim.setEndValue(QPoint(self.width(), 0))
            self._sweep_anim.start()
        super().enterEvent(e)
    def leaveEvent(self, e):
        self._glow.setBlurRadius(20); self._sweep.hide(); super().leaveEvent(e)


# ─── GLOBAL STYLESHEET ───────────────────────────────────────────────────────
GLOBAL_QSS = f"""
QWidget {{
    background: transparent;
    color: {C['text']};
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
}}
QScrollBar:vertical {{
    background: {C['surface']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C['border2']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{
    background: {C['surface']};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {C['border2']};
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {{
    background: {C['surface2']};
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    color: {C['text']};
    selection-background-color: {C['accent']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
    border: none;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C['text2']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {C['surface2']};
    border: none;
    selection-background-color: {C['accent_dim']};
    outline: none;
}}

QTableWidget {{
    background: {C['surface']};
    border: none;
    border-radius: 10px;
    gridline-color: transparent;
    outline: none;
}}
QTableWidget::item {{
    padding: 10px 14px;
    border-bottom: none;
    color: {C['text']};
}}
QTableWidget::item:selected {{
    background: {C['accent_dim']};
    color: {C['text']};
}}
QHeaderView::section {{
    background: {C['surface2']};
    color: {C['text2']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 10px 14px;
    border: none;
    border-bottom: 1px solid #1a2438;
    border-right: none;
}}
QHeaderView::section:last {{ border-right: none; }}

QMessageBox {{
    background: {C['surface']};
}}
QDialog {{
    background: {C['surface']};
    border: none;
    border-radius: 12px;
}}
QLabel {{ background: transparent; }}
"""

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def make_btn(text, style="accent", icon="", min_w=0):
    """Factory used everywhere in the app.
    - 'accent' → real animated gradient button (purple→indigo→cyan border, hover fade, press scale)
    - 'green'  → real animated neon-green sweep button (light sweeps across on hover)
    - others   → flat themed QPushButton
    All return a QPushButton subclass so .clicked / .setEnabled / .setText work."""
    label = f"  {icon}  {text}" if icon else text
    if style == "accent":
        btn = _AnimatedGradientBtn(label)
        btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        if min_w: btn.setMinimumWidth(min_w)
        return btn
    if style == "green":
        btn = _AnimatedSweepBtn(label)
        btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        if min_w: btn.setMinimumWidth(min_w)
        return btn

    btn = QPushButton(label)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    if style == "red":
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['red_dim']}; color: {C['red']};
                border: none; border-radius: 8px; padding: 10px 20px;
            }}
            QPushButton:hover {{ background: {C['red']}; color: white; }}
        """)
    elif style == "ghost":
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface2']}; color: {C['text2']};
                border: 1px solid {C['border']};
                border-radius: 8px; padding: 10px 20px;
            }}
            QPushButton:hover {{ background: {C['surface3']}; color: {C['text']}; }}
        """)
    elif style == "logout":
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C['red']};
                border: none; border-radius: 8px;
                padding: 10px 18px; text-align: left;
            }}
            QPushButton:hover {{ background: {C['red_dim']}; }}
        """)
    else:  # fallback / unknown
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface2']}; color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 8px; padding: 10px 20px;
            }}
            QPushButton:hover {{ background: {C['surface3']}; }}
        """)
    if min_w: btn.setMinimumWidth(min_w)
    return btn

def make_label(text, size=13, weight=QFont.Weight.Normal, color=None, mono=False):
    lbl = QLabel(text)
    font = QFont("Courier New" if mono else "Segoe UI", size, weight)
    lbl.setFont(font)
    if color:
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
    else:
        lbl.setStyleSheet(f"color: {C['text']}; background: transparent;")
    return lbl

def separator(horizontal=True):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
    line.setStyleSheet("background: transparent; max-height: 1px;" if horizontal
                       else "background: transparent; max-width: 1px;")
    return line

_card_id_counter = [0]
def card_widget(radius=10):
    """Surface card. Uses an objectName-scoped QSS so child widgets do NOT
    inherit the border/background — fixes the 'every input has a border' glitch."""
    w = QWidget()
    _card_id_counter[0] += 1
    name = f"neonCard{_card_id_counter[0]}"
    w.setObjectName(name)
    w.setStyleSheet(
        f"QWidget#{name} {{ background: {C['surface']}; "
        f"border: 1px solid {C['border']}; border-radius: {radius}px; }}"
    )
    return w

def section_label(text):
    lbl = QLabel(text.upper())
    lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color: {C['text3']}; letter-spacing: 2px; background: transparent; padding: 14px 16px 4px 16px;")
    return lbl

# monkey-patch QLabel for chained calls
QLabel.also = lambda self, fn: (fn(self), self)[1]

# ─── NEON BUTTON ALIASES ─────────────────────────────────────────────────────
# Public names kept for any external import. Real implementations live at the
# top of this file (_AnimatedGradientBtn / _AnimatedSweepBtn).
GradientButton = _AnimatedGradientBtn
NeonSweepButton = _AnimatedSweepBtn


# ─── STAT CARD ───────────────────────────────────────────────────────────────
class StatCard(QWidget):
    def __init__(self, label, value, meta="", color="accent", parent=None):
        super().__init__(parent)
        self._color = C.get(color, C["accent"])
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        lbl = QLabel(label.upper())
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {C['text2']}; letter-spacing: 1.5px; background: transparent;")

        self.val_lbl = QLabel(str(value))
        self.val_lbl.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.val_lbl.setStyleSheet(f"color: {C['text']}; background: transparent;")

        layout.addWidget(lbl)
        layout.addWidget(self.val_lbl)

        if meta:
            m = QLabel(meta)
            m.setFont(QFont("Segoe UI", 11))
            m.setStyleSheet(f"color: {C['text2']}; background: transparent;")
            layout.addWidget(m)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # card bg
        painter.setBrush(QBrush(qc("surface")))
        painter.setPen(QPen(qc("border"), 1))
        painter.drawRoundedRect(rect, 10, 10)

        # top accent bar
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(self._color)))
        painter.drawRoundedRect(0, 0, rect.width(), 3, 2, 2)

    def set_value(self, v):
        self.val_lbl.setText(str(v))

# ─── BACKGROUND WIDGET ───────────────────────────────────────────────────────
class BGWidget(QWidget):
    """Widget that paints a background image + dark overlay."""
    def __init__(self, image_path=None, overlay_alpha=200, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap(image_path) if image_path and os.path.exists(image_path) else None
        self._alpha = overlay_alpha

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(rect.size(),
                                          Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                          Qt.TransformationMode.SmoothTransformation)
            x = (rect.width() - scaled.width()) // 2
            y = (rect.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            grad = QLinearGradient(0, 0, 0, rect.height())
            grad.setColorAt(0, QColor("#050810"))
            grad.setColorAt(0.4, QColor("#080e1d"))
            grad.setColorAt(1, QColor("#030609"))
            painter.fillRect(rect, grad)

        # dark overlay
        painter.fillRect(rect, QColor(0, 0, 0, self._alpha))

# ─── LOGIN SCREEN ────────────────────────────────────────────────────────────
class LoginScreen(BGWidget):
    login_success = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(BACKGROUND_IMG, overlay_alpha=130, parent=parent)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        center = QHBoxLayout()
        center.addStretch()

        panel = QWidget()
        panel.setFixedWidth(400)
        panel.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border: none;
                border-radius: 14px;
            }}
        """)
        panel_shadow = QGraphicsDropShadowEffect(self)
        panel_shadow.setBlurRadius(28)
        panel_shadow.setColor(QColor(59, 130, 246, 60))
        panel_shadow.setOffset(0, 0)
        panel.setGraphicsEffect(panel_shadow)

        pv = QVBoxLayout(panel)
        pv.setContentsMargins(44, 44, 44, 44)
        pv.setSpacing(0)

        # Logo
        logo_lbl = QLabel()
        logo_lbl.setFixedHeight(110)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none; padding-bottom: 12px;")
        if os.path.exists(LOGO_IMG):
            pix = QPixmap(LOGO_IMG)
            if not pix.isNull():
                scaled = pix.scaled(180, 110, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                logo_lbl.setPixmap(scaled)
                logo_shadow = QGraphicsDropShadowEffect(self)
                logo_shadow.setBlurRadius(20)
                logo_shadow.setColor(QColor(59, 130, 246, 120))
                logo_shadow.setOffset(0, 0)
                logo_lbl.setGraphicsEffect(logo_shadow)
            else:
                logo_lbl.setText("QUAD8")
                logo_lbl.setFont(QFont("Segoe UI", 28, QFont.Weight.ExtraBold))
                logo_lbl.setStyleSheet(f"color: {C['accent_h']}; background: transparent; border: none; letter-spacing: 1px; padding-bottom: 12px;")
        else:
            logo_lbl.setText("QUAD8")
            logo_lbl.setFont(QFont("Segoe UI", 28, QFont.Weight.ExtraBold))
            logo_lbl.setStyleSheet(f"color: {C['accent_h']}; background: transparent; border: none; letter-spacing: 1px; padding-bottom: 12px;")
        pv.addWidget(logo_lbl)

        pv.addSpacing(24)

        title = make_label("Welcome Back", 28, QFont.Weight.Bold)
        title.setStyleSheet(f"color: {C['text']}; background: transparent; font-size: 28px; font-weight: 700;")
        pv.addWidget(title)

        sub = make_label("Access your performance dashboard.", 14, color=C["text2"])
        sub.setStyleSheet(f"color: {C['text2']}; background: transparent; margin-bottom: 28px;")
        pv.addWidget(sub)
        pv.addSpacing(24)

        # Username
        user_lbl = QLabel("USERNAME")
        user_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        user_lbl.setStyleSheet(f"color: {C['text2']}; letter-spacing: 1.5px; background: transparent;")
        pv.addWidget(user_lbl)
        pv.addSpacing(6)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Enter username")
        self.user_input.setFixedHeight(44)
        self.user_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C['surface2']};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                padding: 0 14px;
                color: {C['text']};
                font-size: 14px;
            }}
            QLineEdit:focus {{ border: 1px solid {C['accent_h']}; }}
        """)
        self.user_input.returnPressed.connect(self._do_login)
        pv.addWidget(self.user_input)
        pv.addSpacing(16)

        # Password
        pw_lbl = QLabel("PASSWORD")
        pw_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        pw_lbl.setStyleSheet(f"color: {C['text2']}; letter-spacing: 1.5px; background: transparent;")
        pv.addWidget(pw_lbl)
        pv.addSpacing(6)

        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("Enter password")
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_input.setFixedHeight(44)
        self.pw_input.setStyleSheet(self.user_input.styleSheet())
        self.pw_input.returnPressed.connect(self._do_login)
        pv.addWidget(self.pw_input)
        pv.addSpacing(8)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {C['red']}; font-size: 12px; background: transparent;")
        self.err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pv.addWidget(self.err_lbl)
        pv.addSpacing(16)

        login_btn = QPushButton("SIGN IN")
        login_btn.setFixedHeight(52)
        login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        login_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['accent']};
                color: white;
                border: none;
                border-radius: 10px;
                letter-spacing: 2px;
                font-size: 14px;
                padding: 0 12px;
            }}
            QPushButton:hover {{ background: {C['accent_h']}; }}
            QPushButton:pressed {{ background: {C['accent']}; }}
        """)
        login_btn.clicked.connect(self._do_login)
        pv.addWidget(login_btn)

        pv.addSpacing(24)
        quote = make_label('"The only bad workout is the one that didn\'t happen."', 11, color=C["text3"])
        quote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote.setStyleSheet(f"color: {C['text3']}; font-style: italic; background: transparent;")
        pv.addWidget(quote)

        center.addWidget(panel)
        center.addStretch()

        outer.addStretch(1)
        outer.addLayout(center)
        outer.addStretch(1)

    def _do_login(self):
        u = self.user_input.text().strip()
        p = self.pw_input.text()
        if not u or not p:
            self.err_lbl.setText("Please enter username and password.")
            return
        try:
            from controllers.auth_controller import AuthController
            ok, result = AuthController.login(u, p)
            if ok:
                self.err_lbl.setText("")
                self.login_success.emit(result)
            else:
                self.err_lbl.setText(str(result))
        except Exception as e:
            self.err_lbl.setText(f"Error: {e}")

NAV_ITEMS = [
    ("", [
        ("dashboard",   "", "Dashboard"),
        ("daypass",     "", "Day Pass Entry"),
        ("planreg",     "", "Plan Registration"),
        ("checkin",     "", "Check-in by ID"),
        ("customers",   "", "Customers"),
    ]),
    ("", [
        ("products",    "", "Products"),
        ("sales",       "", "Sales"),
        ("restock",     "", "Restocks"),
    ]),
    ("", [
        ("reports",     "", "Reports"),
        ("auditlog",    "", "Audit Log"),
    ]),
    ("", [
        ("settings",    "",  "Settings"),
        ("recycle",     "", "Recycle Bin"),
        ("profile",     "", "Profile"),
    ]),
]

class _SidebarChildButton(QPushButton):
    def __init__(self, key, label, parent=None):
        super().__init__(label, parent)
        self.key = key
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setCheckable(True)
        self.setFixedHeight(36)
        self._active = False
        self._apply()

    def setActive(self, active):
        self._active = active
        self.setChecked(active)
        self._apply()

    def _apply(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 6px 12px 6px 30px;
                    border: none;
                    border-left: 2px solid {C['cyan']};
                    background: rgba(255,255,255,0.05);
                    color: {C['white']};
                    font: 500 12px 'Segoe UI';
                }}
                QPushButton:hover {{ background: rgba(255,255,255,0.07); }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 6px 12px 6px 30px;
                    border: none;
                    background: transparent;
                    color: {C['text3']};
                    font: 500 12px 'Segoe UI';
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.05);
                    color: {C['white']};
                }}
            """)


class _ParentNavButton(QPushButton):
    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(42)
        self._open = False
        self._apply()

    def setOpen(self, open_):
        self._open = open_
        self._apply()

    def _apply(self):
        if self._open:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 0 14px 0 18px;
                    border: none;
                    border-left: 3px solid qlineargradient(
                        x1:0, y1:0, x2:0, y2:1,
                        stop:0 {C['purple']}, stop:1 {C['cyan']});
                    background: rgba(255,255,255,0.04);
                    color: {C['white']};
                    font: 600 13px 'Segoe UI';
                }}
                QPushButton:hover {{ background: rgba(255,255,255,0.07); }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 0 14px 0 18px;
                    border: none;
                    background: transparent;
                    color: {C['text2']};
                    font: 600 13px 'Segoe UI';
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.05);
                    color: {C['white']};
                }}
            """)


class CollapsibleMenu(QWidget):
    """Parent button + animated child container (accordion)."""
    child_selected = pyqtSignal(str)
    request_open   = pyqtSignal(object)

    def __init__(self, title, items, parent=None):
        super().__init__(parent)
        self._is_open = False
        self.title = title
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        self.parent_btn = _ParentNavButton(f"  {title}")
        self.parent_btn.clicked.connect(self._on_parent_clicked)
        root.addWidget(self.parent_btn)

        self.container = QWidget(self); self.container.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(self.container); cl.setContentsMargins(0, 4, 0, 6); cl.setSpacing(2)

        self.children_btns = []  # list[_SidebarChildButton]
        for key, _icon, label in items:
            b = _SidebarChildButton(key, label)
            b.clicked.connect(lambda _=False, btn=b: self._on_child(btn))
            cl.addWidget(b)
            self.children_btns.append(b)

        self.container.adjustSize()
        self._full_h = self.container.sizeHint().height()
        self.container.setMaximumHeight(0)
        root.addWidget(self.container)

        self._anim = QPropertyAnimation(self.container, b"maximumHeight", self)
        self._anim.setDuration(250); self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _on_parent_clicked(self):
        if self._is_open: self.collapse()
        else: self.request_open.emit(self)

    def _on_child(self, btn):
        for b in self.children_btns: b.setActive(b is btn)
        self.child_selected.emit(btn.key)

    def expand(self):
        if self._is_open: return
        self._is_open = True
        self.parent_btn.setOpen(True)
        target = max(self._full_h, self.container.sizeHint().height())
        self._full_h = target
        self._anim.stop()
        self._anim.setStartValue(self.container.maximumHeight())
        self._anim.setEndValue(target); self._anim.start()

    def collapse(self):
        if not self._is_open: return
        self._is_open = False
        self.parent_btn.setOpen(False)
        self._anim.stop()
        self._anim.setStartValue(self.container.maximumHeight())
        self._anim.setEndValue(0); self._anim.start()

    def deactivate_children(self):
        for b in self.children_btns: b.setActive(False)

    def activate_key(self, key):
        for b in self.children_btns:
            b.setActive(b.key == key)


# Section titles for the accordion groups (NAV_ITEMS sections have empty names)
_SECTION_TITLES = ["Operations", "Inventory", "Insights", "System"]


class SidebarWidget(QWidget):
    nav_clicked = pyqtSignal(str)
    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self._current = "dashboard"
        self._menus = []          # list[CollapsibleMenu]
        self._key_to_menu = {}    # key -> CollapsibleMenu
        self._build()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Solid neon-dark sidebar background
        p.fillRect(self.rect(), QColor(C["sidebar"]))
        # Subtle right-edge glow line
        pen = QPen(QColor(91, 66, 243, 90), 1)
        p.setPen(pen)
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)

        # Logo / brand
        logo_frame = QWidget(); logo_frame.setFixedHeight(90)
        logo_frame.setStyleSheet("background: transparent;")
        lf = QVBoxLayout(logo_frame); lf.setContentsMargins(20, 18, 20, 14)
        logo_lbl = QLabel()
        if os.path.exists(LOGO_IMG):
            pix = QPixmap(LOGO_IMG).scaled(140, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("◆ QUAD8 GYM")
            logo_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Black))
            logo_lbl.setStyleSheet(f"color: {C['white']}; letter-spacing: 2px;")
        logo_lbl.setStyleSheet(logo_lbl.styleSheet() + " background: transparent;")
        lf.addWidget(logo_lbl)
        layout.addWidget(logo_frame)

        # Scrollable nav
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        nav_widget = QWidget(); nav_widget.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 6, 0, 6); nav_layout.setSpacing(2)

        for i, (_section_name, items) in enumerate(NAV_ITEMS):
            title = _SECTION_TITLES[i] if i < len(_SECTION_TITLES) else f"Group {i+1}"
            menu = CollapsibleMenu(title, items)
            menu.request_open.connect(self._open_menu)
            menu.child_selected.connect(self._on_child_selected)
            self._menus.append(menu)
            for key, _icon, _lbl in items:
                self._key_to_menu[key] = menu
            nav_layout.addWidget(menu)

        nav_layout.addStretch()
        scroll.setWidget(nav_widget)
        layout.addWidget(scroll, 1)

        # Logout
        logout_btn = QPushButton("  ⏻  Logout")
        logout_btn.setFixedHeight(46)
        logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['red']};
                border: none;
                text-align: left;
                padding: 0 20px;
                font: 600 12px 'Segoe UI';
            }}
            QPushButton:hover {{ background: {C['red_dim']}; }}
        """)
        logout_btn.clicked.connect(self.logout_clicked)
        layout.addWidget(logout_btn)
        layout.addSpacing(10)

        self._activate("dashboard")

    # ── accordion behavior ─────────────────────────────────────────────────
    def _open_menu(self, menu):
        for m in self._menus:
            if m is not menu: m.collapse()
        menu.expand()

    def _on_child_selected(self, key):
        # Make sure other menus' children are deselected
        for m in self._menus:
            if key not in [b.key for b in m.children_btns]:
                m.deactivate_children()
        self._current = key
        self.nav_clicked.emit(key)

    # Public API kept compatible with MainWindow ─────────────────────────────
    def _activate(self, key):
        self._current = key
        target = self._key_to_menu.get(key)
        for m in self._menus:
            if m is target:
                m.expand(); m.activate_key(key)
            else:
                m.collapse(); m.deactivate_children()

    def set_badge(self, key, count):
        pass


# ─── TOP BAR ─────────────────────────────────────────────────────────────────
class TopBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._build()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(C["surface"]))
        painter.setPen(QPen(QColor(C["border"]), 1))
        painter.drawLine(0, self.height()-1, self.width(), self.height()-1)

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(12)

        self.title_lbl = make_label("Dashboard", 20, QFont.Weight.Bold)
        self.title_lbl.setStyleSheet(f"color: {C['text']}; font-size: 20px; font-weight: 700; background: transparent;")
        layout.addWidget(self.title_lbl)

        self.sub_lbl = make_label("", 13, color=C["text2"])
        self.sub_lbl.setStyleSheet(f"color: {C['text2']}; font-style: italic; font-size: 13px; background: transparent;")
        layout.addWidget(self.sub_lbl)
        layout.addStretch(1)

        self.clock_lbl = make_label("", 12, color=C["text2"])
        self.clock_lbl.setStyleSheet(f"color: {C['text3']}; background: transparent; font-family: 'Courier New';")
        layout.addWidget(self.clock_lbl)

        self.avatar = QLabel("A")
        self.avatar.setFixedSize(34, 34)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.avatar.setStyleSheet(f"""
            background: {C['accent_dim']};
            border: 2px solid {C['accent']};
            border-radius: 17px;
            color: {C['accent_h']};
        """)
        layout.addWidget(self.avatar)

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)
        self._tick()

    def _tick(self):
        now = datetime.now().strftime("%a, %b %d  %H:%M:%S")
        self.clock_lbl.setText(now)

    def set_page(self, title, sub=""):
        self.title_lbl.setText(title)
        self.sub_lbl.setText(f"— {sub}" if sub else "")

    def set_admin(self, admin_data):
        name = admin_data.get("username", "A")
        self.avatar.setText(name[0].upper())

# ─── DASHBOARD PAGE ───────────────────────────────────────────────────────────
class DashboardPage(QWidget):
    def __init__(self, parent=None, admin_data=None):
        super().__init__(parent)
        self.admin_data = admin_data or {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Page header
        hdr = make_label("Every day is a chance to be better.", 32, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 32px; font-weight: 900; letter-spacing: 1px; background: transparent;")
        layout.addWidget(hdr)
        sub = make_label("SYSTEM STATUS: OPTIMIZED", 13, color=C["text2"])
        sub.setStyleSheet(f"color: {C['text2']}; background: transparent; margin-bottom: 4px; letter-spacing: 1px;")
        layout.addWidget(sub)

        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self.sc_checkins  = StatCard("Today's Check-ins", "—", "", "accent")
        self.sc_active    = StatCard("Active Plans", "—", "", "green")
        self.sc_revenue   = StatCard("Today's Revenue", "₱0", "", "accent")
        self.sc_lowstock  = StatCard("Low Stock Alerts", "—", "", "yellow")
        self.sc_expiring  = StatCard("Expiring Plans", "—", "", "red")
        for sc in [self.sc_checkins, self.sc_active, self.sc_revenue, self.sc_lowstock, self.sc_expiring]:
            stats_row.addWidget(sc)
        layout.addLayout(stats_row)

        # Recent check-ins table
        tbl_card = QWidget()
        tbl_card.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        tbl_v = QVBoxLayout(tbl_card)
        tbl_v.setContentsMargins(0, 0, 0, 0)
        tbl_v.setSpacing(0)

        tbl_header = QWidget()
        tbl_header.setFixedHeight(48)
        tbl_header.setStyleSheet(f"background: {C['surface2']}; border-radius: 10px 10px 0 0; border-bottom: 1px solid {C['border']};")
        th_layout = QHBoxLayout(tbl_header)
        th_layout.setContentsMargins(20, 0, 20, 0)
        th_lbl = make_label("Recent Check-ins", 14, QFont.Weight.Bold)
        th_lbl.setStyleSheet(f"color: {C['text']}; font-weight: 700; background: transparent;")
        th_layout.addWidget(th_lbl)
        th_layout.addStretch()
        tbl_v.addWidget(tbl_header)

        self.checkin_table = QTableWidget()
        self.checkin_table.setColumnCount(4)
        self.checkin_table.setHorizontalHeaderLabels(["Name", "Code", "Type", "Time"])
        self.checkin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.checkin_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.checkin_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.checkin_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.checkin_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.checkin_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.checkin_table.verticalHeader().setVisible(False)
        self.checkin_table.setShowGrid(False)
        self.checkin_table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent;
                border: none;
                border-radius: 0;
            }}
            QTableWidget::item {{ border-bottom: 1px solid {C['border']}; }}
        """)
        tbl_v.addWidget(self.checkin_table)
        layout.addWidget(tbl_card, 1)

    def refresh(self):
        try:
            from controllers.dashboard_controller import DashboardController
            data = DashboardController.get_dashboard_data()

            self.sc_checkins.set_value(data.get("today_checkins_count", 0))
            self.sc_active.set_value(data.get("active_plans_count", 0))
            rev = data.get("today_revenue", 0) or 0
            self.sc_revenue.set_value(f"₱{float(rev):,.2f}")
            self.sc_lowstock.set_value(data.get("low_stock_count", 0))
            self.sc_expiring.set_value(data.get("expiring_count", 0))

            checkins = data.get("recent_checkins", [])
            self.checkin_table.setRowCount(len(checkins))
            for i, row in enumerate(checkins):
                def ci(text, align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft):
                    item = QTableWidgetItem(str(text or "—"))
                    item.setTextAlignment(align)
                    item.setForeground(QColor(C["text"]))
                    return item
                self.checkin_table.setItem(i, 0, ci(row.get("full_name", "—")))
                code_item = QTableWidgetItem(str(row.get("customer_code", "—")))
                code_item.setForeground(QColor(C["accent_h"]))
                code_item.setFont(QFont("Courier New", 12))
                self.checkin_table.setItem(i, 1, code_item)
                checkin_type = row.get("checkin_type", row.get("type", "—"))
                self.checkin_table.setItem(i, 2, ci(checkin_type))
                ts_val = row.get("check_in_time", row.get("checkin_time", ""))
                if isinstance(ts_val, datetime):
                    time_value = ts_val.strftime("%H:%M")
                else:
                    ts_text = str(ts_val) if ts_val else ""
                    time_value = ts_text[11:16] if len(ts_text) >= 16 else "—"
                self.checkin_table.setItem(i, 3, ci(time_value))
                self.checkin_table.setRowHeight(i, 44)
        except Exception as e:
            pass

# ─── PAGE: CHECK-IN ──────────────────────────────────────────────────────────
class CheckInPage(QWidget):
    def __init__(self, admin_data=None, parent=None):
        super().__init__(parent)
        self.admin_data = admin_data or {}
        self._customer = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        hdr = make_label("CHECK-IN", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 26px; font-weight: 900; letter-spacing: 2px; background: transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label("Scan or enter customer code to check in.", 13, color=C["text2"]))

        # Input bar
        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter customer code (e.g. PLAN-001)...")
        self.code_input.setFixedHeight(52)
        self.code_input.setFont(QFont("Courier New", 15))
        self.code_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C['surface2']};
                border: 1px solid {C['border2']};
                border-radius: 10px;
                padding: 0 18px;
                color: {C['accent_h']};
                letter-spacing: 2px;
            }}
            QLineEdit:focus {{ border: 1px solid {C['accent_h']}; }}
        """)
        self.code_input.returnPressed.connect(self._validate)
        input_row.addWidget(self.code_input)

        scan_btn = make_btn("CHECK IN", "accent")
        scan_btn.setFixedHeight(52)
        scan_btn.clicked.connect(self._validate)
        input_row.addWidget(scan_btn)
        layout.addLayout(input_row)

        # Result panel
        self.result_panel = QWidget()
        self.result_panel.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        self.result_panel.hide()
        self.rp_layout = QVBoxLayout(self.result_panel)
        self.rp_layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(self.result_panel)

        # Action cards
        self.renewal_card = self._build_renewal_card()
        self.renewal_card.hide()
        layout.addWidget(self.renewal_card)

        self.noplan_card = self._build_noplan_card()
        self.noplan_card.hide()
        layout.addWidget(self.noplan_card)

        layout.addStretch()

    def _build_renewal_card(self):
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(16)

        lbl = make_label("Plan Expired — Renew Subscription", 16, QFont.Weight.Bold)
        lbl.setStyleSheet(f"color: {C['yellow']}; font-weight: 700; background: transparent;")
        v.addWidget(lbl)

        plan_row = QHBoxLayout()
        plan_row.setSpacing(12)
        self.plan_buttons_renewal = []
        try:
            from controllers.checkin_controller import CheckInController
            from models.plan import Plan
            plans = Plan.get_weekly_monthly()
        except:
            plans = []
        self._renewal_plans = plans
        for p in plans:
            pb = QPushButton(f"{p['plan_name']}\n₱{p.get('price', '?')}")
            pb.setCheckable(True)
            pb.setFixedHeight(70)
            pb.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            pb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            pb.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface2']};
                    border: 2px solid {C['border2']};
                    border-radius: 8px;
                    color: {C['text']};
                }}
                QPushButton:checked {{
                    background: {C['accent_dim']};
                    border: 2px solid {C['accent_h']};
                    color: {C['accent_h']};
                }}
                QPushButton:hover {{ border: 2px solid {C['accent']}; }}
            """)
            pb.clicked.connect(lambda _, plan=p, b=pb: self._select_plan(plan, b))
            self.plan_buttons_renewal.append((pb, p))
            plan_row.addWidget(pb)

        self._selected_plan = None
        plan_row.addStretch()
        v.addLayout(plan_row)

        pay_row = QHBoxLayout()
        pay_lbl = make_label("Payment:", 13)
        self.pay_combo = QComboBox()
        self.pay_combo.addItems(["cash", "gcash", "card"])
        self.pay_combo.setFixedWidth(140)
        pay_row.addWidget(pay_lbl)
        pay_row.addWidget(self.pay_combo)
        pay_row.addStretch()
        v.addLayout(pay_row)

        btn_row = QHBoxLayout()
        confirm_btn = make_btn("Confirm Renewal", "green")
        confirm_btn.clicked.connect(self._confirm_renewal)
        cancel_btn = make_btn("Cancel", "ghost")
        cancel_btn.clicked.connect(lambda: self.renewal_card.hide())
        btn_row.addWidget(confirm_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)
        return card

    def _build_noplan_card(self):
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(12)
        lbl = make_label("No active plan — Issue a Day Pass?", 15, QFont.Weight.Bold)
        lbl.setStyleSheet(f"color: {C['text']}; font-weight: 700; background: transparent;")
        v.addWidget(lbl)
        btn_row = QHBoxLayout()
        dp_btn = make_btn("Issue Day Pass", "accent")
        dp_btn.clicked.connect(self._issue_daypass)
        cancel_btn = make_btn("Cancel", "ghost")
        cancel_btn.clicked.connect(lambda: self.noplan_card.hide())
        btn_row.addWidget(dp_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)
        return card

    def _select_plan(self, plan, btn):
        self._selected_plan = plan
        for b, _ in self.plan_buttons_renewal:
            b.setChecked(False)
        btn.setChecked(True)

    def _clear_result(self):
        while self.rp_layout.count():
            item = self.rp_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.result_panel.hide()
        self.renewal_card.hide()
        self.noplan_card.hide()
        self._customer = None

    def _validate(self):
        code = self.code_input.text().strip()
        if not code:
            return
        self._clear_result()
        try:
            from controllers.checkin_controller import CheckInController
            ok, status, data = CheckInController.validate(code)
        except Exception as e:
            self._show_result("error", {"message": str(e)})
            return

        self._customer = data if isinstance(data, dict) else None
        self._show_result(status, data)

    def _show_result(self, status, data):
        self.result_panel.show()
        colors = {
            "active":    (C["green"],   "✓"),
            "expired":   (C["yellow"],  "⚠"),
            "no_plan":   (C["text2"],   "○"),
            "not_found": (C["red"],     "✗"),
            "error":     (C["red"],     "✗"),
        }
        color, icon = colors.get(status, (C["text2"], "○"))

        name_lbl = make_label(
            f"{icon}  {data.get('name', data.get('message', 'Unknown')) if isinstance(data, dict) else str(data)}",
            20, QFont.Weight.Bold
        )
        name_lbl.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: 800; background: transparent;")
        self.rp_layout.addWidget(name_lbl)

        if isinstance(data, dict) and status == "active":
            info_row = QHBoxLayout()
            for k, v in [("Code", data.get("code", "—")),
                          ("Plan", data.get("plan", "—")),
                          ("Expires", data.get("end_date", "—")),
                          ("Time", data.get("checkin_time", "—"))]:
                grp = QWidget()
                grp.setStyleSheet("background: transparent;")
                gv = QVBoxLayout(grp)
                gv.setSpacing(2)
                kl = QLabel(k.upper())
                kl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                kl.setStyleSheet(f"color: {C['text3']}; letter-spacing: 1px; background: transparent;")
                vl = QLabel(str(v))
                vl.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
                vl.setStyleSheet(f"color: {C['text']}; background: transparent;")
                gv.addWidget(kl)
                gv.addWidget(vl)
                info_row.addWidget(grp)
            info_row.addStretch()
            self.rp_layout.addLayout(info_row)

            badge = QLabel("  CHECK-IN RECORDED  ")
            badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            badge.setStyleSheet(f"""
                background: {C['green_dim']};
                color: {C['green']};
                border: 1px solid {C['green']};
                border-radius: 4px;
                padding: 4px 10px;
                letter-spacing: 1px;
            """)
            self.rp_layout.addWidget(badge)

        elif status == "expired":
            exp_lbl = make_label(f"Plan expired: {data.get('expired_date', '—')}", 13, color=C["text2"])
            exp_lbl.setStyleSheet(f"color: {C['text2']}; background: transparent;")
            self.rp_layout.addWidget(exp_lbl)
            self.renewal_card.show()

        elif status == "no_plan":
            msg = make_label("No active subscription found.", 13, color=C["text2"])
            msg.setStyleSheet(f"color: {C['text2']}; background: transparent;")
            self.rp_layout.addWidget(msg)
            self.noplan_card.show()

        elif status == "not_found":
            msg = make_label("Customer not found. Check the code and try again.", 13, color=C["red"])
            msg.setStyleSheet(f"color: {C['red']}; background: transparent;")
            self.rp_layout.addWidget(msg)

    def _confirm_renewal(self):
        if not self._selected_plan or not self._customer:
            QMessageBox.warning(self, "Warning", "Select a plan first.")
            return
        try:
            from controllers.checkin_controller import CheckInController
            pay = self.pay_combo.currentText()
            ok, result = CheckInController.renew_plan(
                self._customer["customer_id"],
                self._selected_plan["plan_id"],
                pay,
                self.admin_data.get("admin_id")
            )
            if ok:
                self.renewal_card.hide()
                self._clear_result()
                self.result_panel.show()
                lbl = make_label(f"✓ {self._customer.get('name','?')} — Plan Renewed", 20, QFont.Weight.Bold)
                lbl.setStyleSheet(f"color: {C['green']}; font-weight: 800; background: transparent;")
                self.rp_layout.addWidget(lbl)
                exp_lbl = make_label(f"New expiry: {result.get('end_date','—')}   Check-in: {result.get('checkin_time','—')}", 13)
                exp_lbl.setStyleSheet(f"color: {C['text2']}; background: transparent;")
                self.rp_layout.addWidget(exp_lbl)
            else:
                QMessageBox.critical(self, "Error", str(result))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _issue_daypass(self):
        if not self._customer:
            return
        try:
            from controllers.daypass_controller import DayPassController
            ok, result = DayPassController.create_daypass(
                name=self._customer.get("name", ""),
                gender="male",
                address="",
                admin_id=self.admin_data.get("admin_id")
            )
            if ok:
                self.noplan_card.hide()
                self._clear_result()
                self.result_panel.show()
                lbl = make_label(f"✓ Day Pass Issued", 20, QFont.Weight.Bold)
                lbl.setStyleSheet(f"color: {C['green']}; font-weight: 800; background: transparent;")
                self.rp_layout.addWidget(lbl)
            else:
                QMessageBox.critical(self, "Error", str(result))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh(self):
        pass

# ─── PAGE: DAY PASS ──────────────────────────────────────────────────────────
class DayPassPage(QWidget):
    def __init__(self, admin_data=None, parent=None):
        super().__init__(parent)
        self.admin_data = admin_data or {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        hdr = make_label("DAY PASS ENTRY", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 26px; font-weight: 900; letter-spacing: 2px; background: transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label("Register a single-day visitor.", 13, color=C["text2"]))

        form_card = QWidget()
        form_card.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        form_card.setMaximumWidth(600)
        fv = QVBoxLayout(form_card)
        fv.setContentsMargins(28, 28, 28, 28)
        fv.setSpacing(16)

        def field(label, widget):
            g = QWidget()
            g.setStyleSheet("background: transparent;")
            gv = QVBoxLayout(g)
            gv.setContentsMargins(0, 0, 0, 0)
            gv.setSpacing(6)
            lbl = QLabel(label.upper())
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {C['text2']}; letter-spacing: 1.5px; background: transparent;")
            gv.addWidget(lbl)
            gv.addWidget(widget)
            return g

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")
        self.name_input.setFixedHeight(40)
        fv.addWidget(field("Full Name", self.name_input))

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["male", "female"])
        self.gender_combo.setFixedHeight(40)
        fv.addWidget(field("Gender", self.gender_combo))

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Address (optional)")
        self.address_input.setFixedHeight(40)
        fv.addWidget(field("Address", self.address_input))

        self.pay_combo = QComboBox()
        self.pay_combo.addItems(["cash", "gcash", "card"])
        self.pay_combo.setFixedHeight(40)
        fv.addWidget(field("Payment Method", self.pay_combo))

        btn_row = QHBoxLayout()
        submit_btn = make_btn("Issue Day Pass", "accent")
        submit_btn.clicked.connect(self._submit)
        clear_btn = make_btn("Clear", "ghost")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(submit_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        fv.addLayout(btn_row)

        # Success panel
        self.success_panel = QWidget()
        self.success_panel.setStyleSheet(f"""
            QWidget {{
                background: {C['green_dim']};
                border: 1px solid {C['green']};
                border-radius: 10px;
            }}
        """)
        self.success_panel.hide()
        sp_v = QVBoxLayout(self.success_panel)
        sp_v.setContentsMargins(24, 20, 24, 20)
        self.success_lbl = make_label("", 16, QFont.Weight.Bold)
        self.success_lbl.setStyleSheet(f"color: {C['green']}; font-weight: 800; background: transparent;")
        sp_v.addWidget(self.success_lbl)
        self.success_detail = make_label("", 13, color=C["text2"])
        self.success_detail.setStyleSheet(f"color: {C['text2']}; background: transparent;")
        sp_v.addWidget(self.success_detail)

        layout.addWidget(form_card)
        layout.addWidget(self.success_panel)
        layout.addStretch()

    def _submit(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Please enter a name.")
            return
        try:
            from controllers.daypass_controller import DayPassController
            ok, result = DayPassController.create_daypass(
                name=name,
                gender=self.gender_combo.currentText(),
                address=self.address_input.text().strip(),
                payment_type=self.pay_combo.currentText(),
                admin_id=self.admin_data.get("admin_id")
            )
            if ok:
                c = result["customer"]
                self.success_lbl.setText(f"✓ Day Pass Issued — {c['name']}")
                self.success_detail.setText(f"Code: {c['code']}   Fee: ₱{c['fee']}   Time: {c['time']}")
                self.success_panel.show()
                self._clear_fields()
            else:
                QMessageBox.critical(self, "Error", str(result))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _clear_fields(self):
        self.name_input.clear()
        self.address_input.clear()
        self.gender_combo.setCurrentIndex(0)
        self.pay_combo.setCurrentIndex(0)

    def _clear(self):
        self._clear_fields()
        self.success_panel.hide()

    def refresh(self):
        pass

# ─── PAGE: PLAN REGISTRATION ─────────────────────────────────────────────────
class PlanRegPage(QWidget):
    def __init__(self, admin_data=None, parent=None):
        super().__init__(parent)
        self.admin_data = admin_data or {}
        self._selected_plan = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        hdr = make_label("PLAN REGISTRATION", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 26px; font-weight: 900; letter-spacing: 2px; background: transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label("Register a new member and assign a subscription plan.", 13, color=C["text2"]))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # Left: form
        form_card = QWidget()
        form_card.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        fv = QVBoxLayout(form_card)
        fv.setContentsMargins(28, 28, 28, 28)
        fv.setSpacing(14)

        form_title = make_label("Member Information", 15, QFont.Weight.Bold)
        form_title.setStyleSheet(f"color: {C['text']}; font-weight: 700; background: transparent;")
        fv.addWidget(form_title)

        def field(label, widget):
            g = QWidget()
            g.setStyleSheet("background: transparent;")
            gv = QVBoxLayout(g)
            gv.setContentsMargins(0, 0, 0, 0)
            gv.setSpacing(6)
            lbl = QLabel(label.upper())
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {C['text2']}; letter-spacing: 1.5px; background: transparent;")
            gv.addWidget(lbl)
            gv.addWidget(widget)
            return g

        self.name_input = QLineEdit(); self.name_input.setFixedHeight(40)
        self.name_input.setPlaceholderText("Full name")
        fv.addWidget(field("Full Name", self.name_input))

        self.gender_combo = QComboBox(); self.gender_combo.setFixedHeight(40)
        self.gender_combo.addItems(["male", "female"])
        fv.addWidget(field("Gender", self.gender_combo))

        self.address_input = QLineEdit(); self.address_input.setFixedHeight(40)
        self.address_input.setPlaceholderText("Address")
        fv.addWidget(field("Address", self.address_input))

        self.contact_input = QLineEdit(); self.contact_input.setFixedHeight(40)
        self.contact_input.setPlaceholderText("Phone / contact info")
        fv.addWidget(field("Contact", self.contact_input))

        self.reg_pay_combo = QComboBox(); self.reg_pay_combo.setFixedHeight(40)
        self.reg_pay_combo.addItems(["cash", "gcash", "card"])
        fv.addWidget(field("Payment Method", self.reg_pay_combo))

        fv.addStretch()

        btn_row = QHBoxLayout()
        register_btn = make_btn("Register Member", "accent")
        register_btn.clicked.connect(self._submit)
        clear_btn = make_btn("Clear", "ghost")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(register_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        fv.addLayout(btn_row)

        # Right: plan selection
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(20, 0, 0, 0)
        rv.setSpacing(14)

        plan_title = make_label("Select Plan", 15, QFont.Weight.Bold)
        plan_title.setStyleSheet(f"color: {C['text']}; font-weight: 700; background: transparent;")
        rv.addWidget(plan_title)

        self.plan_buttons = []
        try:
            from controllers.planreg_controller import PlanRegController
            plans = PlanRegController.get_plans()
        except:
            plans = []

        for p in plans:
            pb = QPushButton()
            pb.setCheckable(True)
            pb.setFixedHeight(90)
            pb.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            pb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            pn = p.get("plan_name", "Plan")
            dd = p.get("duration_days", 0)
            pb.setText(f"{pn} Plan\n{dd} days")
            pb.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface2']};
                    border: 2px solid {C['border2']};
                    border-radius: 10px;
                    color: {C['text']};
                    text-align: center;
                }}
                QPushButton:checked {{
                    background: {C['accent_dim']};
                    border: 2px solid {C['accent_h']};
                    color: {C['accent_h']};
                }}
                QPushButton:hover {{ border: 2px solid {C['accent']}; }}
            """)
            pb.clicked.connect(lambda _, plan=p, b=pb: self._select_plan(plan, b))
            self.plan_buttons.append((pb, p))
            rv.addWidget(pb)

        rv.addStretch()

        # Success panel
        self.success_panel = QWidget()
        self.success_panel.setStyleSheet(f"""
            QWidget {{
                background: {C['green_dim']};
                border: 1px solid {C['green']};
                border-radius: 10px;
            }}
        """)
        self.success_panel.hide()
        sp_v = QVBoxLayout(self.success_panel)
        sp_v.setContentsMargins(24, 20, 24, 20)
        self.success_lbl = make_label("", 16, QFont.Weight.Bold)
        self.success_lbl.setStyleSheet(f"color: {C['green']}; font-weight: 800; background: transparent;")
        sp_v.addWidget(self.success_lbl)
        self.success_detail = make_label("", 13, color=C["text2"])
        self.success_detail.setStyleSheet(f"color: {C['text2']}; background: transparent;")
        sp_v.addWidget(self.success_detail)
        rv.addWidget(self.success_panel)

        splitter.addWidget(form_card)
        splitter.addWidget(right)
        splitter.setSizes([480, 320])

        layout.addWidget(splitter, 1)

    def _select_plan(self, plan, btn):
        self._selected_plan = plan
        for b, _ in self.plan_buttons:
            b.setChecked(False)
        btn.setChecked(True)

    def _submit(self):
        if not self._selected_plan:
            QMessageBox.warning(self, "Validation", "Please select a plan.")
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Please enter a name.")
            return
        try:
            from controllers.planreg_controller import PlanRegController
            ok, result = PlanRegController.register_plan(
                name=name,
                gender=self.gender_combo.currentText(),
                address=self.address_input.text().strip(),
                contact_info=self.contact_input.text().strip(),
                plan_id=self._selected_plan["plan_id"],
                payment_type=self.reg_pay_combo.currentText(),
                admin_id=self.admin_data.get("admin_id")
            )
            if ok:
                self.success_lbl.setText(f"✓ {result['customer_name']} Registered!")
                self.success_detail.setText(
                    f"Code: {result['customer_code']}   Plan: {result['plan_name']}   "
                    f"Expires: {result['end_date']}   Paid: ₱{result['price']}"
                )
                self.success_panel.show()
                self._clear()
            else:
                QMessageBox.critical(self, "Error", str(result))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _clear(self):
        self.name_input.clear()
        self.address_input.clear()
        self.contact_input.clear()
        self.gender_combo.setCurrentIndex(0)
        self.reg_pay_combo.setCurrentIndex(0)
        self._selected_plan = None
        for b, _ in self.plan_buttons:
            b.setChecked(False)
        self.success_panel.hide()

    def refresh(self):
        pass

# ─── PAGE: CUSTOMERS ─────────────────────────────────────────────────────────
class CustomersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        hdr = make_label("CUSTOMERS", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 26px; font-weight: 900; letter-spacing: 2px; background: transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label("All registered gym members and visitors.", 13, color=C["text2"]))

        # Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or code...")
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self._filter)
        search_row.addWidget(self.search_input)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "plan", "day-pass"])
        self.type_filter.setFixedHeight(40)
        self.type_filter.setFixedWidth(150)
        self.type_filter.currentTextChanged.connect(self._filter)
        search_row.addWidget(self.type_filter)
        layout.addLayout(search_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Code", "Name", "Gender", "Type", "Status", "Actions"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)       # Code — fixed width
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)     # Name — takes remaining space
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)       # Gender
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)       # Type
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)       # Status
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)       # Actions — fixed so button fits
        self.table.setColumnWidth(0, 140)   # Code: e.g. "DAY-00009" fits fully
        self.table.setColumnWidth(2, 80)    # Gender
        self.table.setColumnWidth(3, 90)    # Type
        self.table.setColumnWidth(4, 80)    # Status
        self.table.setColumnWidth(5, 110)   # Actions: enough for Delete button
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

        self._all_customers = []

    def refresh(self):
        try:
            from controllers.customer_controller import CustomerController
            self._all_customers = CustomerController.get_all() or []
            self._populate(self._all_customers)
        except Exception as e:
            pass

    def _filter(self):
        q = self.search_input.text().lower()
        t = self.type_filter.currentText()
        filtered = [c for c in self._all_customers
                    if (q in str(c.get("full_name","")).lower() or q in str(c.get("customer_code","")).lower())
                    and (t == "All Types" or c.get("customer_type") == t)]
        self._populate(filtered)

    def _populate(self, customers):
        self.table.setRowCount(len(customers))
        for i, c in enumerate(customers):
            code_item = QTableWidgetItem(str(c.get("customer_code", "—")))
            code_item.setForeground(QColor(C["accent_h"]))
            code_item.setFont(QFont("Courier New", 12))
            self.table.setItem(i, 0, code_item)

            def ci(text):
                item = QTableWidgetItem(str(text or "—"))
                item.setForeground(QColor(C["text"]))
                return item

            self.table.setItem(i, 1, ci(c.get("full_name")))
            self.table.setItem(i, 2, ci(c.get("gender")))
            self.table.setItem(i, 3, ci(c.get("customer_type")))

            status = "Active" if c.get("has_active_sub") else ("Expired" if c.get("customer_type") == "plan" else "—")
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(C["green"] if status == "Active" else C["red"] if status == "Expired" else C["text3"]))
            self.table.setItem(i, 4, status_item)

            # Action buttons cell
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            ah = QHBoxLayout(action_widget)
            ah.setContentsMargins(4, 4, 4, 4)
            ah.setSpacing(6)

            del_btn = make_btn("Delete", "red")
            del_btn.setFixedHeight(30)
            del_btn.setFixedWidth(90)
            del_btn.setFont(QFont("Segoe UI", 10))
            cid = c.get("customer_id")
            del_btn.clicked.connect(lambda _, id=cid: self._delete(id))
            ah.addWidget(del_btn)
            self.table.setCellWidget(i, 5, action_widget)
            self.table.setRowHeight(i, 46)

    def _delete(self, customer_id):
        reply = QMessageBox.question(self, "Confirm Delete",
                                      "Move this customer to Recycle Bin?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from controllers.customer_controller import CustomerController
                CustomerController.soft_delete(customer_id)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

# ─── PAGE: PRODUCTS ──────────────────────────────────────────────────────────
class ProductsPage(QWidget):
    def __init__(self, admin_data=None, parent=None):
        super().__init__(parent)
        self.admin_data = admin_data or {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        hdr = make_label("PRODUCTS", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 26px; font-weight: 900; letter-spacing: 2px; background: transparent;")
        top_row.addWidget(hdr)
        top_row.addStretch()
        add_btn = make_btn("+ Add Product", "accent")
        add_btn.clicked.connect(self._add_product)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["SKU", "Product Name", "Category", "Price", "Stock", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(5, 180)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

    def refresh(self):
        try:
            from controllers.inventory_controller import InventoryController
            products = InventoryController.get_all() or []
            self.table.setRowCount(len(products))
            for i, p in enumerate(products):
                def ci(text, color=None):
                    item = QTableWidgetItem(str(text or "—"))
                    item.setForeground(QColor(color or C["text"]))
                    return item

                self.table.setItem(i, 0, ci(p.get("sku"), C["text3"]))
                self.table.setItem(i, 1, ci(p.get("product_name")))
                self.table.setItem(i, 2, ci(p.get("category")))
                price_item = QTableWidgetItem(f"₱{float(p.get('price',0)):,.2f}")
                price_item.setForeground(QColor(C["accent_h"]))
                self.table.setItem(i, 3, price_item)

                stock = p.get("stock", 0)
                stock_color = C["green"] if stock > 10 else C["yellow"] if stock > 0 else C["red"]
                self.table.setItem(i, 4, ci(stock, stock_color))

                aw = QWidget(); aw.setStyleSheet("background: transparent;")
                ah = QHBoxLayout(aw); ah.setContentsMargins(4,4,4,4); ah.setSpacing(6)

                restock_btn = make_btn("Restock", "ghost")
                restock_btn.setFixedHeight(30); restock_btn.setMinimumWidth(80); restock_btn.setFont(QFont("Segoe UI", 10))
                pid = p.get("product_id")
                restock_btn.clicked.connect(lambda _, id=pid: self._restock(id))

                del_btn = make_btn("Delete", "red")
                del_btn.setFixedHeight(30); del_btn.setMinimumWidth(80); del_btn.setFont(QFont("Segoe UI", 10))
                del_btn.clicked.connect(lambda _, id=pid: self._delete(id))

                ah.addWidget(restock_btn); ah.addWidget(del_btn); ah.addStretch()
                self.table.setCellWidget(i, 5, aw)
                self.table.setRowHeight(i, 46)
        except Exception as e:
            pass

    def _add_product(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Product")
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet(f"background: {C['surface']}; color: {C['text']};")
        v = QVBoxLayout(dialog)
        v.setContentsMargins(28,28,28,28); v.setSpacing(14)

        v.addWidget(make_label("Add New Product", 16, QFont.Weight.Bold))

        def fld(label, w):
            g = QWidget(); g.setStyleSheet("background:transparent;")
            gv = QVBoxLayout(g); gv.setContentsMargins(0,0,0,0); gv.setSpacing(4)
            lbl = QLabel(label.upper()); lbl.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{C['text2']};background:transparent;letter-spacing:1px;")
            gv.addWidget(lbl); gv.addWidget(w); return g

        sku_e = QLineEdit(); sku_e.setFixedHeight(38); sku_e.setPlaceholderText("e.g. WHEY-001")
        name_e = QLineEdit(); name_e.setFixedHeight(38); name_e.setPlaceholderText("Product name")
        cat_e = QComboBox(); cat_e.setFixedHeight(38)
        cat_e.addItems(["Supplements","Accessories","Equipment","Beverages","Others"])
        price_e = QDoubleSpinBox(); price_e.setFixedHeight(38); price_e.setPrefix("₱ ")
        price_e.setMaximum(99999); price_e.setDecimals(2)
        stock_e = QSpinBox(); stock_e.setFixedHeight(38); stock_e.setMaximum(99999)

        v.addWidget(fld("SKU", sku_e))
        v.addWidget(fld("Product Name", name_e))
        v.addWidget(fld("Category", cat_e))
        v.addWidget(fld("Price", price_e))
        v.addWidget(fld("Initial Stock", stock_e))

        btn_row = QHBoxLayout()
        ok_btn = make_btn("Add Product", "accent"); cancel_btn = make_btn("Cancel", "ghost")
        btn_row.addWidget(ok_btn); btn_row.addWidget(cancel_btn); btn_row.addStretch()

        def do_add():
            try:
                from controllers.inventory_controller import InventoryController
                ok, r = InventoryController.create(
                    sku_e.text().strip(), name_e.text().strip(),
                    cat_e.currentText(), price_e.value(), stock_e.value()
                )
                if ok:
                    dialog.accept(); self.refresh()
                else:
                    QMessageBox.critical(dialog, "Error", str(r))
            except Exception as e:
                QMessageBox.critical(dialog, "Error", str(e))

        ok_btn.clicked.connect(do_add)
        cancel_btn.clicked.connect(dialog.reject)
        v.addLayout(btn_row)
        dialog.exec()

    def _restock(self, product_id):
        qty, ok = self._ask_int("Restock", "Quantity to add:", 1, 9999)
        if ok and qty > 0:
            try:
                from controllers.restock_controller import RestockController
                RestockController.restock(product_id, qty)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete(self, product_id):
        reply = QMessageBox.question(self, "Confirm", "Move to Recycle Bin?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from controllers.inventory_controller import InventoryController
                InventoryController.soft_delete(product_id)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _ask_int(self, title, label, min_val, max_val):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setStyleSheet(f"background: {C['surface']}; color: {C['text']};")
        v = QVBoxLayout(dialog)
        v.setContentsMargins(24,24,24,24); v.setSpacing(14)
        v.addWidget(make_label(label, 13))
        spin = QSpinBox(); spin.setMinimum(min_val); spin.setMaximum(max_val); spin.setFixedHeight(38)
        v.addWidget(spin)
        btn_row = QHBoxLayout()
        ok_btn = make_btn("Confirm", "green"); cancel_btn = make_btn("Cancel", "ghost")
        result = [0, False]

        def do_ok():
            result[0] = spin.value(); result[1] = True; dialog.accept()

        ok_btn.clicked.connect(do_ok); cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn); btn_row.addWidget(cancel_btn)
        v.addLayout(btn_row)
        dialog.exec()
        return result[0], result[1]

# ─── PAGE: SALES ─────────────────────────────────────────────────────────────
class SalesPage(QWidget):
    def __init__(self, admin_data=None, parent=None):
        super().__init__(parent)
        self.admin_data = admin_data or {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        hdr = make_label("SALES", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 26px; font-weight: 900; letter-spacing: 2px; background: transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label("Record product transactions.", 13, color=C["text2"]))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # Products grid
        left = QWidget(); left.setStyleSheet("background:transparent;")
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(10)
        lv.addWidget(make_label("Products", 15, QFont.Weight.Bold))

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        self.prod_container = QWidget(); self.prod_container.setStyleSheet("background:transparent;")
        self.prod_grid = QGridLayout(self.prod_container)
        self.prod_grid.setSpacing(12)
        scroll.setWidget(self.prod_container)
        lv.addWidget(scroll)

        # Recent sales
        right = QWidget(); right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right); rv.setContentsMargins(20,0,0,0); rv.setSpacing(10)
        rv.addWidget(make_label("Recent Sales", 15, QFont.Weight.Bold))

        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(4)
        self.sales_table.setHorizontalHeaderLabels(["Product","Qty","Total","Date"])
        self.sales_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sales_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sales_table.verticalHeader().setVisible(False)
        self.sales_table.setShowGrid(False)
        rv.addWidget(self.sales_table)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([500, 380])
        layout.addWidget(splitter, 1)

    def refresh(self):
        try:
            from controllers.inventory_controller import InventoryController
            from controllers.product_sales_controller import ProductSalesController
            products = InventoryController.get_all() or []
            sales = ProductSalesController.get_recent(20) or []

            # Clear grid
            for i in reversed(range(self.prod_grid.count())):
                w = self.prod_grid.itemAt(i).widget()
                if w: w.deleteLater()

            cols = 2
            for idx, p in enumerate(products):
                card = self._make_product_card(p)
                self.prod_grid.addWidget(card, idx // cols, idx % cols)

            # Sales table
            self.sales_table.setRowCount(len(sales))
            for i, s in enumerate(sales):
                def ci(text, color=None):
                    item = QTableWidgetItem(str(text or "—"))
                    item.setForeground(QColor(color or C["text"]))
                    return item
                self.sales_table.setItem(i, 0, ci(s.get("product_name")))
                self.sales_table.setItem(i, 1, ci(s.get("quantity")))
                total_item = QTableWidgetItem(f"₱{float(s.get('total_amount',0)):,.2f}")
                total_item.setForeground(QColor(C["accent_h"]))
                self.sales_table.setItem(i, 2, total_item)
                self.sales_table.setItem(i, 3, ci(str(s.get("sale_date",""))[:10]))
                self.sales_table.setRowHeight(i, 42)
        except Exception as e:
            pass

    def _make_product_card(self, p):
        card = QWidget()
        stock = p.get("stock", 0)
        is_out = stock <= 0
        card.setStyleSheet(f"""
            QWidget {{
                background: {C['surface2']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(16, 14, 16, 14)
        cv.setSpacing(6)

        cat = QLabel(str(p.get("category","—")))
        cat.setFont(QFont("Segoe UI", 10))
        cat.setStyleSheet(f"color:{C['text3']}; background:transparent;")
        cv.addWidget(cat)

        name = QLabel(str(p.get("product_name","—")))
        name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{C['text']}; background:transparent;")
        cv.addWidget(name)

        price = QLabel(f"₱{float(p.get('price',0)):,.2f}")
        price.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        price.setStyleSheet(f"color:{C['accent_h']}; background:transparent;")
        cv.addWidget(price)

        foot_row = QHBoxLayout()
        stock_lbl = QLabel(f"{'⚠' if 0<stock<=10 else '✗' if is_out else '✓'} {stock} units")
        stock_color = C["red"] if is_out else C["yellow"] if stock <= 10 else C["green"]
        stock_lbl.setStyleSheet(f"color:{stock_color}; background:transparent; font-size:11px; font-weight:600;")
        foot_row.addWidget(stock_lbl)
        foot_row.addStretch()

        sell_btn = make_btn("Sell", "accent")
        sell_btn.setFixedHeight(32)
        sell_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        sell_btn.setEnabled(not is_out)
        pid = p.get("product_id")
        pstock = stock
        sell_btn.clicked.connect(lambda _, id=pid, s=pstock, pr=float(p.get('price',0)), pn=p.get('product_name',''): self._sell(id, s, pr, pn))
        foot_row.addWidget(sell_btn)
        cv.addLayout(foot_row)
        return card

    def _sell(self, product_id, stock, price, name):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Sell — {name}")
        dialog.setStyleSheet(f"background:{C['surface']};color:{C['text']};")
        v = QVBoxLayout(dialog); v.setContentsMargins(28,28,28,28); v.setSpacing(16)
        v.addWidget(make_label(f"Sell: {name}", 16, QFont.Weight.Bold))
        v.addWidget(make_label(f"Available stock: {stock} units @ ₱{price:,.2f}", 12, color=C["text2"]))

        spin = QSpinBox(); spin.setMinimum(1); spin.setMaximum(stock); spin.setFixedHeight(40)
        v.addWidget(make_label("Quantity", 11))
        v.addWidget(spin)

        total_lbl = make_label(f"Total: ₱{price:,.2f}", 18, QFont.Weight.Bold)
        total_lbl.setStyleSheet(f"color:{C['accent_h']};font-size:18px;font-weight:800;background:transparent;")
        spin.valueChanged.connect(lambda val: total_lbl.setText(f"Total: ₱{val*price:,.2f}"))
        v.addWidget(total_lbl)

        btn_row = QHBoxLayout()
        ok_btn = make_btn("Complete Sale", "accent"); cancel_btn = make_btn("Cancel", "ghost")

        def do_sell():
            try:
                from controllers.product_sales_controller import ProductSalesController
                ok, r = ProductSalesController.sell_product(product_id, spin.value())
                if ok:
                    dialog.accept(); self.refresh()
                else:
                    QMessageBox.critical(dialog, "Error", str(r))
            except Exception as e:
                QMessageBox.critical(dialog, "Error", str(e))

        ok_btn.clicked.connect(do_sell); cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn); btn_row.addWidget(cancel_btn)
        v.addLayout(btn_row)
        dialog.exec()

# ─── PAGE: RESTOCK ───────────────────────────────────────────────────────────
class RestockPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        hdr = make_label("RESTOCK", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color: {C['text']}; font-size: 26px; font-weight: 900; letter-spacing: 2px; background: transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label("Update product stock levels.", 13, color=C["text2"]))

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Product", "Category", "Stock", "Status", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

    def refresh(self):
        try:
            from controllers.inventory_controller import InventoryController
            products = InventoryController.get_all() or []
            self.table.setRowCount(len(products))
            for i, p in enumerate(products):
                def ci(text, color=None):
                    item = QTableWidgetItem(str(text or "—"))
                    item.setForeground(QColor(color or C["text"]))
                    return item

                self.table.setItem(i, 0, ci(p.get("product_name")))
                self.table.setItem(i, 1, ci(p.get("category")))
                stock = p.get("stock", 0)
                stock_color = C["green"] if stock > 10 else C["yellow"] if stock > 0 else C["red"]
                self.table.setItem(i, 2, ci(stock, stock_color))

                status = "OK" if stock > 10 else "LOW" if stock > 0 else "OUT"
                s_color = C["green"] if status == "OK" else C["yellow"] if status == "LOW" else C["red"]
                s_item = QTableWidgetItem(status)
                s_item.setForeground(QColor(s_color))
                self.table.setItem(i, 3, s_item)

                aw = QWidget(); aw.setStyleSheet("background:transparent;")
                ah = QHBoxLayout(aw); ah.setContentsMargins(4,4,4,4)
                btn = make_btn("Restock", "ghost"); btn.setFixedHeight(30); btn.setFont(QFont("Segoe UI",10))
                pid = p.get("product_id")
                btn.clicked.connect(lambda _, id=pid: self._restock(id))
                ah.addWidget(btn); ah.addStretch()
                self.table.setCellWidget(i, 4, aw)
                self.table.setRowHeight(i, 46)
        except Exception:
            pass

    def _restock(self, product_id):
        dialog = QDialog(self)
        dialog.setWindowTitle("Restock Product")
        dialog.setStyleSheet(f"background:{C['surface']};color:{C['text']};")
        v = QVBoxLayout(dialog); v.setContentsMargins(24,24,24,24); v.setSpacing(14)
        v.addWidget(make_label("Enter quantity to add:", 13))
        spin = QSpinBox(); spin.setMinimum(1); spin.setMaximum(9999); spin.setFixedHeight(40)
        v.addWidget(spin)
        btn_row = QHBoxLayout()
        ok_btn = make_btn("Confirm", "green"); cancel_btn = make_btn("Cancel", "ghost")

        def do_restock():
            try:
                from controllers.restock_controller import RestockController
                RestockController.restock(product_id, spin.value())
                dialog.accept(); self.refresh()
            except Exception as e:
                QMessageBox.critical(dialog, "Error", str(e))

        ok_btn.clicked.connect(do_restock); cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn); btn_row.addWidget(cancel_btn)
        v.addLayout(btn_row)
        dialog.exec()

# ─── PAGE: REPORTS ───────────────────────────────────────────────────────────
class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left nav
        nav = QWidget()
        nav.setFixedWidth(220)
        nav.setStyleSheet(f"""
            QWidget {{
                background: {C['surface']};
                border-right: 1px solid {C['border']};
            }}
        """)
        nv = QVBoxLayout(nav)
        nv.setContentsMargins(0, 20, 0, 20)
        nv.setSpacing(2)

        nv.addWidget(make_label("Reports", 15, QFont.Weight.Bold).also(lambda l: l.setStyleSheet(f"color:{C['text']};font-weight:700;padding:0 18px 12px 18px;background:transparent;")))

        self._report_tabs = {
            "attendance": "Daily Attendance",
            "daypass": "Day Pass Records",
            "plans": "Plan Subscribers",
            "income": "Income Overview",
            "sales": "Product Sales",
            "frequent": "Top Customers",
        }
        self._tab_btns = {}
        self._current_tab = "attendance"

        for key, label in self._report_tabs.items():
            btn = QPushButton(label)
            btn.setFixedHeight(40)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFont(QFont("Segoe UI", 12))
            btn.setCheckable(True)
            btn.setStyleSheet(self._tab_qss(False))
            btn.clicked.connect(lambda _, k=key: self._switch_tab(k))
            self._tab_btns[key] = btn
            nv.addWidget(btn)

        nv.addStretch()
        layout.addWidget(nav)

        # Content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;border:none;")
        self.content = QWidget()
        self.content.setStyleSheet("background:transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(32, 28, 32, 28)
        scroll.setWidget(self.content)
        layout.addWidget(scroll, 1)

        self._switch_tab("attendance")

    def _tab_qss(self, active):
        if active:
            return f"""QPushButton {{
                background:{C['accent_dim']}; color:{C['accent_h']};
                border:none; border-left:3px solid {C['accent_h']};
                border-radius:0; text-align:left; padding:0 18px;
                font-weight:600;
            }}"""
        return f"""QPushButton {{
            background:transparent; color:{C['text2']};
            border:none; text-align:left; padding:0 18px;
        }}
        QPushButton:hover {{ background:rgba(26,86,219,.12); color:{C['text']}; }}"""

    def _switch_tab(self, key):
        for k, b in self._tab_btns.items():
            b.setStyleSheet(self._tab_qss(k == key))
            b.setChecked(k == key)
        self._current_tab = key
        self._render_tab(key)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _render_tab(self, key):
        self._clear_content()
        title = self._report_tabs.get(key, key)

        hdr = make_label(title.upper(), 22, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color:{C['text']};font-size:22px;font-weight:900;letter-spacing:2px;background:transparent;")
        self.content_layout.addWidget(hdr)
        self.content_layout.addSpacing(12)

        try:
            if key == "attendance":
                self._render_attendance()
            elif key == "daypass":
                self._render_table_generic("Day Pass Records", ["Date","Code","Name","Fee"], self._get_daypass_rows())
            elif key == "plans":
                self._render_table_generic("Plan Subscribers", ["Code","Name","Plan","Start","End","Status"], self._get_plan_rows())
            elif key == "income":
                self._render_income()
            elif key == "sales":
                self._render_table_generic("Product Sales", ["Product","Qty","Total","Date"], self._get_sales_rows())
            elif key == "frequent":
                self._render_table_generic("Top Customers", ["Code","Name","Visits"], self._get_frequent_rows())
        except Exception as e:
            self.content_layout.addWidget(make_label(f"Error loading report: {e}", 12, color=C["red"]))

        self.content_layout.addStretch()

    def _render_attendance(self):
        try:
            from models.checkin import CheckIn
            checkins = CheckIn.get_recent(limit=50) or []
        except:
            checkins = []

        from datetime import date
        today_str = date.today().strftime("%Y-%m-%d")
        today_count = sum(1 for c in checkins if str(c.get("check_in_time", c.get("checkin_time", ""))).startswith(today_str))

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        stats_row.addWidget(StatCard("Total Records", len(checkins)))
        stats_row.addWidget(StatCard("Today", today_count, color="green"))
        stats_row.addStretch()
        self.content_layout.addLayout(stats_row)
        self.content_layout.addSpacing(16)

        rows = []
        for c in checkins[:30]:
            ts_val = c.get("check_in_time", c.get("checkin_time", ""))
            if isinstance(ts_val, datetime):
                date_str = ts_val.strftime("%Y-%m-%d")
                time_str = ts_val.strftime("%H:%M")
            else:
                ts_text = str(ts_val) if ts_val else ""
                date_str = ts_text[:10] if len(ts_text) >= 10 else "—"
                time_str = ts_text[11:16] if len(ts_text) >= 16 else "—"
            rows.append([date_str, str(c.get("customer_code","—")),
                          str(c.get("full_name","—")), time_str, str(c.get("checkin_type","—"))])
        self._render_table_generic("", ["Date","Code","Name","Time","Type"], rows)

    def _get_daypass_rows(self):
        try:
            from models.checkin import CheckIn
            data = CheckIn.get_recent(50) or []
            rows = []
            for c in data:
                if c.get("checkin_type") != "day-pass":
                    continue
                ts_val = c.get("check_in_time", c.get("checkin_time", ""))
                if isinstance(ts_val, datetime):
                    date_str = ts_val.strftime("%Y-%m-%d")
                else:
                    ts_text = str(ts_val) if ts_val else ""
                    date_str = ts_text[:10] if len(ts_text) >= 10 else "—"
                rows.append([date_str, str(c.get("customer_code","—")),
                              str(c.get("full_name","—")), "—"])
            return rows
        except: return []

    def _get_plan_rows(self):
        try:
            from models.subscription import Subscription
            subs = Subscription.get_all() or []
            rows = []
            for s in subs:
                status = "ACTIVE" if s.get("status") == "active" else "EXPIRED"
                rows.append([str(s.get("customer_code","—")), str(s.get("full_name","—")),
                              str(s.get("plan_name","—")), str(s.get("start_date","—")),
                              str(s.get("end_date","—")), status])
            return rows
        except: return []

    def _render_income(self):
        try:
            from models.payment import Payment
            from models.product_sales import ProductSale
            payments = Payment.get_all() or []
            sales = ProductSale.get_recent(999) or []

            total_rev = sum(float(p.get("amount",0)) for p in payments)
            from datetime import date
            today = date.today().strftime("%Y-%m-%d")
            today_rev = sum(float(p.get("amount",0)) for p in payments if str(p.get("payment_date","")).startswith(today))
            sales_rev = sum(float(s.get("total_amount",0)) for s in sales)

            stats_row = QHBoxLayout(); stats_row.setSpacing(12)
            stats_row.addWidget(StatCard("Total Revenue", f"₱{total_rev:,.2f}", color="green"))
            stats_row.addWidget(StatCard("Today's Revenue", f"₱{today_rev:,.2f}", color="accent"))
            stats_row.addWidget(StatCard("Product Sales", f"₱{sales_rev:,.2f}", color="accent"))
            stats_row.addStretch()
            self.content_layout.addLayout(stats_row)
        except Exception as e:
            self.content_layout.addWidget(make_label(f"Error: {e}", 12, color=C["red"]))

    def _get_sales_rows(self):
        try:
            from controllers.product_sales_controller import ProductSalesController
            sales = ProductSalesController.get_recent(30) or []
            return [[str(s.get("product_name","—")), str(s.get("quantity","—")),
                      f"₱{float(s.get('total_amount',0)):,.2f}", str(s.get("sale_date",""))[:10]] for s in sales]
        except: return []

    def _get_frequent_rows(self):
        try:
            from models.checkin import CheckIn
            checkins = CheckIn.get_recent(999) or []
            from collections import Counter
            counts = Counter()
            names = {}
            for c in checkins:
                cid = c.get("customer_id")
                counts[cid] += 1
                names[cid] = (c.get("customer_code","—"), c.get("full_name","—"))
            return [[names[k][0], names[k][1], str(v)] for k, v in counts.most_common(20)]
        except: return []

    def _render_table_generic(self, title, headers, rows):
        if title:
            lbl = make_label(title, 14, QFont.Weight.Bold)
            lbl.setStyleSheet(f"color:{C['text']};font-weight:700;background:transparent;margin-bottom:8px;")
            self.content_layout.addWidget(lbl)

        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False)
        tbl.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                item = QTableWidgetItem(str(cell))
                item.setForeground(QColor(C["text"]))
                tbl.setItem(i, j, item)
            tbl.setRowHeight(i, 42)
        self.content_layout.addWidget(tbl)

    def refresh(self):
        self._render_tab(self._current_tab)


# ─── PAGE: AUDIT LOG ─────────────────────────────────────────────────────────
class AuditLogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        hdr = make_label("AUDIT LOG", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color:{C['text']};font-size:26px;font-weight:900;letter-spacing:2px;background:transparent;")
        layout.addWidget(hdr)
        notice = QLabel("  READ ONLY — System Activity Trail")
        notice.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        notice.setStyleSheet(f"background:{C['accent_dim']};color:{C['accent_h']};border-radius:4px;padding:4px 10px;letter-spacing:1px;")
        layout.addWidget(notice)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Action", "Table", "Record ID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

    def refresh(self):
        try:
            from controllers.audit_log import AuditLogController
            logs = AuditLogController.get_recent(100) or []
        except:
            try:
                from models.audit_log import AuditLog
                logs = AuditLog.get_recent(100) or []
            except:
                logs = []

        self.table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            def ci(text, color=None):
                item = QTableWidgetItem(str(text or "—"))
                item.setForeground(QColor(color or C["text"]))
                return item

            ts = str(log.get("created_at", log.get("timestamp", "—")))
            self.table.setItem(i, 0, ci(ts[:19]))
            action_item = QTableWidgetItem(str(log.get("action","—")))
            action_item.setForeground(QColor(C["accent_h"]))
            action_item.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            self.table.setItem(i, 1, action_item)
            self.table.setItem(i, 2, ci(log.get("table_name")))
            self.table.setItem(i, 3, ci(log.get("record_id")))
            self.table.setRowHeight(i, 40)

# ─── PAGE: SETTINGS ──────────────────────────────────────────────────────────
class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")

        container = QWidget(); container.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        cv = QVBoxLayout(container)
        cv.setContentsMargins(32, 28, 32, 28)
        cv.setSpacing(20)

        hdr = make_label("SETTINGS", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color:{C['text']};font-size:26px;font-weight:900;letter-spacing:2px;background:transparent;")
        cv.addWidget(hdr)

        row = QHBoxLayout(); row.setSpacing(20)

        def section(title, fields_fn):
            card = card_widget(10)
            v = QVBoxLayout(card); v.setContentsMargins(28,24,28,24); v.setSpacing(14)
            t = make_label(title, 15, QFont.Weight.Bold)
            t.setStyleSheet(f"color:{C['text']};font-weight:700;background:transparent;")
            v.addWidget(t)
            fields_fn(v)
            return card

        def fld(parent_layout, label, widget):
            g = QWidget(); g.setStyleSheet("background:transparent;")
            gv = QVBoxLayout(g); gv.setContentsMargins(0,0,0,0); gv.setSpacing(4)
            lbl = QLabel(label.upper()); lbl.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{C['text2']};background:transparent;letter-spacing:1px;")
            gv.addWidget(lbl); gv.addWidget(widget)
            parent_layout.addWidget(g)

        # Left column
        left = QWidget(); left.setStyleSheet("background:transparent;")
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(16)

        def gym_info_section(v):
            self.gym_name = QLineEdit(); self.gym_name.setFixedHeight(38)
            self.gym_addr = QLineEdit(); self.gym_addr.setFixedHeight(38)
            self.gym_contact = QLineEdit(); self.gym_contact.setFixedHeight(38)
            self.gym_email = QLineEdit(); self.gym_email.setFixedHeight(38)
            fld(v, "Gym Name", self.gym_name)
            fld(v, "Address", self.gym_addr)
            fld(v, "Contact", self.gym_contact)
            fld(v, "Email", self.gym_email)
            sb = make_btn("Save Gym Info", "accent"); sb.clicked.connect(self._save_gym_info)
            v.addWidget(sb)

        def pricing_section(v):
            self.dp_fee = QDoubleSpinBox(); self.dp_fee.setFixedHeight(38)
            self.dp_fee.setPrefix("₱ "); self.dp_fee.setMaximum(9999); self.dp_fee.setDecimals(2)
            self.weekly_price = QDoubleSpinBox(); self.weekly_price.setFixedHeight(38)
            self.weekly_price.setPrefix("₱ "); self.weekly_price.setMaximum(9999); self.weekly_price.setDecimals(2)
            self.monthly_price = QDoubleSpinBox(); self.monthly_price.setFixedHeight(38)
            self.monthly_price.setPrefix("₱ "); self.monthly_price.setMaximum(9999); self.monthly_price.setDecimals(2)
            fld(v, "Day Pass Fee", self.dp_fee)
            fld(v, "Weekly Plan Price", self.weekly_price)
            fld(v, "Monthly Plan Price", self.monthly_price)
            sb = make_btn("Save Pricing", "accent"); sb.clicked.connect(self._save_pricing)
            v.addWidget(sb)

        lv.addWidget(section("Gym Information", gym_info_section))
        lv.addWidget(section("Pricing", pricing_section))

        # Right column
        right = QWidget(); right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(16)

        def alerts_section(v):
            self.low_stock_thresh = QSpinBox(); self.low_stock_thresh.setFixedHeight(38)
            self.low_stock_thresh.setMinimum(1); self.low_stock_thresh.setMaximum(999)
            self.exp_plan_days = QSpinBox(); self.exp_plan_days.setFixedHeight(38)
            self.exp_plan_days.setMinimum(1); self.exp_plan_days.setMaximum(90)
            fld(v, "Low Stock Threshold", self.low_stock_thresh)
            fld(v, "Expiring Plan Warning (days)", self.exp_plan_days)
            sb = make_btn("Save Alert Preferences", "accent"); sb.clicked.connect(self._save_alerts)
            v.addWidget(sb)

        rv.addWidget(section("Alert Preferences", alerts_section))
        rv.addStretch()

        row.addWidget(left)
        row.addWidget(right)
        cv.addLayout(row)
        cv.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def refresh(self):
        try:
            from controllers.setting_controller import SettingController
            s = SettingController.get_gym_settings()
            self.gym_name.setText(str(s.get("gym_name","")))
            self.gym_addr.setText(str(s.get("gym_address","")))
            self.gym_contact.setText(str(s.get("gym_contact","")))
            self.gym_email.setText(str(s.get("gym_email","")))
            self.dp_fee.setValue(float(s.get("day_pass_fee", 25)))
            self.weekly_price.setValue(float(s.get("weekly_plan_price", 110)))
            self.monthly_price.setValue(float(s.get("monthly_plan_price", 375)))
            self.low_stock_thresh.setValue(int(s.get("low_stock_threshold", 5)))
            self.exp_plan_days.setValue(int(s.get("expiring_plan_days", 3)))
        except Exception as e:
            pass

    def _save_gym_info(self):
        self._save({
            "gym_name": self.gym_name.text(),
            "gym_address": self.gym_addr.text(),
            "gym_contact": self.gym_contact.text(),
            "gym_email": self.gym_email.text(),
        })

    def _save_pricing(self):
        self._save({
            "day_pass_fee": str(self.dp_fee.value()),
            "weekly_plan_price": str(self.weekly_price.value()),
            "monthly_plan_price": str(self.monthly_price.value()),
        })

    def _save_alerts(self):
        self._save({
            "low_stock_threshold": str(self.low_stock_thresh.value()),
            "expiring_plan_days": str(self.exp_plan_days.value()),
        })

    def _save(self, data):
        try:
            from controllers.setting_controller import SettingController
            SettingController.update_settings(data)
            QMessageBox.information(self, "Saved", "Settings updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# ─── PAGE: PROFILE ───────────────────────────────────────────────────────────
class ProfilePage(QWidget):
    def __init__(self, admin_data=None, parent=None):
        super().__init__(parent)
        self.admin_data = admin_data or {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        hdr = make_label("PROFILE", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color:{C['text']};font-size:26px;font-weight:900;letter-spacing:2px;background:transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label('"Know yourself. Push yourself."', 13, color=C["text3"]))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;}")

        # Left
        left = QWidget(); left.setStyleSheet("background:transparent;")
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(16)

        profile_card = card_widget(10)
        pv = QVBoxLayout(profile_card); pv.setContentsMargins(28,28,28,28); pv.setSpacing(14)
        pv.addWidget(make_label("Update Profile", 15, QFont.Weight.Bold).also(lambda l: l.setStyleSheet(f"color:{C['text']};font-weight:700;background:transparent;")))

        def fld(parent_layout, label, widget):
            g = QWidget(); g.setStyleSheet("background:transparent;")
            gv = QVBoxLayout(g); gv.setContentsMargins(0,0,0,0); gv.setSpacing(4)
            lbl = QLabel(label.upper()); lbl.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{C['text2']};background:transparent;letter-spacing:1px;")
            gv.addWidget(lbl); gv.addWidget(widget)
            parent_layout.addWidget(g)

        self.name_edit = QLineEdit(); self.name_edit.setFixedHeight(38)
        self.name_edit.setText(str(self.admin_data.get("username","")))
        fld(pv, "Full Name", self.name_edit)

        save_btn = make_btn("Save Changes", "accent")
        save_btn.clicked.connect(self._save_profile)
        pv.addWidget(save_btn)
        lv.addWidget(profile_card)

        pw_card = card_widget(10)
        wv = QVBoxLayout(pw_card); wv.setContentsMargins(28,28,28,28); wv.setSpacing(14)
        wv.addWidget(make_label("Change Password", 15, QFont.Weight.Bold).also(lambda l: l.setStyleSheet(f"color:{C['text']};font-weight:700;background:transparent;")))

        self.cur_pw = QLineEdit(); self.cur_pw.setEchoMode(QLineEdit.EchoMode.Password); self.cur_pw.setFixedHeight(38)
        self.new_pw = QLineEdit(); self.new_pw.setEchoMode(QLineEdit.EchoMode.Password); self.new_pw.setFixedHeight(38)
        self.conf_pw = QLineEdit(); self.conf_pw.setEchoMode(QLineEdit.EchoMode.Password); self.conf_pw.setFixedHeight(38)
        fld(wv, "Current Password", self.cur_pw)
        fld(wv, "New Password", self.new_pw)
        fld(wv, "Confirm Password", self.conf_pw)
        pw_btn = make_btn("Update Password", "accent")
        pw_btn.clicked.connect(self._change_pw)
        wv.addWidget(pw_btn)
        lv.addWidget(pw_card)

        # Right: account info
        right = QWidget(); right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right); rv.setContentsMargins(20,0,0,0); rv.setSpacing(16)

        info_card = card_widget(10)
        iv = QVBoxLayout(info_card); iv.setContentsMargins(28,28,28,28); iv.setSpacing(14)
        iv.addWidget(make_label("Account Info", 15, QFont.Weight.Bold).also(lambda l: l.setStyleSheet(f"color:{C['text']};font-weight:700;background:transparent;")))

        username_ro = QLineEdit(str(self.admin_data.get("username","admin")))
        username_ro.setReadOnly(True); username_ro.setFixedHeight(38)
        username_ro.setStyleSheet(f"QLineEdit{{background:{C['surface2']};border:1px solid {C['border']};border-radius:8px;color:{C['text2']};padding:0 12px;}}")
        fld(iv, "Username", username_ro)

        role_ro = QLineEdit("Administrator")
        role_ro.setReadOnly(True); role_ro.setFixedHeight(38)
        role_ro.setStyleSheet(username_ro.styleSheet())
        fld(iv, "Role", role_ro)

        status_row = QHBoxLayout(); status_row.setSpacing(10)
        for label, color, val in [("Session", C["green"], "ACTIVE")]:
            s_card = QWidget()
            _card_id_counter[0] += 1
            _scn = f"neonStatusCard{_card_id_counter[0]}"
            s_card.setObjectName(_scn)
            s_card.setStyleSheet(f"QWidget#{_scn}{{background:{C['green_dim']};border:1px solid {C['green']};border-radius:8px;}}")
            sc = QVBoxLayout(s_card); sc.setContentsMargins(16,12,16,12); sc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sc.addWidget(make_label(label, 9, QFont.Weight.Bold).also(lambda l: l.setStyleSheet(f"color:{color};font-weight:700;letter-spacing:1px;background:transparent;text-align:center;")))
            sc.addWidget(make_label(val, 13, QFont.Weight.Bold).also(lambda l: l.setStyleSheet(f"color:{color};font-weight:700;background:transparent;")))
            status_row.addWidget(s_card)
        iv.addLayout(status_row)
        rv.addWidget(info_card)
        rv.addStretch()

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([480, 300])
        layout.addWidget(splitter, 1)

    def _save_profile(self):
        QMessageBox.information(self, "Saved", "Profile updated.")

    def _change_pw(self):
        if not self.cur_pw.text():
            QMessageBox.warning(self, "Validation", "Enter current password.")
            return
        if len(self.new_pw.text()) < 8:
            QMessageBox.warning(self, "Validation", "Password must be at least 8 characters.")
            return
        if self.new_pw.text() != self.conf_pw.text():
            QMessageBox.warning(self, "Validation", "Passwords do not match.")
            return
        try:
            from models.admin import Admin
            ok = Admin.change_password(self.admin_data.get("admin_id"), self.cur_pw.text(), self.new_pw.text())
            if ok:
                QMessageBox.information(self, "Success", "Password updated successfully.")
                self.cur_pw.clear(); self.new_pw.clear(); self.conf_pw.clear()
            else:
                QMessageBox.critical(self, "Error", "Current password incorrect.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh(self):
        pass


# ─── PAGE: RECYCLE BIN ───────────────────────────────────────────────────────
class RecycleBinPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        hdr = make_label("RECYCLE BIN", 26, QFont.Weight.Bold)
        hdr.setStyleSheet(f"color:{C['text']};font-size:26px;font-weight:900;letter-spacing:2px;background:transparent;")
        layout.addWidget(hdr)
        layout.addWidget(make_label("Soft-deleted customers. Restore or permanently delete.", 13, color=C["text2"]))

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Code", "Name", "Type", "Deleted At", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

    def refresh(self):
        try:
            from models.customer import Customer
            deleted = Customer.get_deleted() or []
            self.table.setRowCount(len(deleted))
            for i, c in enumerate(deleted):
                def ci(text, color=None):
                    item = QTableWidgetItem(str(text or "—"))
                    item.setForeground(QColor(color or C["text"]))
                    return item
                code_item = QTableWidgetItem(str(c.get("customer_code","—")))
                code_item.setForeground(QColor(C["accent_h"]))
                code_item.setFont(QFont("Courier New", 12))
                self.table.setItem(i, 0, code_item)
                self.table.setItem(i, 1, ci(c.get("full_name")))
                self.table.setItem(i, 2, ci(c.get("customer_type")))
                self.table.setItem(i, 3, ci(str(c.get("deleted_at",""))[:19]))

                aw = QWidget(); aw.setStyleSheet("background:transparent;")
                ah = QHBoxLayout(aw); ah.setContentsMargins(4,4,4,4); ah.setSpacing(6)
                cid = c.get("customer_id")

                restore_btn = make_btn("Restore", "green")
                restore_btn.setFixedHeight(30); restore_btn.setFont(QFont("Segoe UI",10))
                restore_btn.clicked.connect(lambda _, id=cid: self._restore(id))

                del_btn = make_btn("Delete", "red")
                del_btn.setFixedHeight(30); del_btn.setFont(QFont("Segoe UI",10))
                del_btn.clicked.connect(lambda _, id=cid: self._perm_delete(id))

                ah.addWidget(restore_btn); ah.addWidget(del_btn); ah.addStretch()
                self.table.setCellWidget(i, 4, aw)
                self.table.setRowHeight(i, 46)
        except Exception as e:
            pass

    def _restore(self, customer_id):
        from models.customer import Customer
        Customer.restore(customer_id)
        self.refresh()

    def _perm_delete(self, customer_id):
        reply = QMessageBox.warning(self, "Permanent Delete",
            "This will permanently delete this record. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from db_connection import get_cursor
                with get_cursor() as cursor:
                    cursor.execute("DELETE FROM customers WHERE customer_id = %s AND is_deleted = 1", (customer_id,))
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

# ─── MAIN WINDOW ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quad8 Gym Management System")
        self.setMinimumSize(1200, 750)
        self.showMaximized()
        self.setStyleSheet(GLOBAL_QSS)

        self._admin_data = {}
        self._pages = {}

        # Central widget
        self.central = QStackedWidget()
        self.setCentralWidget(self.central)

        # Login screen
        self.login_screen = LoginScreen()
        self.login_screen.login_success.connect(self._on_login)
        self.central.addWidget(self.login_screen)

        # App shell (added after login)
        self.app_shell = None

    def _build_app_shell(self):
        shell = BGWidget(BACKGROUND_IMG, overlay_alpha=240)
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Sidebar
        self.sidebar = SidebarWidget()
        self.sidebar.nav_clicked.connect(self._nav_to)
        self.sidebar.logout_clicked.connect(self._on_logout)
        shell_layout.addWidget(self.sidebar)

        # Right area
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        self.topbar = TopBar()
        rv.addWidget(self.topbar)

        # Page stack
        self.page_stack = QStackedWidget()
        self.page_stack.setStyleSheet("background: transparent;")
        rv.addWidget(self.page_stack, 1)

        shell_layout.addWidget(right, 1)
        return shell

    def _create_pages(self):
        ad = self._admin_data
        pages = {
            "dashboard": DashboardPage(),
            "checkin":   CheckInPage(admin_data=ad),
            "daypass":   DayPassPage(admin_data=ad),
            "planreg":   PlanRegPage(admin_data=ad),
            "customers": CustomersPage(),
            "products":  ProductsPage(admin_data=ad),
            "sales":     SalesPage(admin_data=ad),
            "restock":   RestockPage(),
            "reports":   ReportsPage(),
            "auditlog":  AuditLogPage(),
            "settings":  SettingsPage(),
            "profile":   ProfilePage(admin_data=ad),
            "recycle":   RecycleBinPage(),
        }
        for key, page in pages.items():
            page.setStyleSheet("background: transparent;")
            self.page_stack.addWidget(page)
        return pages

    def _on_login(self, admin_data):
        self._admin_data = admin_data

        if not self.app_shell:
            self.app_shell = self._build_app_shell()
            self.central.addWidget(self.app_shell)
            self._pages = self._create_pages()

        self.topbar.set_admin(admin_data)
        self.central.setCurrentWidget(self.app_shell)
        self._nav_to("dashboard")

    def _nav_to(self, key):
        titles = {
            "dashboard": ("Dashboard", "Today's Overview"),
            "checkin":   ("Check-In", "Scan or search customer"),
            "daypass":   ("Day Pass Entry", "Single-day visitor"),
            "planreg":   ("Plan Registration", "New member signup"),
            "customers": ("Customers", "All members & visitors"),
            "products":  ("Products", "Inventory management"),
            "sales":     ("Sales", "Record transactions"),
            "restock":   ("Restock", "Update stock levels"),
            "reports":   ("Reports", "Analytics & records"),
            "auditlog":  ("Audit Log", "System activity trail"),
            "settings":  ("Settings", "System configuration"),
            "profile":   ("Profile", "Account settings"),
            "recycle":   ("Recycle Bin", "Deleted records"),
        }
        title, sub = titles.get(key, (key.title(), ""))
        self.topbar.set_page(title, sub)
        self.sidebar._activate(key)

        if key in self._pages:
            self.page_stack.setCurrentWidget(self._pages[key])
            try:
                self._pages[key].refresh()
            except Exception:
                pass

    def _on_logout(self):
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.central.setCurrentWidget(self.login_screen)
            self.login_screen.user_input.clear()
            self.login_screen.pw_input.clear()
            self.login_screen.err_lbl.clear()
