
import sys
import math
import os
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QStackedWidget, QFrame,
    QScrollArea, QGridLayout, QSizePolicy, QGraphicsDropShadowEffect,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QAbstractItemView, QMessageBox, QFileDialog,
    QSpacerItem
)
from PyQt6.QtCore import (
    Qt, QTimer, QDateTime, QDate, QPropertyAnimation,
    QEasingCurve, QPoint, QRect, pyqtSignal, QSize
)
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QLinearGradient,
    QRadialGradient, QFontDatabase, QPainterPath, QPixmap,
    QIcon, QPalette, QPdfWriter, QPageSize
)
from PyQt6.QtSvg import QSvgRenderer

# ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
C = {
    "background":               "#131313",
    "surface":                  "#131313",
    "surface_dim":              "#131313",
    "surface_container_lowest": "#0e0e0e",
    "surface_container_low":    "#1c1b1b",
    "surface_container":        "#201f1f",
    "surface_container_high":   "#2a2a2a",
    "surface_container_highest":"#353534",
    "on_surface":               "#e5e2e1",
    "on_surface_variant":       "#c3c6d3",
    "primary":                  "#aec6ff",
    "primary_container":        "#1d4e9e",
    "on_primary":               "#002e6b",
    "secondary":                "#88d982",
    "secondary_container":      "#005b14",
    "on_secondary":             "#003909",
    "tertiary":                 "#ffb4ac",
    "tertiary_container":       "#a60010",
    "outline":                  "#8d909d",
    "outline_variant":          "#434751",
    "error":                    "#ffb4ab",
}

def qc(key): return QColor(C[key])

FONT_HEADLINE = "Space Grotesk"
FONT_BODY = "Inter"


def php_currency(amount):
    return f"₱{amount:,.0f}"


class RegistrationDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _build_member_id(self, full_name, phone):
        initials = "".join(part[0] for part in full_name.upper().split() if part)[:3]
        if not initials:
            initials = "NEW"
        phone_tail = (phone[-4:] if phone and len(phone) >= 4 else "0000")
        return f"Q8-{initials}-{phone_tail}"

    def _build_walkin_member_id(self, walkin_name):
        compact = "".join(ch for ch in walkin_name.upper() if ch.isalnum())
        if not compact:
            compact = "WALKIN"
        return f"WALKIN-{compact[:12]}"

    def generate_walkin_member_id(self, walkin_name):
        return self._build_walkin_member_id(walkin_name)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS member_registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    member_id TEXT,
                    cycle_start_date TEXT NOT NULL,
                    cycle_expiration_date TEXT,
                    protocol_name TEXT NOT NULL,
                    protocol_price_php REAL NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registration_id INTEGER,
                    member_name TEXT NOT NULL,
                    member_id TEXT NOT NULL,
                    checkin_date TEXT NOT NULL,
                    checkin_time TEXT NOT NULL,
                    checkout_time TEXT,
                    station TEXT NOT NULL DEFAULT 'STATION 04',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(member_id, checkin_date)
                )
                """
            )

            # Add checkout_time column if it doesn't exist
            cols = [row[1] for row in conn.execute("PRAGMA table_info(daily_checkins)").fetchall()]
            if "checkout_time" not in cols:
                conn.execute("ALTER TABLE daily_checkins ADD COLUMN checkout_time TEXT")
            
            # Add cycle_expiration_date column if it doesn't exist
            member_cols = [row[1] for row in conn.execute("PRAGMA table_info(member_registrations)").fetchall()]
            if "cycle_expiration_date" not in member_cols:
                conn.execute("ALTER TABLE member_registrations ADD COLUMN cycle_expiration_date TEXT")

            missing_member_ids = conn.execute(
                """
                SELECT id, full_name, phone
                FROM member_registrations
                WHERE member_id IS NULL OR TRIM(member_id) = ''
                """
            ).fetchall()
            for rec_id, full_name, phone in missing_member_ids:
                generated_member_id = self._build_member_id(full_name, phone)
                conn.execute(
                    "UPDATE member_registrations SET member_id = ? WHERE id = ?",
                    (generated_member_id, rec_id),
                )
            conn.commit()

    def save_registration(self, payload):
        from datetime import datetime, timedelta
        
        member_id = payload.get("member_id") or self._build_member_id(payload["full_name"], payload["phone"])
        
        # Calculate expiration date based on protocol
        start_date = datetime.strptime(payload["cycle_start_date"], "%m/%d/%Y")
        protocol = payload["protocol_name"]
        
        if protocol == "Weekly":
            expiration_date = (start_date + timedelta(days=7)).strftime("%m/%d/%Y")
        elif protocol == "Monthly":
            # Add 30 days for monthly
            expiration_date = (start_date + timedelta(days=30)).strftime("%m/%d/%Y")
        else:
            expiration_date = payload["cycle_start_date"]  # Default to start date
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO member_registrations (
                    full_name, email, phone, member_id, cycle_start_date,
                    cycle_expiration_date, protocol_name, protocol_price_php
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["full_name"],
                    payload["email"],
                    payload["phone"],
                    member_id,
                    payload["cycle_start_date"],
                    expiration_date,
                    payload["protocol_name"],
                    payload["protocol_price_php"],
                ),
            )
            conn.commit()

    def get_registrations(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, full_name, email, phone, member_id, cycle_start_date,
                    protocol_name, protocol_price_php, created_at
                FROM member_registrations
                ORDER BY id DESC
                """
            )
            return cur.fetchall()

    def find_member_for_checkin(self, search_text):
        token = (search_text or "").strip()
        if not token:
            return None

        normalized_member_id = token.upper()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, full_name, email, phone, member_id, cycle_start_date,
                    protocol_name, protocol_price_php
                FROM member_registrations
                WHERE UPPER(member_id) = UPPER(?)
                OR phone = ?
                OR full_name LIKE ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (normalized_member_id, token, f"%{token}%"),
            )
            row = cur.fetchone()

            if not row:
                return None

            rec_id, full_name, email, phone, member_id, cycle_start_date, protocol_name, protocol_price_php = row
            if not member_id:
                member_id = self._build_member_id(full_name, phone)
                conn.execute("UPDATE member_registrations SET member_id = ? WHERE id = ?", (member_id, rec_id))
                conn.commit()

            return {
                "id": rec_id,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "member_id": member_id,
                "cycle_start_date": cycle_start_date,
                "protocol_name": protocol_name,
                "protocol_price_php": protocol_price_php,
            }

    def record_daily_checkin(self, member, station="STATION 04"):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        now_time = QDateTime.currentDateTime().toString("HH:mm:ss")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO daily_checkins (
                        registration_id, member_name, member_id,
                        checkin_date, checkin_time, station
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        member["id"],
                        member["full_name"],
                        member["member_id"],
                        today,
                        now_time,
                        station,
                    ),
                )
                conn.commit()
            return True, f"Check-in saved for {today} at {now_time}."
        except sqlite3.IntegrityError:
            return False, "Already checked in today."

    def record_walkin_checkin(self, walkin_name, station="STATION 04"):
        clean_name = " ".join((walkin_name or "").strip().split())
        if not clean_name:
            return False, "Walk-in name is required."

        today = QDate.currentDate().toString("yyyy-MM-dd")
        now_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        walkin_member_id = self._build_walkin_member_id(clean_name)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO daily_checkins (
                        registration_id, member_name, member_id,
                        checkin_date, checkin_time, station
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        None,
                        clean_name,
                        walkin_member_id,
                        today,
                        now_time,
                        station,
                    ),
                )
                conn.commit()
            return True, f"Walk-in check-in saved for {today} at {now_time}.", walkin_member_id
        except sqlite3.IntegrityError:
            return False, "This walk-in guest is already checked in today.", walkin_member_id

    def get_existing_walkin_checkin(self, walkin_name, target_date=None):
        clean_name = " ".join((walkin_name or "").strip().split())
        if not clean_name:
            return None

        check_date = target_date or QDate.currentDate().toString("yyyy-MM-dd")
        normalized_date_expr = """
            CASE
                WHEN instr(checkin_date, '/') > 0 THEN
                    substr(checkin_date, 7, 4) || '-' || substr(checkin_date, 1, 2) || '-' || substr(checkin_date, 4, 2)
                ELSE
                    substr(checkin_date, 1, 10)
            END
        """

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                f"""
                SELECT id, member_name, member_id, checkin_date, checkin_time, checkout_time, station
                FROM daily_checkins
                WHERE registration_id IS NULL
                AND UPPER(TRIM(member_name)) = UPPER(?)
                AND {normalized_date_expr} = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (clean_name, check_date),
            )
            row = cur.fetchone()

        if not row:
            return None

        rec_id, member_name, member_id, checkin_date, checkin_time, checkout_time, station = row
        return {
            "id": rec_id,
            "member_name": member_name,
            "member_id": member_id,
            "checkin_date": checkin_date,
            "checkin_time": checkin_time,
            "checkout_time": checkout_time,
            "station": station,
        }

    def record_walkin_checkout(self, checkin_id):
        now_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT checkout_time
                FROM daily_checkins
                WHERE id = ?
                LIMIT 1
                """,
                (checkin_id,),
            )
            row = cur.fetchone()
            if not row:
                return False, "Walk-in check-in record not found.", None

            existing_checkout_time = row[0]
            if existing_checkout_time:
                return False, "This walk-in guest is already checked out today.", existing_checkout_time

            conn.execute(
                """
                UPDATE daily_checkins
                SET checkout_time = ?
                WHERE id = ?
                """,
                (now_time, checkin_id),
            )
            conn.commit()

        return True, f"Walk-in check-out saved at {now_time}.", now_time

    def get_today_checkins(self):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT member_name, member_id, checkin_time
                FROM daily_checkins
                WHERE checkin_date = ?
                ORDER BY checkin_time DESC
                """,
                (today,),
            )
            return cur.fetchall()

    def get_checkins_by_date(self, date_str):
        """Get all check-ins for a specific date"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, member_name, member_id, checkin_time, station, registration_id
                FROM daily_checkins
                WHERE checkin_date = ?
                ORDER BY checkin_time DESC
                """,
                (date_str,),
            )
            return cur.fetchall()

    def get_membership_checkins_by_date(self, date_str):
        """Get check-ins with membership cards (registered members only) for a specific date"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, member_name, member_id, checkin_time, station, registration_id
                FROM daily_checkins
                WHERE checkin_date = ? AND registration_id IS NOT NULL
                ORDER BY checkin_time DESC
                """,
                (date_str,),
            )
            return cur.fetchall()

    def get_walkin_checkins_by_date(self, date_str):
        """Get walk-in check-ins (no membership card) for a specific date"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, member_name, member_id, checkin_time, station, registration_id
                FROM daily_checkins
                WHERE checkin_date = ? AND registration_id IS NULL
                ORDER BY checkin_time DESC
                """,
                (date_str,),
            )
            return cur.fetchall()


# ─── CUSTOM PAINTER WIDGETS ───────────────────────────────────────────────────

class BarChart(QWidget):
    def __init__(self, data, labels=None, highlight_index=None, parent=None):
        super().__init__(parent)
        self.data = data
        self.labels = labels or []
        self.highlight_index = highlight_index if highlight_index is not None else (data.index(max(data)) if data else 0)
        self.setMinimumHeight(140)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 10, 10, 10, 28
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b
        n = len(self.data)
        if n == 0:
            return
        max_val = max(self.data) or 1
        bar_gap = 6
        bar_w = max(4, (chart_w - bar_gap * (n - 1)) / n)

        for i, val in enumerate(self.data):
            bh = int(chart_h * val / max_val)
            x = pad_l + i * (bar_w + bar_gap)
            y = pad_t + chart_h - bh
            if i == self.highlight_index:
                grad = QLinearGradient(x, y, x, y + bh)
                grad.setColorAt(0, qc("secondary"))
                grad.setColorAt(1, qc("secondary_container"))
                p.setBrush(QBrush(grad))
                p.setPen(Qt.PenStyle.NoPen)
                # Highlight label
                p.setPen(QPen(qc("surface_container_lowest")))
                p.setFont(QFont(FONT_BODY, 6, QFont.Weight.Bold))
                p.drawText(int(x), int(y) - 2, int(bar_w), 14,
                        Qt.AlignmentFlag.AlignCenter, f"PEAK:\n{val}")
                p.setPen(Qt.PenStyle.NoPen)
            else:
                p.setBrush(QBrush(qc("surface_container_high")))
                p.setPen(Qt.PenStyle.NoPen)
            r = 3
            p.drawRoundedRect(int(x), int(y), int(bar_w), bh, r, r)

        # Labels
        if self.labels:
            p.setPen(QPen(qc("on_surface_variant")))
            p.setFont(QFont(FONT_BODY, 7))
            for i, lbl in enumerate(self.labels):
                x = pad_l + i * (bar_w + bar_gap)
                p.drawText(int(x), h - pad_b + 4, int(bar_w), 20,
                        Qt.AlignmentFlag.AlignCenter, lbl)


class DonutChart(QWidget):
    def __init__(self, value=75, label="CAPACITY", parent=None):
        super().__init__(parent)
        self.value = value
        self.label = label
        self.setFixedSize(140, 140)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, r, pen_w = self.width()//2, self.height()//2, 52, 12
        rect = QRect(cx - r, cy - r, r * 2, r * 2)

        # Background arc
        p.setPen(QPen(qc("surface_container_high"), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # Foreground arc
        grad_pen = QPen(qc("secondary"), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(grad_pen)
        span = int(360 * 16 * self.value / 100)
        p.drawArc(rect, 90 * 16, -span)

        # Center text
        p.setPen(QPen(qc("on_surface")))
        p.setFont(QFont(FONT_HEADLINE, 18, QFont.Weight.Bold))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}%")

        # Label below
        p.setPen(QPen(qc("on_surface_variant")))
        p.setFont(QFont(FONT_BODY, 7))
        p.drawText(QRect(0, cy + r - 6, self.width(), 20),
                Qt.AlignmentFlag.AlignCenter, self.label)


class WeekHeatmap(QWidget):
    def __init__(self, values=None, parent=None):
        super().__init__(parent)
        self.values = values or [2, 4, 3, 4, 2, 5, 4]  # Mon-Sun
        self.setFixedHeight(54)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = 7
        w = self.width()
        cell = (w - 8) / n
        labels = ["MON", "TUE", "WED", "THU", "FRI", "TODAY", "SUN"]
        for i, val in enumerate(self.values):
            x = 4 + i * cell
            intensity = val / 5.0
            if i == 5:  # TODAY
                col = QColor(C["secondary"])
            else:
                col = QColor(C["secondary_container"])
                col.setAlphaF(0.3 + 0.6 * intensity)
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(int(x), 0, int(cell) - 4, 30, 4, 4)
            p.setPen(QPen(qc("on_surface_variant")))
            p.setFont(QFont(FONT_BODY, 6))
            p.drawText(int(x), 34, int(cell) - 4, 14,
                    Qt.AlignmentFlag.AlignCenter, labels[i])


class PowerGauge(QWidget):
    """Horizontal power gauge bar"""
    def __init__(self, value=0, max_val=100, label="", color_key="secondary", parent=None):
        super().__init__(parent)
        self.value = value
        self.max_val = max_val
        self.label = label
        self.color_key = color_key
        self.setFixedHeight(24)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        track_h = 6
        ty = (h - track_h) // 2

        # Track
        p.setBrush(QBrush(qc("surface_container_high")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, ty, w, track_h, 3, 3)

        # Fill
        fill_w = int(w * self.value / self.max_val)
        grad = QLinearGradient(0, 0, fill_w, 0)
        grad.setColorAt(0, qc("surface_container_high"))
        grad.setColorAt(1, qc(self.color_key))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(0, ty, fill_w, track_h, 3, 3)


# ─── STYLE HELPERS ────────────────────────────────────────────────────────────

def card_style(bg="surface_container", radius=6):
    return f"""
        background: {C[bg]};
        border-radius: {radius}px;
        border: none;
    """

def label_style(size=11, color="on_surface", weight="normal", family=FONT_BODY, ls=0):
    ls_css = f"letter-spacing: {ls}px;" if ls else ""
    w_map = {"normal": 400, "medium": 500, "bold": 700, "light": 300}
    return f"""
        color: {C[color]};
        font-family: '{family}';
        font-size: {size}px;
        font-weight: {w_map.get(weight, weight)};
        {ls_css}
    """

def btn_primary_style():
    return f"""
        QPushButton {{
            background: {C['secondary']};
            color: {C['on_secondary']};
            font-family: '{FONT_HEADLINE}';
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 3px;
            border: none;
            border-radius: 4px;
            padding: 12px 24px;
        }}
        QPushButton:hover {{
            background: #9de896;
        }}
        QPushButton:pressed {{
            background: {C['secondary_container']};
            color: {C['secondary']};
        }}
    """

def btn_secondary_style():
    return f"""
        QPushButton {{
            background: transparent;
            color: {C['on_surface_variant']};
            font-family: '{FONT_HEADLINE}';
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 2px;
            border: 1px solid {C['outline_variant']}40;
            border-radius: 4px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            color: {C['primary']};
            border-color: {C['primary']}60;
        }}
    """

def input_style():
    return f"""
        QLineEdit {{
            background: {C['surface_container_lowest']};
            color: {C['on_surface']};
            font-family: '{FONT_BODY}';
            font-size: 12px;
            border: none;
            border-bottom: 2px solid {C['outline_variant']};
            border-radius: 2px;
            padding: 10px 12px;
        }}
        QLineEdit:focus {{
            border-bottom: 2px solid {C['primary']};
        }}
        QLineEdit::placeholder {{
            color: {C['on_surface_variant']}60;
        }}
    """

def nav_btn_style(active=False):
    if active:
        return f"""
            QPushButton {{
                background: {C['surface_container_high']};
                color: {C['primary']};
                font-family: '{FONT_HEADLINE}';
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                border: none;
                border-left: 2px solid {C['primary']};
                border-radius: 0px;
                padding: 12px 16px;
                text-align: left;
            }}
        """
    return f"""
        QPushButton {{
            background: transparent;
            color: {C['on_surface_variant']};
            font-family: '{FONT_HEADLINE}';
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 2px;
            border: none;
            border-left: 2px solid transparent;
            border-radius: 0px;
            padding: 12px 16px;
            text-align: left;
        }}
        QPushButton:hover {{
            background: {C['surface_container']};
            color: {C['on_surface']};
        }}
    """


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

class Sidebar(QWidget):
    nav_changed = pyqtSignal(int)
    logout_requested = pyqtSignal()

    NAV_ITEMS = [
        ("⊞", "DASHBOARD", 0),
        ("◈", "RECORD USER", 1),
        ("◉", "REGISTER MEMBER", 2),
        ("⊡", "CHECK-IN", 3),
        ("▦", "REPORTS", 4),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background: {C['surface_container_low']}; border: none;")
        self.current = 0
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo area
        logo_frame = QFrame()
        logo_frame.setFixedHeight(160)
        logo_frame.setStyleSheet(f"background: {C['surface_container_low']}; border: none;")
        logo_lay = QVBoxLayout(logo_frame)
        logo_lay.setContentsMargins(16, 24, 16, 24)
        logo_lay.setSpacing(0)
        logo_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Welcome admin text - professional style
        welcome_lbl = QLabel("Welcome\nAdmin")
        welcome_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 24px; font-weight: 700; line-height: 1.3;")
        logo_lay.addWidget(welcome_lbl)

        layout.addWidget(logo_frame)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['outline_variant']}30;")
        layout.addWidget(div)

        # Nav buttons
        self.nav_btns = []
        for icon, label, idx in self.NAV_ITEMS:
            btn = QPushButton(f"  {icon}   {label}")
            btn.setFixedHeight(44)
            btn.setStyleSheet(nav_btn_style(idx == self.current))
            btn.clicked.connect(lambda _, i=idx: self._nav(i))
            layout.addWidget(btn)
            self.nav_btns.append(btn)

        layout.addStretch()

        # Bottom items
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet(f"background: {C['outline_variant']}30;")
        layout.addWidget(div2)

        support_btn = QPushButton("  ? SUPPORT")
        support_btn.setFixedHeight(40)
        support_btn.setStyleSheet(nav_btn_style(False))
        layout.addWidget(support_btn)
        
        self.logout_btn = QPushButton("  → LOGOUT")
        self.logout_btn.setFixedHeight(40)
        self.logout_btn.setStyleSheet(nav_btn_style(False))
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.clicked.connect(self.show_logout_dialog)
        layout.addWidget(self.logout_btn)

    def show_logout_dialog(self):
        """Show logout confirmation dialog"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Logout")
        dialog.setText("Are you sure you want to logout?")
        dialog.setStyleSheet(f"""
            QMessageBox {{
                background: {C['surface_container']};
            }}
            QMessageBox QLabel {{
                color: {C['on_surface']};
            }}
            QPushButton {{
                background: {C['secondary']};
                color: {C['on_secondary']};
                font-family: '{FONT_BODY}';
                font-size: 10px;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background: #9de896;
            }}
        """)
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        dialog.setIcon(QMessageBox.Icon.Question)
        
        if dialog.exec() == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def _nav(self, idx):
        self.current = idx
        for i, btn in enumerate(self.nav_btns):
            btn.setStyleSheet(nav_btn_style(i == idx))
        self.nav_changed.emit(idx)

    def set_active(self, idx):
        self._nav(idx)


# ─── TOP NAV BAR ──────────────────────────────────────────────────────────────

class TopBar(QWidget):
    def __init__(self, title="Command Center", parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            background: {C['surface_container_low']}CC;
            border-bottom: 1px solid {C['outline_variant']}30;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 16px; font-weight: 700;")
        lay.addWidget(self.title_lbl)
        lay.addStretch()

        # Search
        search = QLineEdit()
        search.setPlaceholderText("Search members, logs...")
        search.setFixedWidth(240)
        search.setFixedHeight(32)
        search.setStyleSheet(input_style())
        lay.addWidget(search)
        lay.addSpacing(16)

        # Icons
        for sym in ["🔔", "⚙", "👤"]:
            b = QPushButton(sym)
            b.setFixedSize(34, 34)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface_container_high']};
                    color: {C['on_surface_variant']};
                    border: none; border-radius: 17px;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background: {C['surface_container_highest']}; }}
            """)
            lay.addWidget(b)


# ─── STAT CARD ────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, label, value, sub_text, sub_color="secondary", parent=None):
        super().__init__(parent)
        self.setStyleSheet(card_style("surface_container"))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(110)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_HEADLINE, 2))
        lay.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(f"color: {C['on_surface']}; font-family: '{FONT_HEADLINE}'; font-size: 26px; font-weight: 700;")
        lay.addWidget(val)

        # Ghost big number decoration
        bg_num = QLabel("8")
        bg_num.setStyleSheet(f"""
            color: {C['surface_container_highest']};
            font-family: '{FONT_HEADLINE}';
            font-size: 72px;
            font-weight: 900;
        """)
        bg_num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        sub = QLabel(sub_text)
        sub.setStyleSheet(label_style(9, sub_color, "medium", FONT_BODY))
        lay.addWidget(sub)
        lay.addStretch()


# ─── ACTIVITY ROW ─────────────────────────────────────────────────────────────

class ActivityRow(QFrame):
    def __init__(self, name, detail, time_ago, status_color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: transparent; border-bottom: 1px solid {C['outline_variant']}20;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(12)

        # Avatar circle
        av = QFrame()
        av.setFixedSize(36, 36)
        av.setStyleSheet(f"background: {C['surface_container_high']}; border-radius: 18px;")
        av_lay = QVBoxLayout(av)
        av_lay.setContentsMargins(0, 0, 0, 0)
        av_lbl = QLabel(name[0])
        av_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 13px; font-weight: 700;")
        av_lay.addWidget(av_lbl)
        lay.addWidget(av)

        # Status dot
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {status_color}; border-radius: 4px;")

        info = QVBoxLayout()
        info.setSpacing(2)
        n_lbl = QLabel(name)
        n_lbl.setStyleSheet(label_style(12, "on_surface", "medium", FONT_BODY))
        d_lbl = QLabel(detail)
        d_lbl.setStyleSheet(label_style(9, "on_surface_variant", "normal", FONT_BODY))
        info.addWidget(n_lbl)
        info.addWidget(d_lbl)
        lay.addLayout(info)
        lay.addStretch()

        right = QVBoxLayout()
        right.setSpacing(4)
        t_lbl = QLabel(time_ago)
        t_lbl.setStyleSheet(label_style(9, "on_surface_variant", "normal", FONT_BODY))
        right.addWidget(t_lbl)
        right.addWidget(dot)
        lay.addLayout(right)


# ─── PAGE: LOGIN ──────────────────────────────────────────────────────────────

def create_icon_pixmap(icon_type="lock", size=24, color="#88d982"):
    """Create SVG-based icons"""
    svg_icons = {
        "lock": f"""<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="{color}" stroke-width="1.5"/>
            <path d="M7 11V7C7 4.24 9.24 2 12 2C14.76 2 17 4.24 17 7V11" stroke="{color}" stroke-width="1.5" fill="none"/>
            <circle cx="12" cy="16" r="1.5" fill="{color}"/>
        </svg>""",
        "eye": f"""<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 4C7 4 2.73 7.11 1 11.46C2.73 15.89 7 19 12 19C17 19 21.27 15.89 23 11.46C21.27 7.11 17 4 12 4Z" fill="none" stroke="{color}" stroke-width="1.5"/>
            <circle cx="12" cy="11" r="2.5" fill="{color}"/>
        </svg>"""
    }
    
    svg = svg_icons.get(icon_type, svg_icons["lock"])
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    svg_bytes = svg.encode('utf-8')
    
    painter = QPainter(pixmap)
    renderer = QSvgRenderer(svg_bytes)
    renderer.render(painter)
    painter.end()
    
    return pixmap


class PasswordInput(QWidget):
    """Custom password input with visibility toggle"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.password_visible = False
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Password input field
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setFixedHeight(40)
        self.input.setStyleSheet(input_style())
        lay.addWidget(self.input)

        # Eye toggle button with icon
        self.eye_btn = QPushButton()
        self.eye_btn.setFixedSize(40, 40)
        self.eye_btn.setIcon(QIcon(create_icon_pixmap("lock", 20, C["secondary"])))
        self.eye_btn.setIconSize(QSize(20, 20))
        self.eye_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface_container_lowest']};
                border: none;
                padding: 0px;
                border-radius: 2px;
                margin-left: -2px;
            }}
            QPushButton:hover {{
                background: {C['surface_container_high']};
            }}
            QPushButton:pressed {{
                background: {C['primary_container']};
            }}
        """)
        self.eye_btn.clicked.connect(self.toggle_visibility)
        lay.addWidget(self.eye_btn)

    def toggle_visibility(self):
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setIcon(QIcon(create_icon_pixmap("eye", 20, C["secondary"])))
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setIcon(QIcon(create_icon_pixmap("lock", 20, C["secondary"])))

    def setText(self, text):
        self.input.setText(text)

    def text(self):
        return self.input.text()

    def setPlaceholderText(self, text):
        self.input.setPlaceholderText(text)

    def returnPressed(self):
        return self.input.returnPressed


class LoginPage(QWidget):
    login_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C['background']};")
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        center = QWidget()
        center.setFixedWidth(420)
        lay = QVBoxLayout(center)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        # Logo area
        logo_area = QVBoxLayout()
        logo_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_area.setSpacing(8)

        logo_box = QFrame()
        logo_box.setFixedSize(128, 80)
        logo_box.setStyleSheet(f"""
            background: {C['primary_container']};
            border-radius: 10px;
        """)
        logo_lay = QVBoxLayout(logo_box)
        logo_lay.setContentsMargins(4, 4, 4, 4)
        logo_lbl = QLabel("QUAD8\nGYM")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 18px; font-weight: 900; letter-spacing: 2px;")
        logo_lay.addWidget(logo_lbl)

        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.addWidget(logo_box)

        title1 = QLabel("QUAD 8  ")
        title1.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 22px; font-weight: 800; letter-spacing: 8px;")
        title2 = QLabel("ADMIN")
        title2.setStyleSheet(f"color: {C['secondary']}; font-family: '{FONT_HEADLINE}'; font-size: 22px; font-weight: 800; letter-spacing: 8px;")
        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.setSpacing(0)
        title_row.addWidget(title1)
        title_row.addWidget(title2)

        sub = QLabel("THE KINETIC ENGINE")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(label_style(9, "on_surface_variant", "normal", FONT_HEADLINE, 5))

        logo_area.addLayout(logo_row)
        logo_area.addSpacing(16)
        logo_area.addLayout(title_row)
        logo_area.addWidget(sub)

        lay.addLayout(logo_area)
        lay.addSpacing(40)

        # Card
        card = QFrame()
        card.setStyleSheet(f"""
            background: {C['surface_container']}CC;
            border-radius: 6px;
            border: 1px solid {C['outline_variant']}20;
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(32, 28, 32, 28)
        card_lay.setSpacing(20)

        # Header
        h_lbl = QLabel("SECURE ENTRY")
        h_lbl.setStyleSheet(label_style(16, "on_surface", "medium", FONT_HEADLINE, 1))
        accent = QFrame()
        accent.setFixedSize(48, 3)
        accent.setStyleSheet(f"background: {C['secondary']}; border-radius: 2px;")
        card_lay.addWidget(h_lbl)
        card_lay.addWidget(accent)
        card_lay.addSpacing(8)

        # Username
        u_lbl = QLabel("Username")
        u_lbl.setStyleSheet(label_style(12, "on_surface_variant", "medium", FONT_HEADLINE, 3))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter your username")
        self.username.setFixedHeight(40)
        self.username.setStyleSheet(input_style())
        card_lay.addWidget(u_lbl)
        card_lay.addWidget(self.username)

        # Password with toggle
        p_lbl = QLabel("Password")
        p_lbl.setStyleSheet(label_style(12, "on_surface_variant", "medium", FONT_HEADLINE, 3))
        self.password = PasswordInput()
        self.password.setPlaceholderText("Enter your password")
        self.password.setFixedHeight(40)
        card_lay.addWidget(p_lbl)
        card_lay.addWidget(self.password)

        card_lay.addSpacing(8)

        # Login button
        login_btn = QPushButton("Login")
        login_btn.setFixedHeight(48)
        login_btn.setStyleSheet(btn_primary_style())
        login_btn.clicked.connect(self.validate_login)
        self.password.returnPressed().connect(self.validate_login)
        card_lay.addWidget(login_btn)
        card_lay.addSpacing(12)

        # Error message label
        self.error_msg = QLabel("")
        self.error_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_msg.setStyleSheet(f"color: {C['error']}; font-family: '{FONT_BODY}'; font-size: 11px; margin-top: 4px;")
        self.error_msg.setVisible(False)
        card_lay.addWidget(self.error_msg)

        lay.addWidget(card)
        lay.addSpacing(48)

        # System metadata
        meta = QHBoxLayout()
        meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta.setSpacing(24)
        for label, value in [("LATENCY", "14MS"), ("UPTIME", "99.9%"), ("STATUS", "ACTIVE")]:
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(label)
            lbl.setStyleSheet(label_style(8, "on_surface_variant", "normal", FONT_HEADLINE, 1))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val = QLabel(value)
            c = "secondary" if value == "ACTIVE" else "on_surface_variant"
            val.setStyleSheet(label_style(12, c, "bold", FONT_HEADLINE))
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)
            col.addWidget(val)
            meta.addLayout(col)
            if label != "STATUS":
                div = QFrame()
                div.setFixedSize(1, 32)
                div.setStyleSheet(f"background: {C['outline_variant']};")
                meta.addWidget(div)

        meta_w = QWidget()
        meta_w.setStyleSheet("opacity: 0.3;")
        meta_lay = QVBoxLayout(meta_w)
        meta_lay.addLayout(meta)
        lay.addWidget(meta_w)

        outer.addWidget(center)

        # Corner decoration
        corner = QLabel("QUAD_8_CORE_V2.0")
        corner.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 8px; letter-spacing: 3px;")
        outer.addWidget(corner, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

    def validate_login(self):
        """Validate username and password"""
        username = self.username.text().strip()
        password = self.password.text().strip()
        
        # Correct credentials
        valid_username = "admin"
        valid_password = "admin123"
        
        if username == valid_username and password == valid_password:
            self.error_msg.setVisible(False)
            self.login_success.emit()
        else:
            self.error_msg.setText("Invalid username or password")
            self.error_msg.setVisible(True)


# ─── PAGE: DASHBOARD ──────────────────────────────────────────────────────────

class DashboardPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.setStyleSheet(f"background: {C['background']};")
        self._build()
        # Keep dashboard data fresh while the app is open.
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_stats)
        self.refresh_timer.start(3000)

    def get_overall_checkins(self):
        """Get total overall activity (all check-ins + all registrations)."""
        if not self.db:
            return 0
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM daily_checkins) +
                        (SELECT COUNT(*) FROM member_registrations)
                    """
                )
                result = cur.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"Error in get_overall_checkins: {e}")
            return 0

    def get_weekly_checkins(self):
        """Get total ACTIVE members enrolled in Weekly membership plan."""
        if not self.db:
            return 0
        try:
            import sqlite3
            active_weekly = 0
            today = QDate.currentDate()
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT cycle_expiration_date
                    FROM member_registrations
                    WHERE protocol_name = ?
                    """,
                    ("Weekly",)
                )
                for (expiration_date,) in cur.fetchall():
                    if self._is_active_membership(expiration_date):
                        active_weekly += 1
                return active_weekly
        except Exception as e:
            print(f"Error in get_weekly_checkins: {e}")
            return 0

    def get_monthly_checkins(self):
        """Get total ACTIVE members enrolled in Monthly membership plan."""
        if not self.db:
            return 0
        try:
            import sqlite3
            active_monthly = 0
            today = QDate.currentDate()
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT cycle_expiration_date
                    FROM member_registrations
                    WHERE protocol_name = ?
                    """,
                    ("Monthly",)
                )
                for (expiration_date,) in cur.fetchall():
                    if self._is_active_membership(expiration_date):
                        active_monthly += 1
                return active_monthly
        except Exception as e:
            print(f"Error in get_monthly_checkins: {e}")
            return 0

    def _is_active_membership(self, expiration_date):
        """Use the same ACTIVE rule as Record User membership status."""
        expiry = QDate.fromString(expiration_date or "", "MM/dd/yyyy")
        return expiry.isValid() and QDate.currentDate() <= expiry

    def get_active_memberships(self):
        """Get total active memberships based on expiration date."""
        if not self.db:
            return 0
        try:
            import sqlite3
            active_members = 0
            today = QDate.currentDate()
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT cycle_expiration_date
                    FROM member_registrations
                    """
                )
                for (expiration_date,) in cur.fetchall():
                    if self._is_active_membership(expiration_date):
                        active_members += 1
            return active_members
        except Exception as e:
            print(f"Error in get_active_memberships: {e}")
            return 0

    def get_overall_revenue(self):
        """Get total recorded revenue from all memberships."""
        if not self.db:
            return 0
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT COALESCE(SUM(protocol_price_php), 0)
                    FROM member_registrations
                    """
                )
                result = cur.fetchone()
                return float(result[0]) if result and result[0] is not None else 0
        except Exception as e:
            print(f"Error in get_overall_revenue: {e}")
            return 0

    def get_plan_revenue(self, protocol_name):
        """Get total recorded revenue for a specific membership plan."""
        if not self.db:
            return 0
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT COALESCE(SUM(protocol_price_php), 0)
                    FROM member_registrations
                    WHERE protocol_name = ?
                    """,
                    (protocol_name,),
                )
                result = cur.fetchone()
                return float(result[0]) if result and result[0] is not None else 0
        except Exception as e:
            print(f"Error in get_plan_revenue({protocol_name}): {e}")
            return 0

    def get_current_month_revenue(self):
        """Get revenue recorded for the current month based on cycle start date."""
        today = QDate.currentDate()
        return self.get_month_revenue(today.year(), today.month())

    def get_month_revenue(self, year, month):
        """Get revenue for a specific month based on cycle start date."""
        if not self.db:
            return 0
        try:
            import sqlite3
            total = 0.0
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT cycle_start_date, protocol_price_php
                    FROM member_registrations
                    """
                )
                for start_date, price in cur.fetchall():
                    start_qdate = QDate.fromString(start_date or "", "MM/dd/yyyy")
                    if not start_qdate.isValid():
                        continue
                    if start_qdate.year() == year and start_qdate.month() == month:
                        total += float(price or 0)
            return total
        except Exception as e:
            print(f"Error in get_month_revenue: {e}")
            return 0

    def get_plan_purchase_metrics(self):
        """Get Weekly vs Monthly purchase counts and percentages."""
        if not self.db:
            return 0, 0, 0, 0, "NONE"

        try:
            import sqlite3
            weekly_count = 0
            monthly_count = 0
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT protocol_name, COUNT(*)
                    FROM member_registrations
                    WHERE protocol_name IN ('Weekly', 'Monthly')
                    GROUP BY protocol_name
                    """
                )
                for protocol_name, cnt in cur.fetchall():
                    if protocol_name == "Weekly":
                        weekly_count = cnt
                    elif protocol_name == "Monthly":
                        monthly_count = cnt

            total = weekly_count + monthly_count
            if total == 0:
                return weekly_count, monthly_count, 0, 0, "NONE"

            weekly_pct = int(round((weekly_count / total) * 100))
            monthly_pct = max(0, 100 - weekly_pct)

            if weekly_count > monthly_count:
                leader = "WEEKLY"
            elif monthly_count > weekly_count:
                leader = "MONTHLY"
            else:
                leader = "TIE"

            return weekly_count, monthly_count, weekly_pct, monthly_pct, leader
        except Exception as e:
            print(f"Error in get_plan_purchase_metrics: {e}")
            return 0, 0, 0, 0, "NONE"

    def update_plan_purchase_panel(self):
        if not hasattr(self, "plan_purchase_widgets"):
            return

        weekly_count, monthly_count, weekly_pct, monthly_pct, leader = self.get_plan_purchase_metrics()

        weekly_lbl = self.plan_purchase_widgets["weekly_pct_lbl"]
        weekly_lbl.setText(f"{weekly_pct}% ({weekly_count})")
        weekly_gauge = self.plan_purchase_widgets["weekly_gauge"]
        weekly_gauge.value = weekly_pct
        weekly_gauge.update()

        monthly_lbl = self.plan_purchase_widgets["monthly_pct_lbl"]
        monthly_lbl.setText(f"{monthly_pct}% ({monthly_count})")
        monthly_gauge = self.plan_purchase_widgets["monthly_gauge"]
        monthly_gauge.value = monthly_pct
        monthly_gauge.update()

        if leader == "WEEKLY":
            self.plan_leader_lbl.setText("Most Purchased: WEEKLY")
            self.plan_leader_lbl.setStyleSheet(label_style(9, "secondary", "bold", FONT_HEADLINE, 1))
        elif leader == "MONTHLY":
            self.plan_leader_lbl.setText("Most Purchased: MONTHLY")
            self.plan_leader_lbl.setStyleSheet(label_style(9, "tertiary", "bold", FONT_HEADLINE, 1))
        elif leader == "TIE":
            self.plan_leader_lbl.setText("Most Purchased: TIE")
            self.plan_leader_lbl.setStyleSheet(label_style(9, "on_surface_variant", "bold", FONT_HEADLINE, 1))
        else:
            self.plan_leader_lbl.setText("No purchases yet")
            self.plan_leader_lbl.setStyleSheet(label_style(9, "on_surface_variant", "bold", FONT_HEADLINE, 1))

    def update_revenue_panel(self):
        if not hasattr(self, "revenue_total_lbl"):
            return

        overall_revenue = self.get_overall_revenue()
        today = QDate.currentDate()
        monthly_revenue = self.get_current_month_revenue()
        prev_month_date = QDate(today.year(), today.month(), 1).addMonths(-1)
        previous_month_revenue = self.get_month_revenue(prev_month_date.year(), prev_month_date.month())
        monthly_share_pct = (monthly_revenue / overall_revenue * 100.0) if overall_revenue > 0 else 0.0

        self.revenue_total_lbl.setText(f"{monthly_share_pct:.1f}%")
        self.revenue_month_lbl.setText(f"THIS MONTH REVENUE: {php_currency(monthly_revenue)}")

        if previous_month_revenue > 0:
            change_pct = ((monthly_revenue - previous_month_revenue) / previous_month_revenue) * 100.0
            if change_pct > 0:
                self.revenue_change_lbl.setText(f"↑ +{change_pct:.1f}% VS LAST MONTH")
                self.revenue_change_lbl.setStyleSheet(label_style(9, "secondary", "medium", FONT_BODY))
            elif change_pct < 0:
                self.revenue_change_lbl.setText(f"↓ {change_pct:.1f}% VS LAST MONTH")
                self.revenue_change_lbl.setStyleSheet(label_style(9, "tertiary", "medium", FONT_BODY))
            else:
                self.revenue_change_lbl.setText("0.0% VS LAST MONTH")
                self.revenue_change_lbl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_BODY))
        elif monthly_revenue > 0:
            self.revenue_change_lbl.setText("NEW REVENUE THIS MONTH")
            self.revenue_change_lbl.setStyleSheet(label_style(9, "secondary", "medium", FONT_BODY))
        else:
            self.revenue_change_lbl.setText("NO REVENUE ACTIVITY")
            self.revenue_change_lbl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_BODY))

    def get_recent_checkins(self, limit=6):
        """Get latest check-ins for today only (dashboard recent activity panel)."""
        if not self.db:
            return []

        try:
            import sqlite3
            today_iso = QDate.currentDate().toString("yyyy-MM-dd")
            today_us = QDate.currentDate().toString("MM/dd/yyyy")
            with sqlite3.connect(self.db.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT member_name, member_id, checkin_date, checkin_time, registration_id
                    FROM daily_checkins
                    WHERE checkin_date = ?
                       OR checkin_date LIKE ?
                       OR checkin_date LIKE ?
                    ORDER BY checkin_date DESC, checkin_time DESC
                    LIMIT ?
                    """,
                    (today_iso, f"{today_iso}%", f"{today_us}%", limit),
                )
                return cur.fetchall()
        except Exception as e:
            print(f"Error in get_recent_checkins: {e}")
            return []

    def _format_checkin_display_time(self, checkin_date, checkin_time):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        if not checkin_time:
            return "--"
        if checkin_date == today:
            return checkin_time
        if checkin_date:
            return f"{checkin_date} {checkin_time}"
        return checkin_time

    def update_recent_activity_panel(self):
        if not hasattr(self, "activity_rows_lay"):
            return

        while self.activity_rows_lay.count() > 0:
            item = self.activity_rows_lay.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        rows = self.get_recent_checkins(6)
        if not rows:
            empty_lbl = QLabel("No recent check-ins yet")
            empty_lbl.setStyleSheet(label_style(10, "on_surface_variant", "medium", FONT_BODY))
            self.activity_rows_lay.addWidget(empty_lbl)
            return

        for member_name, member_id, checkin_date, checkin_time, registration_id in rows:
            name = member_name or "Unknown"
            detail = f"Check-in • {member_id or '--'}"
            time_text = self._format_checkin_display_time(checkin_date, checkin_time)
            status_color = C["secondary"] if registration_id else C["primary"]
            row = ActivityRow(name, detail, time_text, status_color)
            self.activity_rows_lay.addWidget(row)

    def get_today_checkins(self, period="Overall"):
        """Get today's activity by selected period.

        Weekly/Monthly: activity for the selected membership plan only.
        Overall: combined activity for both Weekly and Monthly plans.
        """
        if not self.db:
            return 0
        try:
            import sqlite3
            from datetime import datetime
            today_iso = datetime.now().strftime("%Y-%m-%d")
            today_us = datetime.now().strftime("%m/%d/%Y")
            with sqlite3.connect(self.db.db_path) as conn:
                if period == "Weekly":
                    protocol_filter = "Weekly"
                elif period == "Monthly":
                    protocol_filter = "Monthly"
                else:
                    protocol_filter = None

                if protocol_filter:
                    checkin_cur = conn.execute(
                        """
                                                SELECT mr.cycle_expiration_date
                        FROM daily_checkins dc
                        JOIN member_registrations mr ON mr.id = dc.registration_id
                        WHERE (dc.checkin_date LIKE ? OR dc.checkin_date LIKE ?)
                          AND mr.protocol_name = ?
                        """,
                        (f"{today_iso}%", f"{today_us}%", protocol_filter),
                    )
                    reg_cur = conn.execute(
                        """
                                                SELECT cycle_expiration_date
                        FROM member_registrations
                        WHERE (created_at LIKE ? OR created_at LIKE ?)
                          AND protocol_name = ?
                        """,
                        (f"{today_iso}%", f"{today_us}%", protocol_filter),
                    )
                else:
                    checkin_cur = conn.execute(
                        """
                                                SELECT mr.cycle_expiration_date
                        FROM daily_checkins dc
                        JOIN member_registrations mr ON mr.id = dc.registration_id
                        WHERE (dc.checkin_date LIKE ? OR dc.checkin_date LIKE ?)
                          AND mr.protocol_name IN ('Weekly', 'Monthly')
                        """,
                        (f"{today_iso}%", f"{today_us}%"),
                    )
                    reg_cur = conn.execute(
                        """
                                                SELECT cycle_expiration_date
                        FROM member_registrations
                        WHERE (created_at LIKE ? OR created_at LIKE ?)
                          AND protocol_name IN ('Weekly', 'Monthly')
                        """,
                        (f"{today_iso}%", f"{today_us}%"),
                    )

                active_checkins = sum(
                    1
                    for (expiration_date,) in checkin_cur.fetchall()
                    if self._is_active_membership(expiration_date)
                )
                active_registrations = sum(
                    1
                    for (expiration_date,) in reg_cur.fetchall()
                    if self._is_active_membership(expiration_date)
                )
                return active_checkins + active_registrations
        except Exception as e:
            print(f"Error in get_today_checkins: {e}")
            return 0

    def update_stats(self, period="Overall"):
        """Update stat cards based on selected period"""
        # Always fetch fresh data from database
        overall = self.get_overall_checkins()
        weekly = self.get_weekly_checkins()
        monthly = self.get_monthly_checkins()
        active_memberships = self.get_active_memberships()
        overall_revenue = self.get_overall_revenue()
        weekly_revenue = self.get_plan_revenue("Weekly")
        monthly_revenue_by_plan = self.get_plan_revenue("Monthly")
        # Today metric follows the selected period.
        if hasattr(self, 'period_combo'):
            selected_period = self.period_combo.currentText()
        else:
            selected_period = period or "Overall"
        today_checkins = self.get_today_checkins(selected_period)
        
        # Clear existing cards completely
        while self.stat_row.count() > 0:
            item = self.stat_row.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        # Get current period - use parameter or combo box
        if hasattr(self, 'period_combo'):
            current_period = self.period_combo.currentText()
        else:
            current_period = period or "Overall"
        
        if current_period == "Weekly":
            stats = [
                ("WEEKLY CHECKIN", str(weekly), f"↑ {weekly} MEMBERS", "secondary"),
                ("TODAY'S CHECK-INS", str(today_checkins), "WEEKLY PLAN TODAY", "primary"),
                ("ACTIVE MEMBERSHIPS", str(active_memberships), "CURRENTLY ACTIVE", "tertiary"),
                ("WEEKLY REVENUE", php_currency(weekly_revenue), f"🎯 TARGET: {php_currency(45000)}", "secondary"),
            ]
        elif current_period == "Monthly":
            stats = [
                ("MONTHLY CHECKIN", str(monthly), f"↑ {monthly} MEMBERS", "secondary"),
                ("TODAY'S CHECK-INS", str(today_checkins), "MONTHLY PLAN TODAY", "primary"),
                ("ACTIVE MEMBERSHIPS", str(active_memberships), "CURRENTLY ACTIVE", "tertiary"),
                ("MONTHLY REVENUE", php_currency(monthly_revenue_by_plan), f"TARGET: {php_currency(45000)}", "secondary"),
            ]
        else:  # Overall
            stats = [
                ("OVERALL CHECKIN", str(overall), f"↑ {weekly} THIS WEEK", "secondary"),
                ("TODAY'S CHECK-INS", str(today_checkins), "WEEKLY + MONTHLY TOTAL TODAY", "primary"),
                ("ACTIVE MEMBERSHIPS", str(active_memberships), "CURRENTLY ACTIVE", "tertiary"),
                ("OVERALL REVENUE", php_currency(overall_revenue), f" TARGET: {php_currency(45000)}", "secondary"),
            ]
        
        for label, val, sub, col in stats:
            card = StatCard(label, val, sub, col)
            self.stat_row.addWidget(card)

        self.update_plan_purchase_panel()
        self.update_revenue_panel()
        self.update_recent_activity_panel()

    def _build(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { width: 0px; }")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        # Period filter
        filter_row = QHBoxLayout()
        filter_row.addStretch()
        
        period_lbl = QLabel("Period: ")
        period_lbl.setStyleSheet(label_style(10, "on_surface_variant", "medium", FONT_BODY))
        filter_row.addWidget(period_lbl)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Overall", "Weekly", "Monthly"])
        self.period_combo.setFixedWidth(130)
        self.period_combo.setFixedHeight(32)
        self.period_combo.setStyleSheet(f"""
            QComboBox {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                font-family: '{FONT_BODY}';
                font-size: 10px;
                border: 1px solid {C['outline_variant']};
                border-radius: 4px;
                padding: 4px 8px;
                padding-right: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
                background: transparent;
                border-left: 1px solid {C['outline_variant']};
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
                width: 12px;
                height: 8px;
                background: transparent;
                margin-right: 4px;
            }}
            QComboBox::down-arrow:on {{
                top: 2px;
            }}
            QAbstractItemView {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                selection-background-color: {C['primary_container']};
                border: 1px solid {C['outline_variant']};
                border-radius: 4px;
                outline: none;
            }}
            QAbstractItemView::item:hover {{
                background-color: {C['surface_container_high']};
            }}
            QAbstractItemView::item:selected {{
                background-color: {C['primary_container']};
                color: {C['on_primary']};
            }}
        """)
        self.period_combo.currentTextChanged.connect(self.update_stats)
        filter_row.addWidget(self.period_combo)
        lay.addLayout(filter_row)

        # Stat cards row
        self.stat_row = QHBoxLayout()
        self.stat_row.setSpacing(12)
        self.update_stats()
        lay.addLayout(self.stat_row)

        # Mid row: chart + activity
        mid_row = QHBoxLayout()
        mid_row.setSpacing(12)

        # Check-in velocity chart
        chart_card = QFrame()
        chart_card.setStyleSheet(card_style("surface_container"))
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(20, 18, 20, 18)
        chart_lay.setSpacing(8)

        ct = QLabel("Check-in Velocity")
        ct.setStyleSheet(label_style(15, "on_surface", "bold", FONT_HEADLINE))
        cs = QLabel("Hourly member traffic analysis")
        cs.setStyleSheet(label_style(10, "on_surface_variant"))

        # Live badge
        badge_row = QHBoxLayout()
        badge_row.addWidget(ct)
        badge_row.addStretch()
        for b_txt in ["LIVE", "24H"]:
            bb = QPushButton(b_txt)
            bb.setFixedSize(44, 22)
            bb.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface_container_high']};
                    color: {C['on_surface_variant']};
                    font-family: '{FONT_BODY}'; font-size: 8px; font-weight: 600;
                    border-radius: 11px; border: none;
                }}
            """)
            badge_row.addWidget(bb)
        chart_lay.addLayout(badge_row)
        chart_lay.addWidget(cs)

        bar_data = [22, 35, 48, 42, 58, 44, 38, 30, 25]
        labels = ["06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "00:00", "", ""]
        bar_chart = BarChart(bar_data, labels[:len(bar_data)], highlight_index=4)
        bar_chart.setMinimumHeight(160)
        chart_lay.addWidget(bar_chart)
        mid_row.addWidget(chart_card, 3)

        # Recent Activity
        act_card = QFrame()
        act_card.setStyleSheet(card_style("surface_container"))
        act_lay = QVBoxLayout(act_card)
        act_lay.setContentsMargins(18, 16, 18, 16)
        act_lay.setSpacing(4)

        act_title = QLabel("Recent Activity")
        act_title.setStyleSheet(label_style(14, "on_surface", "bold", FONT_HEADLINE))
        act_lay.addWidget(act_title)

        self.activity_rows_lay = QVBoxLayout()
        self.activity_rows_lay.setSpacing(0)
        act_lay.addLayout(self.activity_rows_lay)

        view_btn = QPushButton("VIEW AUDIT LOG")
        view_btn.setFixedHeight(34)
        view_btn.setStyleSheet(btn_secondary_style())
        act_lay.addSpacing(8)
        act_lay.addWidget(view_btn)

        self.update_recent_activity_panel()
        mid_row.addWidget(act_card, 2)

        lay.addLayout(mid_row)

        # Bottom row
        bot_row = QHBoxLayout()
        bot_row.setSpacing(12)

        # Plan Purchaseability
        zone_card = QFrame()
        zone_card.setStyleSheet(card_style("surface_container"))
        zone_lay = QVBoxLayout(zone_card)
        zone_lay.setContentsMargins(20, 18, 20, 18)
        zone_lay.setSpacing(8)

        zt = QLabel("Plan Purchaseability")
        zt.setStyleSheet(label_style(15, "on_surface", "bold", FONT_HEADLINE))
        zs = QLabel("Weekly vs Monthly membership preference")
        zs.setStyleSheet(label_style(10, "on_surface_variant"))
        zone_lay.addWidget(zt)
        zone_lay.addWidget(zs)
        zone_lay.addSpacing(12)

        self.plan_purchase_widgets = {}

        for plan_name, key, col in [
            ("WEEKLY MEMBERSHIP PLAN", "weekly", "secondary"),
            ("MONTHLY MEMBERSHIP PLAN", "monthly", "tertiary"),
        ]:
            zr = QHBoxLayout()
            zl = QLabel(plan_name)
            zl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_HEADLINE, 1))
            zp = QLabel("0% (0)")
            zp.setStyleSheet(label_style(9, col, "bold", FONT_HEADLINE))
            zr.addWidget(zl)
            zr.addStretch()
            zr.addWidget(zp)
            zone_lay.addLayout(zr)
            gauge = PowerGauge(0, 100, plan_name, col)
            zone_lay.addWidget(gauge)
            zone_lay.addSpacing(4)

            self.plan_purchase_widgets[f"{key}_pct_lbl"] = zp
            self.plan_purchase_widgets[f"{key}_gauge"] = gauge

        self.plan_leader_lbl = QLabel("No purchases yet")
        self.plan_leader_lbl.setStyleSheet(label_style(9, "on_surface_variant", "bold", FONT_HEADLINE, 1))
        zone_lay.addWidget(self.plan_leader_lbl)

        self.update_plan_purchase_panel()

        bot_row.addWidget(zone_card, 3)

        # Revenue Insights
        ret_card = QFrame()
        ret_card.setStyleSheet(card_style("surface_container"))
        ret_lay = QVBoxLayout(ret_card)
        ret_lay.setContentsMargins(20, 18, 20, 18)
        ret_lay.setSpacing(8)

        rr = QHBoxLayout()
        rt = QLabel("Revenue Insights")
        rt.setStyleSheet(label_style(15, "on_surface", "bold", FONT_HEADLINE))
        rr.addWidget(rt)
        rr.addStretch()
        ri = QPushButton("↗")
        ri.setFixedSize(32, 32)
        ri.setStyleSheet(f"background: {C['primary_container']}; color: {C['primary']}; border: none; border-radius: 6px; font-size: 14px;")
        rr.addWidget(ri)
        rs = QLabel("Live membership revenue overview")
        rs.setStyleSheet(label_style(10, "on_surface_variant"))
        ret_lay.addLayout(rr)
        ret_lay.addWidget(rs)
        ret_lay.addSpacing(8)

        self.revenue_total_lbl = QLabel("0.0%")
        self.revenue_total_lbl.setStyleSheet(f"color: {C['on_surface']}; font-family: '{FONT_HEADLINE}'; font-size: 40px; font-weight: 800;")
        self.revenue_month_lbl = QLabel("THIS MONTH REVENUE: ₱0")
        self.revenue_month_lbl.setStyleSheet(label_style(9, "secondary", "medium", FONT_BODY))
        self.revenue_change_lbl = QLabel("0.0% VS LAST MONTH")
        self.revenue_change_lbl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_BODY))
        ret_lay.addWidget(self.revenue_total_lbl)
        ret_lay.addWidget(self.revenue_month_lbl)
        ret_lay.addWidget(self.revenue_change_lbl)

        self.update_revenue_panel()

        bot_row.addWidget(ret_card, 2)
        lay.addLayout(bot_row)
        lay.addStretch()


# ─── PAGE: REGISTER MEMBER ────────────────────────────────────────────────────

class RegisterPage(QWidget):
    registration_completed = pyqtSignal()  # Signal emitted when a member is successfully registered
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.form_inputs = {}
        self.protocol_prices = {
            "Weekly": 120,
            "Monthly": 350,
        }
        self.selected_protocol = "Monthly"  # Default selection
        self.member_status = "PENDING ACTIVATION"
        self.setStyleSheet(f"background: {C['background']};")
        self._build()

    def _build(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; }")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        lay = QHBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        # Left main column
        left = QVBoxLayout()
        left.setSpacing(20)

        # Header
        h1 = QLabel("REGISTER")
        h1.setStyleSheet(f"color: {C['on_surface']}; font-family: '{FONT_HEADLINE}'; font-size: 40px; font-weight: 800; letter-spacing: 2px;")
        h2 = QLabel("MEMBER")
        h2.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 40px; font-weight: 800; font-style: italic;")
        sub = QLabel("ADD A NEW MEMBER TO THE SYSTEM")
        sub.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_HEADLINE, 3))

        title_row = QHBoxLayout()
        title_row.addWidget(h1)
        title_row.addWidget(h2)
        title_row.addStretch()
        left.addLayout(title_row)
        left.addWidget(sub)
        left.addSpacing(8)

        # Section 01: Biometric Data
        s1 = self._make_section("⊙  MEMBER INFORMATION", "01", [
            ("FULL NAME", "Juan Cruz", "EMAIL", "name@email.com"),
            ("PHONE NUMBER", "09xx xxx xxxx", "START DATE", "mm/dd/yyyy"),
        ])
        left.addWidget(s1)

        add_btn = QPushButton("ADD MEMBER  +")
        add_btn.setFixedHeight(42)
        add_btn.setStyleSheet(btn_primary_style())
        add_btn.clicked.connect(self._submit_registration)
        left.addWidget(add_btn)

        # Section 02: Performance Protocol
        s2_card = QFrame()
        s2_card.setStyleSheet(card_style("surface_container"))
        s2_lay = QVBoxLayout(s2_card)
        s2_lay.setContentsMargins(20, 18, 20, 18)
        s2_lay.setSpacing(14)

        s2h = QHBoxLayout()
        s2t = QLabel("⚡  MEMBERSHIP PLAN")
        s2t.setStyleSheet(label_style(12, "on_surface", "bold", FONT_HEADLINE, 1))
        s2n = QLabel("02")
        s2n.setStyleSheet(f"color: {C['surface_container_highest']}; font-family: '{FONT_HEADLINE}'; font-size: 64px; font-weight: 900;")
        s2h.addWidget(s2t)
        s2h.addStretch()
        s2h.addWidget(s2n)
        s2_lay.addLayout(s2h)

        plan_row = QHBoxLayout()
        plan_row.setSpacing(12)
        
        self.plan_cards = {}  # Store references to plan cards
        
        for badge, name, desc, price, protocol_key in [
            ("PLAN W-1", "Weekly", "Pay every week.", php_currency(120), "Weekly"),
            ("PLAN M-4", "Monthly", "Pay once per month.", php_currency(350), "Monthly"),
        ]:
            pc = QFrame()
            # Set initial border based on default selection
            is_selected = (protocol_key == self.selected_protocol)
            border_col = C["secondary"] if is_selected else C["outline_variant"] + "40"
            
            pc.setStyleSheet(f"""
                background: {C['surface_container_low']};
                border-radius: 6px;
                border: 2px solid {border_col};
            """)
            pc.setCursor(Qt.CursorShape.PointingHandCursor)
            pc_lay = QVBoxLayout(pc)
            pc_lay.setContentsMargins(14, 14, 14, 14)
            pc_lay.setSpacing(6)

            pill = QLabel(badge)
            pill.setFixedHeight(20)
            pill.setStyleSheet(f"""
                background: {C['secondary_container']};
                color: {C['secondary']};
                font-family: '{FONT_HEADLINE}'; font-size: 8px; font-weight: 700; letter-spacing: 1px;
                border-radius: 10px; padding: 0 6px;
            """)
            pill.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            n_lbl = QLabel(name)
            n_lbl.setStyleSheet(label_style(22, "on_surface", "bold", FONT_HEADLINE))
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet(label_style(10, "on_surface_variant"))
            d_lbl.setWordWrap(True)

            pr_lbl = QLabel(f"{price} <span style='font-size:10px;font-weight:400;color:{C['on_surface_variant']};'>/ CYCLE</span>")
            pr_lbl.setStyleSheet(f"color: {C['secondary']}; font-family: '{FONT_HEADLINE}'; font-size: 18px; font-weight: 700;")
            pr_lbl.setTextFormat(Qt.TextFormat.RichText)

            pc_lay.addWidget(pill)
            pc_lay.addWidget(n_lbl)
            pc_lay.addWidget(d_lbl)
            pc_lay.addWidget(pr_lbl)
            
            # Store reference and set up click handler
            self.plan_cards[protocol_key] = pc
            pc.mousePressEvent = lambda event, proto=protocol_key: self._select_protocol(proto)
            
            plan_row.addWidget(pc)

        s2_lay.addLayout(plan_row)

        left.addWidget(s2_card)
        left.addStretch()

        lay.addLayout(left, 3)

        # Right column: Token Preview
        right = QVBoxLayout()
        right.setSpacing(12)

        token_card = QFrame()
        token_card.setStyleSheet(card_style("surface_container"))
        token_lay = QVBoxLayout(token_card)
        token_lay.setContentsMargins(18, 16, 18, 16)
        token_lay.setSpacing(12)

        tr = QHBoxLayout()
        tt = QLabel("MEMBER CARD PREVIEW")
        tt.setStyleSheet(label_style(11, "on_surface", "bold", FONT_HEADLINE, 1))
        tv = QLabel("VERSION 8.0.42")
        tv.setStyleSheet(label_style(8, "on_surface_variant"))
        tr.addWidget(tt)
        tr.addStretch()
        tr.addWidget(tv)
        token_lay.addLayout(tr)

        # Live membership card preview
        prev = QFrame()
        prev.setFixedHeight(270)
        prev.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C['surface_container_high']},
                    stop:0.5 #262b35,
                    stop:1 #1b1f26
                );
                border-radius: 12px;
                border: 1px solid {C['outline_variant']}66;
            }}
        """)
        prev_lay = QVBoxLayout(prev)
        prev_lay.setContentsMargins(16, 14, 16, 12)
        prev_lay.setSpacing(5)

        card_top = QHBoxLayout()
        card_brand = QLabel("QUAD8 FITNESS")
        card_brand.setStyleSheet(label_style(10, "on_surface", "bold", FONT_HEADLINE, 2))
        self.card_tier_lbl = QLabel("MEMBERSHIP")
        self.card_tier_lbl.setStyleSheet(f"""
            background: {C['secondary_container']}AA;
            color: {C['secondary']};
            border-radius: 10px;
            padding: 3px 8px;
            font-family: '{FONT_HEADLINE}';
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        self.card_tier_lbl.setMinimumWidth(96)
        self.card_tier_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_top.addWidget(card_brand)
        card_top.addStretch()
        card_top.addWidget(self.card_tier_lbl)
        prev_lay.addLayout(card_top)

        chip_row = QHBoxLayout()
        chip_row.setSpacing(10)
        chip = QFrame()
        chip.setFixedSize(40, 28)
        chip.setStyleSheet(f"""
            background: #cbb36a;
            border-radius: 5px;
            border: 1px solid #d8c88b;
        """)
        chip_art = QLabel("|||=")
        chip_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip_art.setStyleSheet("color: #69531f; font-size: 9px; font-weight: 700;")
        chip_lay = QVBoxLayout(chip)
        chip_lay.setContentsMargins(0, 0, 0, 0)
        chip_lay.addWidget(chip_art)
        badge = QLabel("CARD HOLDER")
        badge.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        chip_row.addWidget(chip)
        chip_row.addWidget(badge)
        chip_row.addStretch()
        prev_lay.addLayout(chip_row)

        self.card_name_lbl = QLabel("NEW MEMBER")
        self.card_name_lbl.setStyleSheet(label_style(22, "on_surface", "bold", FONT_HEADLINE, 1))
        self.card_name_lbl.setWordWrap(True)
        self.card_name_lbl.setMaximumHeight(54)
        self.card_plan_lbl = QLabel("PLAN: MONTHLY")
        self.card_plan_lbl.setStyleSheet(label_style(11, "secondary", "bold", FONT_HEADLINE, 1))
        self.card_phone_lbl = QLabel("PHONE: 09XXXXXXXXX")
        self.card_phone_lbl.setStyleSheet(label_style(10, "on_surface", "medium", FONT_BODY))
        self.card_email_lbl = QLabel("EMAIL: member@email.com")
        self.card_email_lbl.setStyleSheet(label_style(10, "on_surface", "medium", FONT_BODY))
        self.card_date_lbl = QLabel("START: --/--/----")
        self.card_date_lbl.setStyleSheet(label_style(10, "on_surface", "medium", FONT_BODY))
        self.card_exp_lbl = QLabel("VALID UNTIL: --/--/----")
        self.card_exp_lbl.setStyleSheet(label_style(10, "on_surface", "medium", FONT_BODY))
        self.card_no_lbl = QLabel("CARD NO: 0000 0000 0000")
        self.card_no_lbl.setStyleSheet(label_style(10, "on_surface", "bold", FONT_HEADLINE, 2))
        self.card_id_lbl = QLabel("MEMBER ID: Q8-NEW-0000")
        self.card_id_lbl.setStyleSheet(label_style(10, "primary", "bold", FONT_HEADLINE, 1))
        prev_lay.addWidget(self.card_name_lbl)
        prev_lay.addWidget(self.card_plan_lbl)
        prev_lay.addWidget(self.card_phone_lbl)
        prev_lay.addWidget(self.card_email_lbl)
        prev_lay.addWidget(self.card_date_lbl)
        prev_lay.addWidget(self.card_exp_lbl)
        prev_lay.addWidget(self.card_no_lbl)
        prev_lay.addWidget(self.card_id_lbl)
        self.card_preview_frame = prev
        token_lay.addWidget(prev)

        status_card = QFrame()
        status_card.setStyleSheet(card_style("surface_container_high"))
        status_lay = QVBoxLayout(status_card)
        status_lay.setContentsMargins(12, 10, 12, 10)
        status_lay.setSpacing(4)
        status_title = QLabel("MEMBER STATUS")
        status_title.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        self.status_value_lbl = QLabel(self.member_status)
        self.status_value_lbl.setStyleSheet(label_style(11, "secondary", "bold", FONT_HEADLINE, 1))
        status_lay.addWidget(status_title)
        status_lay.addWidget(self.status_value_lbl)
        token_lay.addWidget(status_card)

        member_id_card = QFrame()
        member_id_card.setStyleSheet(card_style("surface_container_high"))
        member_id_lay = QVBoxLayout(member_id_card)
        member_id_lay.setContentsMargins(12, 10, 12, 10)
        member_id_lay.setSpacing(4)
        member_id_title = QLabel("MEMBER ID")
        member_id_title.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        self.member_id_value_lbl = QLabel("Q8-NEW-0000")
        self.member_id_value_lbl.setStyleSheet(label_style(11, "on_surface", "bold", FONT_HEADLINE, 1))
        member_id_lay.addWidget(member_id_title)
        member_id_lay.addWidget(self.member_id_value_lbl)
        token_lay.addWidget(member_id_card)

        print_btn = QPushButton("🖨  PRINT MEMBER CARD")
        print_btn.setFixedHeight(40)
        print_btn.setStyleSheet(btn_secondary_style())
        print_btn.clicked.connect(self._export_member_card_pdf)
        token_lay.addWidget(print_btn)

        # Security notice
        sec_txt = QLabel("Your data is encrypted and stored securely.")
        sec_txt.setStyleSheet(label_style(9, "on_surface_variant"))
        sec_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sec_txt.setWordWrap(True)
        token_lay.addWidget(sec_txt)

        right.addWidget(token_card)
        right.addStretch()
        lay.addLayout(right, 2)

        self._wire_live_preview()
        self._update_live_preview()

    def _make_section(self, title, number, rows):
        card = QFrame()
        card.setStyleSheet(card_style("surface_container"))
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        header = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(label_style(12, "on_surface", "bold", FONT_HEADLINE, 1))
        n = QLabel(number)
        n.setStyleSheet(f"color: {C['surface_container_highest']}; font-family: '{FONT_HEADLINE}'; font-size: 64px; font-weight: 900;")
        header.addWidget(t)
        header.addStretch()
        header.addWidget(n)
        lay.addLayout(header)

        for row in rows:
            grid = QHBoxLayout()
            grid.setSpacing(12)
            for i in range(0, len(row), 2):
                col = QVBoxLayout()
                col.setSpacing(4)
                lbl = QLabel(row[i])
                lbl.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 2))
                if row[i] == "START DATE":
                    inp = QDateEdit()
                    inp.setCalendarPopup(True)
                    inp.setDisplayFormat("MM/dd/yyyy")
                    inp.setDate(QDate.currentDate())
                    inp.setFixedHeight(40)
                    inp.setToolTip("Click the calendar button to pick a date")
                    inp.setStyleSheet(f"""
                        QDateEdit {{
                            background: {C['surface_container_lowest']};
                            color: {C['on_surface']};
                            font-family: '{FONT_BODY}';
                            font-size: 12px;
                            border: none;
                            border-bottom: 2px solid {C['outline_variant']};
                            border-radius: 2px;
                            padding: 10px 12px;
                        }}
                        QDateEdit:focus {{
                            border-bottom: 2px solid {C['primary']};
                        }}
                    """)
                else:
                    inp = QLineEdit()
                    inp.setPlaceholderText(row[i + 1])
                    inp.setFixedHeight(40)
                    inp.setStyleSheet(input_style())
                    if row[i] == "FULL NAME":
                        inp.editingFinished.connect(self._normalize_name_field)
                    if row[i] == "PHONE NUMBER":
                        inp.setMaxLength(11)
                        inp.textChanged.connect(lambda text, w=inp: self._enforce_phone_digits(w, text))
                self.form_inputs[row[i]] = inp
                col.addWidget(lbl)
                col.addWidget(inp)
                grid.addLayout(col)
            lay.addLayout(grid)

        return card

    def _enforce_phone_digits(self, widget, text):
        digits_only = "".join(ch for ch in text if ch.isdigit())[:11]
        if text != digits_only:
            widget.setText(digits_only)

    def _to_name_case(self, raw_name):
        tokens = [t for t in raw_name.strip().split() if t]
        return " ".join(t[:1].upper() + t[1:].lower() for t in tokens)

    def _normalize_name_field(self):
        name_widget = self.form_inputs.get("FULL NAME")
        if not name_widget:
            return
        normalized = self._to_name_case(name_widget.text())
        if normalized != name_widget.text():
            name_widget.setText(normalized)
    
    def _select_protocol(self, protocol):
        self.selected_protocol = protocol
        # Update plan card styles
        for proto, card in self.plan_cards.items():
            if proto == protocol:
                # Selected card - highlight
                card.setStyleSheet(f"""
                    background: {C['surface_container_low']};
                    border-radius: 6px;
                    border: 2px solid {C['secondary']};
                """)
            else:
                # Unselected card - muted
                card.setStyleSheet(f"""
                    background: {C['surface_container_low']};
                    border-radius: 6px;
                    border: 2px solid {C['outline_variant']}40;
                """)
        self._update_live_preview()

    def _wire_live_preview(self):
        for widget in self.form_inputs.values():
            if isinstance(widget, QDateEdit):
                widget.dateChanged.connect(self._update_live_preview)
            else:
                widget.textChanged.connect(self._update_live_preview)

    def _build_member_id(self, name, phone):
        initials = "".join(part[0] for part in name.upper().split() if part)[:3]
        if not initials:
            initials = "NEW"
        phone_tail = (phone[-4:] if len(phone) >= 4 else "0000")
        return f"Q8-{initials}-{phone_tail}"

    def _update_live_preview(self, *_args):
        name = self._to_name_case(self.form_inputs["FULL NAME"].text())
        email = self.form_inputs["EMAIL"].text().strip()
        phone = self.form_inputs["PHONE NUMBER"].text().strip()
        start_qdate = self.form_inputs["START DATE"].date()
        start_date = start_qdate.toString("MM/dd/yyyy")
        selected_plan = self.selected_protocol
        selected_price = float(self.protocol_prices.get(selected_plan, 0))
        card_member_id = self._build_member_id(name, phone)
        if selected_plan == "Weekly":
            expiry_qdate = start_qdate.addDays(7)
            tier_text = "WEEKLY PASS"
        else:
            expiry_qdate = start_qdate.addMonths(1)
            tier_text = "MONTHLY PASS"
        expiry_date = expiry_qdate.toString("MM/dd/yyyy")
        phone_tail = phone[-8:] if len(phone) >= 8 else (phone.rjust(8, "0") if phone else "00000000")
        card_number = f"8800 {phone_tail[:4]} {phone_tail[4:]}"

        self.card_name_lbl.setText(name if name else "NEW MEMBER")
        self.card_plan_lbl.setText(f"PLAN: {selected_plan.upper()} ({php_currency(selected_price)})")
        self.card_phone_lbl.setText(f"PHONE: {phone if phone else '09XXXXXXXXX'}")
        self.card_email_lbl.setText(f"EMAIL: {email if email else 'member@email.com'}")
        self.card_date_lbl.setText(f"START: {start_date}")
        self.card_exp_lbl.setText(f"VALID UNTIL: {expiry_date}")
        self.card_no_lbl.setText(f"CARD NO: {card_number}")
        self.card_id_lbl.setText(f"MEMBER ID: {card_member_id}")
        self.card_tier_lbl.setText(tier_text)
        self.member_id_value_lbl.setText(card_member_id)

    def _submit_registration(self):
        full_name = self._to_name_case(self.form_inputs["FULL NAME"].text())
        email = self.form_inputs["EMAIL"].text().strip()
        phone = self.form_inputs["PHONE NUMBER"].text().strip()
        cycle_start_date = self.form_inputs["START DATE"].date().toString("MM/dd/yyyy")

        self.form_inputs["FULL NAME"].setText(full_name)

        if not all([full_name, email, phone, cycle_start_date]):
            QMessageBox.warning(self, "Missing Data", "Please complete all required fields before saving.")
            return

        if not full_name or len(full_name.strip()) == 0:
            QMessageBox.warning(self, "Invalid Name", "Please enter a full name.")
            return

        if (not phone.isdigit()) or len(phone) != 11:
            QMessageBox.warning(self, "Invalid Phone Number", "Phone number must be exactly 11 digits.")
            return

        protocol_name = self.selected_protocol
        protocol_price = float(self.protocol_prices.get(protocol_name, 0))
        member_id = self._build_member_id(full_name, phone)

        payload = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "member_id": member_id,
            "cycle_start_date": cycle_start_date,
            "protocol_name": protocol_name,
            "protocol_price_php": protocol_price,
        }

        try:
            self.db.save_registration(payload)
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Database Error", f"Failed to save registration: {exc}")
            return

        self.member_status = "ACTIVE"
        self.status_value_lbl.setText(self.member_status)

        QMessageBox.information(self, "Saved", f"Member saved successfully. Plan fee: {php_currency(protocol_price)}")
        for field in self.form_inputs.values():
            if isinstance(field, QDateEdit):
                field.setDate(QDate.currentDate())
            else:
                field.clear()
        self.selected_protocol = "Monthly"
        self.member_status = "PENDING ACTIVATION"
        self.status_value_lbl.setText(self.member_status)
        self._select_protocol("Monthly")
        
        # Emit signal to refresh dashboard
        self.registration_completed.emit()

    def _export_member_card_pdf(self):
        default_file = f"member_card_{self.member_id_value_lbl.text().replace(' ', '_').replace(':', '')}.pdf"
        documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
        initial_path = os.path.join(documents_dir, default_file)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Member Card PDF",
            initial_path,
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        try:
            writer = QPdfWriter(file_path)
            writer.setResolution(300)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

            painter = QPainter(writer)
            if not painter.isActive():
                raise RuntimeError("Unable to start PDF writer")

            page_rect = QRect(0, 0, writer.width(), writer.height())
            card_pixmap = self.card_preview_frame.grab()
            margin = 180
            footer_height = 140
            content_rect = page_rect.adjusted(
                margin,
                margin,
                -margin,
                -(margin + footer_height),
            )

            # Keep the card centered while preserving its original aspect ratio.
            card_ratio = card_pixmap.width() / max(1, card_pixmap.height())
            card_w = content_rect.width()
            card_h = int(card_w / max(0.1, card_ratio))
            if card_h > content_rect.height():
                card_h = content_rect.height()
                card_w = int(card_h * card_ratio)

            card_rect = QRect(
                content_rect.x() + (content_rect.width() - card_w) // 2,
                content_rect.y() + (content_rect.height() - card_h) // 2,
                card_w,
                card_h,
            )

            radius = 36
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Scale pixmap to fill the entire card rect.
            scaled_pixmap = card_pixmap.scaled(
                card_rect.width(),
                card_rect.height(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            # Build a transparent rounded pixmap first so all 4 corners stay rounded in PDF.
            rounded_pixmap = QPixmap(card_rect.size())
            rounded_pixmap.fill(Qt.GlobalColor.transparent)
            rp = QPainter(rounded_pixmap)
            rp.setRenderHint(QPainter.RenderHint.Antialiasing)
            rounded_path = QPainterPath()
            rounded_path.addRoundedRect(
                0,
                0,
                float(card_rect.width()),
                float(card_rect.height()),
                radius,
                radius,
            )
            rp.setClipPath(rounded_path)
            rp.drawPixmap(0, 0, scaled_pixmap)
            rp.end()

            painter.drawPixmap(card_rect.topLeft(), rounded_pixmap)

            painter.setPen(QColor(C["on_surface_variant"]))
            painter.setFont(QFont(FONT_BODY, 10))
            footer = f"Generated: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}"
            painter.drawText(
                margin,
                page_rect.height() - margin,
                page_rect.width() - (margin * 2),
                40,
                Qt.AlignmentFlag.AlignRight,
                footer,
            )
            painter.end()

            QMessageBox.information(self, "PDF Saved", f"Member card saved to:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", f"Failed to create PDF: {exc}")


# ─── PAGE: DAILY CHECK-IN ─────────────────────────────────────────────────────

class DailyCheckInPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C['background']};")
        self._build()

    def _build(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; }")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Header row
        header_row = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(4)

        t1 = QLabel("DAILY")
        t1.setStyleSheet(f"color: {C['on_surface']}; font-family: '{FONT_HEADLINE}'; font-size: 42px; font-weight: 800;")
        t2 = QLabel("TERMINAL")
        t2.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 42px; font-weight: 800; font-style: italic;")
        t_row = QHBoxLayout()
        t_row.addWidget(t1)
        t_row.addWidget(t2)
        t_row.addStretch()
        header_left.addLayout(t_row)

        status_row = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {C['secondary']}; border-radius: 4px;")
        live = QLabel("LIVE SYSTEM ACTIVE")
        live.setStyleSheet(label_style(9, "secondary", "bold", FONT_HEADLINE, 2))
        sep = QLabel("// STATION_ID: Q8_ENTRY_01")
        sep.setStyleSheet(label_style(9, "on_surface_variant", "normal", FONT_BODY))
        status_row.addWidget(dot)
        status_row.addSpacing(4)
        status_row.addWidget(live)
        status_row.addWidget(sep)
        status_row.addStretch()
        header_left.addLayout(status_row)

        header_row.addLayout(header_left, 3)

        # Occupancy card
        occ_card = QFrame()
        occ_card.setStyleSheet(card_style("surface_container"))
        occ_card.setFixedWidth(220)
        occ_lay = QVBoxLayout(occ_card)
        occ_lay.setContentsMargins(16, 14, 16, 14)
        occ_lay.setSpacing(6)
        oc_lbl = QLabel("CURRENT OCCUPANCY")
        oc_lbl.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        oc_val = QLabel("142 <span style='font-size:14px;font-weight:400;color:{};'>/ 250</span>".format(C['on_surface_variant']))
        oc_val.setTextFormat(Qt.TextFormat.RichText)
        oc_val.setStyleSheet(f"color: {C['on_surface']}; font-family: '{FONT_HEADLINE}'; font-size: 28px; font-weight: 800;")
        gauge = PowerGauge(142, 250, "", "secondary")
        occ_lay.addWidget(oc_lbl)
        occ_lay.addWidget(oc_val)
        occ_lay.addWidget(gauge)
        header_row.addWidget(occ_card, 0, Qt.AlignmentFlag.AlignTop)

        lay.addLayout(header_row)

        # Main content row
        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        # Left: Identify Member + Feed
        left = QVBoxLayout()
        left.setSpacing(14)

        # Identify card
        id_card = QFrame()
        id_card.setStyleSheet(card_style("surface_container"))
        id_lay = QVBoxLayout(id_card)
        id_lay.setContentsMargins(18, 16, 18, 16)
        id_lay.setSpacing(12)

        id_h = QLabel("◈  IDENTIFY MEMBER")
        id_h.setStyleSheet(label_style(12, "on_surface", "bold", FONT_HEADLINE, 1))
        id_lay.addWidget(id_h)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        mid_input = QLineEdit()
        mid_input.setPlaceholderText("Scan QR or Enter Member ID...")
        mid_input.setFixedHeight(44)
        mid_input.setStyleSheet(input_style())
        verify_btn = QPushButton("VERIFY IDENTITY")
        verify_btn.setFixedHeight(44)
        verify_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface_container_highest']};
                color: {C['on_surface']};
                font-family: '{FONT_HEADLINE}';
                font-size: 10px; font-weight: 700;
                letter-spacing: 2px;
                border: none; border-radius: 4px;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: {C['primary_container']}; color: {C['primary']}; }}
        """)
        search_row.addWidget(mid_input, 3)
        search_row.addWidget(verify_btn, 1)
        id_lay.addLayout(search_row)

        # Method buttons
        method_row = QHBoxLayout()
        method_row.setSpacing(8)
        for sym, name in [("☉", "BIOMETRIC"), ("▣", "RFID TAG"), ("◎", "FACE SCAN"), ("⌨", "MANUAL PIN")]:
            mb = QVBoxLayout()
            mb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mb.setSpacing(4)
            ic = QPushButton(sym)
            ic.setFixedSize(60, 48)
            ic.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface_container_high']};
                    color: {C['on_surface_variant']};
                    font-size: 18px;
                    border: none; border-radius: 4px;
                }}
                QPushButton:hover {{ background: {C['surface_container_highest']}; color: {C['on_surface']}; }}
            """)
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(label_style(7, "on_surface_variant", "medium", FONT_HEADLINE, 1))
            mb.addWidget(ic)
            mb.addWidget(lbl)
            method_row.addLayout(mb)
        id_lay.addLayout(method_row)
        left.addWidget(id_card)

        # Activity Feed
        feed_card = QFrame()
        feed_card.setStyleSheet(card_style("surface_container"))
        feed_lay = QVBoxLayout(feed_card)
        feed_lay.setContentsMargins(18, 14, 18, 14)
        feed_lay.setSpacing(8)

        fh_row = QHBoxLayout()
        fh = QLabel("TODAY'S ACTIVITY FEED")
        fh.setStyleSheet(label_style(11, "on_surface", "bold", FONT_HEADLINE, 1))
        ft = QLabel("08:00 — 22:00")
        ft.setStyleSheet(label_style(9, "on_surface_variant"))
        fh_row.addWidget(fh)
        fh_row.addStretch()
        fh_row.addWidget(ft)
        feed_lay.addLayout(fh_row)

        # Table header
        cols = ["MEMBER", "TIME", "STATUS", "ACTION"]
        hdr = QHBoxLayout()
        widths = [3, 1, 1, 1]
        for c, w in zip(cols, widths):
            l = QLabel(c)
            l.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 1))
            hdr.addWidget(l, w)
        feed_lay.addLayout(hdr)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['outline_variant']}30;")
        feed_lay.addWidget(div)

        # Feed rows
        feed_data = [
            ("Sarah Chen", "Elite Performance", "14:32:01", "VERIFIED", C["secondary"], False),
            ("Marcus Thorne", "Strength Lab", "14:28:45", "VERIFIED", C["secondary"], False),
            ("Elena Rodriguez", "Kinetic Pro", "14:15:22", "MEMBERSHIP EXPIRED", C["tertiary"], True),
        ]
        for name, tier, time, status, col, is_expired in feed_data:
            row = QHBoxLayout()
            # Member col
            m_col = QHBoxLayout()
            av = QFrame()
            av.setFixedSize(32, 32)
            av.setStyleSheet(f"background: {C['surface_container_high']}; border-radius: 16px;")
            av_l = QVBoxLayout(av)
            av_l.setContentsMargins(0, 0, 0, 0)
            av_lbl = QLabel(name[0])
            av_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-weight: 700; font-size: 12px;")
            av_l.addWidget(av_lbl)
            m_col.addWidget(av)
            m_col.addSpacing(8)
            m_info = QVBoxLayout()
            m_info.setSpacing(2)
            m_n = QLabel(name)
            m_n.setStyleSheet(label_style(11, "on_surface", "medium", FONT_BODY))
            m_t = QLabel(f"Tier: {tier}")
            m_t.setStyleSheet(label_style(8, "on_surface_variant"))
            m_info.addWidget(m_n)
            m_info.addWidget(m_t)
            m_col.addLayout(m_info)
            m_w = QWidget()
            m_w.setLayout(m_col)

            t_lbl = QLabel(time)
            t_lbl.setStyleSheet(label_style(11, "on_surface"))

            s_lbl = QLabel(f"{'⚠' if is_expired else '✓'}  {status}")
            s_lbl.setStyleSheet(f"color: {col}; font-family: '{FONT_BODY}'; font-size: 9px; font-weight: 600;")

            a_col = QHBoxLayout()
            if is_expired:
                ren = QPushButton("RENEW NOW")
                ren.setStyleSheet(f"background: transparent; color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 9px; letter-spacing: 2px; border: none; font-weight: 700;")
                a_col.addWidget(ren)
            else:
                dot = QPushButton("⋮")
                dot.setStyleSheet(f"background: transparent; color: {C['on_surface_variant']}; border: none; font-size: 16px;")
                a_col.addWidget(dot)

            row.addWidget(m_w, 3)
            row.addWidget(t_lbl, 1)
            row.addWidget(s_lbl, 1)
            a_w = QWidget()
            a_w.setLayout(a_col)
            row.addWidget(a_w, 1)
            feed_lay.addLayout(row)

            div2 = QFrame()
            div2.setFixedHeight(1)
            div2.setStyleSheet(f"background: {C['outline_variant']}20;")
            feed_lay.addWidget(div2)

        left.addWidget(feed_card)
        left.addStretch()
        main_row.addLayout(left, 3)

        # Right column
        right = QVBoxLayout()
        right.setSpacing(14)

        # Peak Intensity
        pi_card = QFrame()
        pi_card.setStyleSheet(card_style("surface_container"))
        pi_lay = QVBoxLayout(pi_card)
        pi_lay.setContentsMargins(16, 14, 16, 14)
        pi_lay.setSpacing(8)
        pi_h = QHBoxLayout()
        pi_t = QLabel("PEAK INTENSITY")
        pi_t.setStyleSheet(label_style(10, "on_surface", "bold", FONT_HEADLINE, 1))
        pi_s = QLabel("+12% VS YESTERDAY")
        pi_s.setStyleSheet(label_style(8, "secondary", "medium", FONT_BODY))
        pi_h.addWidget(pi_t)
        pi_h.addStretch()
        pi_h.addWidget(pi_s)
        pi_lay.addLayout(pi_h)
        mini_data = [20, 35, 55, 65, 80, 70, 45, 30]
        mini_chart = BarChart(mini_data, ["08:00", "12:00", "16:00", "20:00", "", "", "", ""], highlight_index=4)
        mini_chart.setFixedHeight(100)
        pi_lay.addWidget(mini_chart)
        right.addWidget(pi_card)

        # System Health
        sh_card = QFrame()
        sh_card.setStyleSheet(card_style("surface_container"))
        sh_lay = QVBoxLayout(sh_card)
        sh_lay.setContentsMargins(16, 14, 16, 14)
        sh_lay.setSpacing(8)
        sh_t = QHBoxLayout()
        sh_i = QLabel("⚡")
        sh_i.setStyleSheet(f"color: {C['secondary']}; font-size: 14px;")
        sh_h = QLabel("SYSTEM HEALTH")
        sh_h.setStyleSheet(label_style(10, "on_surface", "bold", FONT_HEADLINE, 1))
        sh_t.addWidget(sh_i)
        sh_t.addWidget(sh_h)
        sh_t.addStretch()
        sh_lay.addLayout(sh_t)

        for item, status, color in [
            ("QR Scanner 01", "Online", "secondary"),
            ("RFID Receiver", "Online", "secondary"),
            ("Cloud Sync", "2ms Latency", "secondary"),
        ]:
            r = QHBoxLayout()
            il = QLabel(item)
            il.setStyleSheet(label_style(10, "on_surface_variant"))
            sv = QLabel(status)
            sv.setStyleSheet(label_style(10, color, "medium", FONT_BODY))
            r.addWidget(il)
            r.addStretch()
            r.addWidget(sv)
            sh_lay.addLayout(r)

        diag = QPushButton("RUN DIAGNOSTICS")
        diag.setFixedHeight(36)
        diag.setStyleSheet(btn_secondary_style())
        sh_lay.addSpacing(4)
        sh_lay.addWidget(diag)
        right.addWidget(sh_card)

        # Need Assistance
        assist_card = QFrame()
        assist_card.setStyleSheet(f"background: {C['primary_container']}20; border-radius: 6px; border: 1px solid {C['primary']}20;")
        assist_lay = QHBoxLayout(assist_card)
        assist_lay.setContentsMargins(14, 12, 14, 12)
        assist_lay.setSpacing(10)
        ai = QLabel("◈")
        ai.setStyleSheet(f"color: {C['primary']}; font-size: 20px;")
        av2 = QVBoxLayout()
        av2.setSpacing(2)
        an = QLabel("Need Assistance?")
        an.setStyleSheet(label_style(11, "on_surface", "bold", FONT_BODY))
        as_ = QLabel("CONNECT WITH SUPPORT")
        as_.setStyleSheet(label_style(8, "primary", "medium", FONT_HEADLINE, 2))
        av2.addWidget(an)
        av2.addWidget(as_)
        assist_lay.addWidget(ai)
        assist_lay.addLayout(av2)
        assist_lay.addStretch()
        right.addWidget(assist_card)
        right.addStretch()

        main_row.addLayout(right, 2)
        lay.addLayout(main_row)


# ─── PAGE: CHECK-IN ───────────────────────────────────────────────────────────

class QRCheckInPage(QWidget):
    checkin_completed = pyqtSignal()  # Signal emitted when a successful check-in is made
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_member = None
        self.setStyleSheet(f"background: {C['background']};")
        self._build()
        self.refresh_today_checkins()
        self._banner_timer = QTimer(self)
        self._banner_timer.timeout.connect(self._update_checkin_banner_live)
        self._banner_timer.start(1200)
        self._update_checkin_banner_live()

    def _get_latest_today_member_info(self):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        with sqlite3.connect(self.db.db_path) as conn:
            cur = conn.execute(
                """
                SELECT dc.member_id, mr.protocol_name
                FROM daily_checkins dc
                JOIN member_registrations mr ON mr.id = dc.registration_id
                WHERE dc.checkin_date = ? AND dc.registration_id IS NOT NULL
                ORDER BY dc.checkin_time DESC
                LIMIT 1
                """,
                (today,),
            )
            row = cur.fetchone()
        return row if row else None

    def _set_checkin_banner_text(self, top, bottom=""):
        if bottom:
            # Keep two-line real-time data compact and readable.
            max_bottom_len = 24
            compact_bottom = bottom if len(bottom) <= max_bottom_len else f"{bottom[:max_bottom_len-1]}…"
            self.qr_frame_lbl.setText(f"{top}\n{compact_bottom}")
            self.qr_frame_lbl.setStyleSheet(f"""
                color: {C['primary']};
                background: {C['surface_container_lowest']};
                border: 2px solid {C['primary']}CC;
                border-radius: 10px;
                font-family: '{FONT_HEADLINE}';
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 12px;
            """)
        else:
            self.qr_frame_lbl.setText(top)
            self.qr_frame_lbl.setStyleSheet(f"""
                color: {C['primary']};
                background: {C['surface_container_lowest']};
                border: 2px dashed {C['primary']};
                border-radius: 10px;
                font-family: '{FONT_HEADLINE}';
                font-size: 24px;
                font-weight: 700;
                letter-spacing: 3px;
                padding: 8px;
            """)

    def _update_checkin_banner_live(self):
        if not hasattr(self, "qr_frame_lbl"):
            return

        token = self.scan_input.text().strip() if hasattr(self, "scan_input") else ""
        if token:
            member = self.db.find_member_for_checkin(token)
            if member and member.get("member_id"):
                plan = (member.get("protocol_name") or "--").upper()
                self._set_checkin_banner_text("MEMBER ID", f"{member['member_id']} • {plan}")
                return
            self._set_checkin_banner_text("MEMBER ID", "NOT FOUND")
            return

        latest_member_info = self._get_latest_today_member_info()
        if latest_member_info:
            member_id, plan = latest_member_info
            self._set_checkin_banner_text("LATEST CHECK-IN", f"{member_id} • {(plan or '--').upper()}")

            # Keep member info card updated in real time when no manual input is being typed.
            if not self.walkin_input.text().strip():
                member = self.db.find_member_for_checkin(member_id)
                if member:
                    self.current_member = member
                    self._populate_member_card(member)
                    status = "ACTIVE" if self._member_is_active(member) else "EXPIRED"
                    self.membership_id_preview_lbl.setText(f"Membership ID: {member['member_id']} ({status})")
        else:
            self._set_checkin_banner_text("CHECK-IN")
            if not self.walkin_input.text().strip():
                self.membership_id_preview_lbl.setText("Membership ID: --")
                self.current_member = None
                self._reset_member_card()

    def _member_is_active(self, member):
        start_date = QDate.fromString(member["cycle_start_date"], "MM/dd/yyyy")
        if not start_date.isValid():
            return True

        if member["protocol_name"] == "Weekly":
            expiry = start_date.addDays(7)
        else:
            expiry = start_date.addMonths(1)
        return QDate.currentDate() <= expiry

    def _set_access_style(self, mode, subtitle):
        if mode == "granted":
            bg = C["secondary_container"]
            fg = C["secondary"]
            icon = "✓"
            title = "ACCESS GRANTED"
        elif mode == "already":
            bg = C["surface_container_high"]
            fg = C["primary"]
            icon = "•"
            title = "ALREADY CHECKED IN"
        else:
            bg = C["tertiary_container"]
            fg = C["tertiary"]
            icon = "⚠"
            title = "ACCESS DENIED"

        self.access_card.setStyleSheet(f"""
            background: {bg};
            border-radius: 8px;
        """)
        self.check_icon.setText(icon)
        self.check_icon.setStyleSheet(f"color: {fg}; font-size: 36px; font-weight: 900;")
        self.ag_lbl.setText(title)
        self.ag_lbl.setStyleSheet(
            f"color: {fg}; font-family: '{FONT_HEADLINE}'; font-size: 18px; font-weight: 800; letter-spacing: 3px;"
        )
        self.ae_lbl.setText(subtitle)
        self.ae_lbl.setStyleSheet(label_style(9, "on_surface", "medium", FONT_HEADLINE, 1))

    def _reset_member_card(self):
        self.member_name_lbl.setText("No member checked in")
        self.member_id_lbl.setText("ID: --")
        self.member_plan_lbl.setText("PLAN: --")
        self.member_start_lbl.setText("START DATE: --")
        self.member_phone_lbl.setText("PHONE: --")

    def _populate_member_card(self, member):
        initials = "".join(part[0] for part in member["full_name"].split() if part)[:2].upper() or "Q8"
        self.avatar_lbl.setText(initials)
        self.member_name_lbl.setText(member["full_name"])
        self.member_id_lbl.setText(f"ID: {member['member_id']}")
        self.member_plan_lbl.setText(f"PLAN: {member['protocol_name']}")
        self.member_start_lbl.setText(f"START DATE: {member['cycle_start_date']}")
        self.member_phone_lbl.setText(f"PHONE: {member['phone']}")

    def _populate_walkin_card(self, walkin_name, walkin_member_id, checkin_date=None, checkin_time=None, checkout_time=None):
        initials = "".join(part[0] for part in walkin_name.split() if part)[:2].upper() or "WI"
        self.avatar_lbl.setText(initials)
        self.member_name_lbl.setText(walkin_name)
        self.member_id_lbl.setText(f"ID: {walkin_member_id}")
        self.member_plan_lbl.setText("PLAN: WALK-IN (TODAY ONLY)" if not checkout_time else "PLAN: WALK-IN (COMPLETED)")

        if checkin_date and checkin_time:
            self.member_start_lbl.setText(f"CHECK-IN: {checkin_date} {checkin_time}")
        elif checkin_date:
            self.member_start_lbl.setText(f"CHECK-IN DATE: {checkin_date}")
        else:
            self.member_start_lbl.setText(f"CHECK-IN DATE: {QDate.currentDate().toString('MM/dd/yyyy')}")

        self.member_phone_lbl.setText(f"CHECK-OUT TIME: {checkout_time or '--'}")

    def _update_walkin_id_preview(self, text):
        clean_name = " ".join((text or "").strip().split())
        if not clean_name:
            self.walkin_id_preview_lbl.setText("Generated ID: --")
            return
        generated_id = self.db.generate_walkin_member_id(clean_name)
        self.walkin_id_preview_lbl.setText(f"Generated ID: {generated_id}")

    def _update_existing_walkin_preview(self, text):
        clean_name = " ".join((text or "").strip().split())
        if not clean_name:
            self.walkin_existing_lbl.setText("Existing today: --")
            self.walkin_existing_lbl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_BODY))
            if not self.scan_input.text().strip():
                self._reset_member_card()
            self._update_checkin_banner_live()
            return

        existing = self.db.get_existing_walkin_checkin(clean_name)
        if not existing:
            self.walkin_existing_lbl.setText("Existing today: none")
            self.walkin_existing_lbl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_BODY))
            return

        checkin_time = existing.get("checkin_time") or "--"
        checkout_time = existing.get("checkout_time")
        if checkout_time:
            self.walkin_existing_lbl.setText(f"Existing today: IN {checkin_time} | OUT {checkout_time}")
            self.walkin_existing_lbl.setStyleSheet(label_style(9, "secondary", "medium", FONT_BODY))
        else:
            self.walkin_existing_lbl.setText(f"Existing today: IN {checkin_time} | save to set OUT")
            self.walkin_existing_lbl.setStyleSheet(label_style(9, "tertiary", "medium", FONT_BODY))

        self._populate_walkin_card(
            existing["member_name"],
            existing["member_id"],
            existing.get("checkin_date"),
            existing.get("checkin_time"),
            existing.get("checkout_time"),
        )

    def _on_walkin_input_changed(self, text):
        self._update_walkin_id_preview(text)
        self._update_existing_walkin_preview(text)

    def _update_membership_id_preview(self, text):
        token = (text or "").strip()
        if not token:
            self.membership_id_preview_lbl.setText("Membership ID: --")
            self.current_member = None
            if not self.walkin_input.text().strip():
                self._reset_member_card()
            self._update_checkin_banner_live()
            return

        member = self.db.find_member_for_checkin(token)
        if not member:
            self.membership_id_preview_lbl.setText("Membership ID: Not found")
            self.current_member = None
            if not self.walkin_input.text().strip():
                self._reset_member_card()
            self._update_checkin_banner_live()
            return

        self.current_member = member
        self._populate_member_card(member)
        status = "ACTIVE" if self._member_is_active(member) else "EXPIRED"
        self.membership_id_preview_lbl.setText(f"Membership ID: {member['member_id']} ({status})")
        self._update_checkin_banner_live()

    def _on_checkin_banner_clicked(self, event):
        token = self.scan_input.text().strip()
        if token:
            self._update_membership_id_preview(token)
            return

        latest_member_info = self._get_latest_today_member_info()
        if not latest_member_info:
            QMessageBox.information(self, "No Member Check-In", "No registered member check-in found for today.")
            return

        latest_member_id, _ = latest_member_info
        self.scan_input.setText(latest_member_id)
        self._update_membership_id_preview(latest_member_id)

    def _save_walkin_checkin(self, walkin_name):
        clean_name = " ".join((walkin_name or "").strip().split())
        if not clean_name:
            QMessageBox.warning(self, "Missing Name", "Enter walk-in name for non-member check-in.")
            return

        existing = self.db.get_existing_walkin_checkin(clean_name)
        if existing:
            existing_checkout_time = existing.get("checkout_time")
            if existing_checkout_time:
                self._populate_walkin_card(
                    existing["member_name"],
                    existing["member_id"],
                    existing.get("checkin_date"),
                    existing.get("checkin_time"),
                    existing_checkout_time,
                )
                self._set_access_style("already", "Walk-in already checked out today")
                QMessageBox.information(
                    self,
                    "Already Checked-Out",
                    f"Walk-in already checked out at {existing_checkout_time}.",
                )
                self.refresh_today_checkins()
                return

            success, message, checkout_time = self.db.record_walkin_checkout(existing["id"])
            if success:
                self._populate_walkin_card(
                    existing["member_name"],
                    existing["member_id"],
                    existing.get("checkin_date"),
                    existing.get("checkin_time"),
                    checkout_time,
                )
                self._set_access_style("granted", f"Walk-in checked out ({existing.get('checkin_time') or '--'} in)")
                QMessageBox.information(self, "Walk-In Checked-Out", message)
                self.refresh_today_checkins()
                self.walkin_input.clear()
                self.scan_input.clear()
                self._update_walkin_id_preview("")
                self._update_existing_walkin_preview("")
                self._update_membership_id_preview("")
                self._update_checkin_banner_live()
                self.checkin_completed.emit()
                return

            self._set_access_style("already", "Walk-in checkout unavailable")
            QMessageBox.information(self, "Walk-In Checkout", message)
            self.refresh_today_checkins()
            return

        success, message, walkin_member_id = self.db.record_walkin_checkin(clean_name)
        if success:
            self._populate_walkin_card(clean_name, walkin_member_id)
            self._set_access_style("granted", "Walk-in checked in for today")
            QMessageBox.information(self, "Walk-In Saved", message)
            self.refresh_today_checkins()
            self.walkin_input.clear()
            self.scan_input.clear()
            self._update_walkin_id_preview("")
            self._update_existing_walkin_preview("")
            self._update_membership_id_preview("")
            self._update_checkin_banner_live()
            # Emit signal to refresh record user page
            self.checkin_completed.emit()
            return

        self._set_access_style("already", "Walk-in already checked in today")
        QMessageBox.information(self, "Already Checked-In", message)
        self.refresh_today_checkins()

    def _handle_check_in(self):
        token = self.scan_input.text().strip()
        walkin_name = self.walkin_input.text().strip()

        if not token and not walkin_name:
            QMessageBox.warning(self, "Missing Input", "Enter member ID/phone or walk-in name.")
            return

        if not token and walkin_name:
            self._save_walkin_checkin(walkin_name)
            return

        member = self.db.find_member_for_checkin(token)
        if not member:
            if walkin_name:
                self._save_walkin_checkin(walkin_name)
                return
            self._set_access_style("denied", "Member not found")
            self._reset_member_card()
            QMessageBox.warning(self, "Not Found", "Member was not found. Enter walk-in name for non-member entry.")
            return

        self.current_member = member
        self._populate_member_card(member)

        if not self._member_is_active(member):
            if walkin_name:
                self._save_walkin_checkin(walkin_name)
                return
            self._set_access_style("denied", "Membership expired")
            QMessageBox.warning(self, "Membership Expired", "Membership is not active. Use walk-in name for today-only check-in.")
            return

        success, message = self.db.record_daily_checkin(member)
        if success:
            self._set_access_style("granted", "Checked in for today")
            QMessageBox.information(self, "Check-In Saved", message)
            self.refresh_today_checkins()
            self.scan_input.clear()
            self.walkin_input.clear()
            self._update_checkin_banner_live()
            # Emit signal to refresh record user page
            self.checkin_completed.emit()
            return

        self._set_access_style("already", "Attendance already saved today")
        QMessageBox.information(self, "Already Checked-In", message)
        self.refresh_today_checkins()

    def refresh_today_checkins(self):
        rows = self.db.get_today_checkins()
        self.today_count_lbl.setText(f"{len(rows)} check-ins today")
        self.today_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.today_table.setItem(r, c, QTableWidgetItem(value))

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        # Left: Check-in area
        left = QVBoxLayout()
        left.setSpacing(14)

        # Status bar
        status_bar = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {C['secondary']}; border-radius: 4px;")
        status_txt = QLabel("CHECK-IN DESK ACTIVE: STATION 04")
        status_txt.setStyleSheet(label_style(9, "secondary", "bold", FONT_HEADLINE, 2))
        status_bar.addWidget(dot)
        status_bar.addSpacing(6)
        status_bar.addWidget(status_txt)
        status_bar.addStretch()
        left.addLayout(status_bar)

        # Check-in banner
        cam = QFrame()
        cam.setMinimumHeight(220)
        cam.setStyleSheet(f"""
            background: {C['surface_container_high']};
            border-radius: 6px;
        """)
        cam_lay = QVBoxLayout(cam)
        cam_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qr_frame = QLabel("CHECK-IN")
        qr_frame.setFixedSize(280, 140)
        qr_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_frame.setWordWrap(True)
        qr_frame.setStyleSheet(f"""
            color: {C['primary']};
            background: {C['surface_container_lowest']};
            border: 2px dashed {C['primary']};
            border-radius: 10px;
            font-family: '{FONT_HEADLINE}';
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 3px;
            padding: 8px;
        """)
        self.qr_frame_lbl = qr_frame
        qr_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        qr_frame.mousePressEvent = self._on_checkin_banner_clicked

        cam_sub = QLabel("Use Member ID/phone for members. Re-enter same walk-in name to save checkout.")
        cam_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_sub.setStyleSheet(f"""
            background: {C['background']}80;
            color: {C['on_surface']};
            font-family: '{FONT_BODY}'; font-size: 11px;
            border-radius: 4px;
            padding: 6px 12px;
        """)

        cam_lay.addWidget(qr_frame, 0, Qt.AlignmentFlag.AlignCenter)
        cam_lay.addWidget(cam_sub, 0, Qt.AlignmentFlag.AlignCenter)
        left.addWidget(cam)

        input_card = QFrame()
        input_card.setStyleSheet(card_style("surface_container"))
        input_lay = QVBoxLayout(input_card)
        input_lay.setContentsMargins(14, 12, 14, 12)
        input_lay.setSpacing(10)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        lookup_card = QFrame()
        lookup_card.setStyleSheet(card_style("surface_container_high"))
        lookup_lay = QVBoxLayout(lookup_card)
        lookup_lay.setContentsMargins(12, 10, 12, 10)
        lookup_lay.setSpacing(6)

        input_title = QLabel("MEMBER LOOKUP")
        input_title.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Member ID / Phone / Name (for active members)")
        self.scan_input.setFixedHeight(40)
        self.scan_input.setStyleSheet(input_style())
        self.scan_input.returnPressed.connect(self._handle_check_in)
        self.scan_input.textChanged.connect(self._update_membership_id_preview)

        self.membership_id_preview_lbl = QLabel("Membership ID: --")
        self.membership_id_preview_lbl.setStyleSheet(label_style(9, "secondary", "medium", FONT_HEADLINE, 1))

        lookup_lay.addWidget(input_title)
        lookup_lay.addWidget(self.scan_input)
        lookup_lay.addWidget(self.membership_id_preview_lbl)

        walkin_title = QLabel("WALK-IN NAME (NO MEMBERSHIP)")
        walkin_title.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_HEADLINE, 1))

        walkin_card = QFrame()
        walkin_card.setStyleSheet(card_style("surface_container_high"))
        walkin_lay = QVBoxLayout(walkin_card)
        walkin_lay.setContentsMargins(12, 10, 12, 10)
        walkin_lay.setSpacing(6)

        self.walkin_input = QLineEdit()
        self.walkin_input.setPlaceholderText("Enter full name for today-only walk-in")
        self.walkin_input.setFixedHeight(40)
        self.walkin_input.setStyleSheet(input_style())
        self.walkin_input.returnPressed.connect(self._handle_check_in)
        self.walkin_input.textChanged.connect(self._on_walkin_input_changed)

        self.walkin_id_preview_lbl = QLabel("Generated ID: --")
        self.walkin_id_preview_lbl.setStyleSheet(label_style(9, "primary", "medium", FONT_HEADLINE, 1))

        self.walkin_existing_lbl = QLabel("Existing today: --")
        self.walkin_existing_lbl.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_BODY))

        walkin_lay.addWidget(walkin_title)
        walkin_lay.addWidget(self.walkin_input)
        walkin_lay.addWidget(self.walkin_id_preview_lbl)
        walkin_lay.addWidget(self.walkin_existing_lbl)

        input_row.addWidget(lookup_card, 1)
        input_row.addWidget(walkin_card, 1)

        checkin_btn = QPushButton("SAVE CHECK-IN / CHECK-OUT")
        checkin_btn.setFixedHeight(42)
        checkin_btn.setStyleSheet(btn_primary_style())
        checkin_btn.clicked.connect(self._handle_check_in)

        input_lay.addLayout(input_row)
        input_lay.addWidget(checkin_btn)
        left.addWidget(input_card)

        # Bottom info row
        info_row = QHBoxLayout()
        info_row.setSpacing(12)
        for title, value, color in [
            ("CHECK-IN MODE", "Daily attendance only", "on_surface"),
            ("SYSTEM HEALTH", "Optimal", "secondary"),
        ]:
            ic = QFrame()
            ic.setStyleSheet(card_style("surface_container"))
            ic_lay = QVBoxLayout(ic)
            ic_lay.setContentsMargins(14, 10, 14, 10)
            ic_lay.setSpacing(4)
            it = QLabel(title)
            it.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 1))
            iv = QLabel(value)
            iv.setStyleSheet(label_style(11, color, "bold", FONT_BODY))
            ic_lay.addWidget(it)
            ic_lay.addWidget(iv)
            info_row.addWidget(ic)
        left.addLayout(info_row)
        left.addStretch()

        # Watermark
        wm = QLabel("QUAD 8")
        wm.setStyleSheet(f"color: {C['surface_container_highest']}; font-family: '{FONT_HEADLINE}'; font-size: 48px; font-weight: 900; font-style: italic;")
        wm.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        left.addWidget(wm)

        lay.addLayout(left, 3)

        # Right: Member info
        right = QVBoxLayout()
        right.setSpacing(14)

        self.access_card = QFrame()
        self.access_card.setStyleSheet(f"""
            background: {C['surface_container_high']};
            border-radius: 8px;
        """)
        access_lay = QVBoxLayout(self.access_card)
        access_lay.setContentsMargins(24, 20, 24, 20)
        access_lay.setSpacing(6)
        access_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.check_icon = QLabel("•")
        self.check_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.check_icon.setStyleSheet(f"color: {C['primary']}; font-size: 36px; font-weight: 900;")
        self.ag_lbl = QLabel("READY TO CHECK-IN")
        self.ag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ag_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 18px; font-weight: 800; letter-spacing: 3px;")
        self.ae_lbl = QLabel("Waiting for member details")
        self.ae_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ae_lbl.setStyleSheet(label_style(9, "on_surface", "medium", FONT_HEADLINE, 1))
        access_lay.addWidget(self.check_icon)
        access_lay.addWidget(self.ag_lbl)
        access_lay.addWidget(self.ae_lbl)
        right.addWidget(self.access_card)

        # Member card
        member_card = QFrame()
        member_card.setStyleSheet(card_style("surface_container"))
        member_lay = QVBoxLayout(member_card)
        member_lay.setContentsMargins(16, 14, 16, 14)
        member_lay.setSpacing(10)

        # Avatar + name
        av_row = QHBoxLayout()
        av_row.setSpacing(12)
        av = QFrame()
        av.setFixedSize(64, 64)
        av.setStyleSheet(f"background: {C['primary_container']}; border-radius: 32px;")
        av_l = QVBoxLayout(av)
        av_l.setContentsMargins(0, 0, 0, 0)
        self.avatar_lbl = QLabel("Q8")
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 18px; font-weight: 800;")
        av_l.addWidget(self.avatar_lbl)

        name_info = QVBoxLayout()
        name_info.setSpacing(4)
        self.member_name_lbl = QLabel("No member checked in")
        self.member_name_lbl.setStyleSheet(label_style(16, "on_surface", "bold", FONT_HEADLINE))
        self.member_id_lbl = QLabel("ID: --")
        self.member_id_lbl.setStyleSheet(label_style(9, "on_surface_variant"))
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        for badge_txt, bg, fg in [("MEMBER", C["secondary_container"], C["secondary"]), ("TODAY", C["primary_container"], C["primary"])]:
            b = QLabel(badge_txt)
            b.setFixedHeight(20)
            b.setStyleSheet(f"background: {bg}; color: {fg}; font-family: '{FONT_HEADLINE}'; font-size: 8px; font-weight: 700; border-radius: 10px; padding: 0 8px;")
            badge_row.addWidget(b)
        badge_row.addStretch()
        pill = QLabel("CHECK-IN")
        pill.setFixedHeight(22)
        pill.setStyleSheet(f"background: {C['primary_container']}; color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 8px; font-weight: 700; border-radius: 11px; padding: 0 10px;")

        name_info.addWidget(self.member_name_lbl)
        name_info.addWidget(self.member_id_lbl)
        name_info.addLayout(badge_row)

        av_row.addWidget(av)
        av_row.addLayout(name_info)
        av_row.addStretch()
        av_row.addWidget(pill, 0, Qt.AlignmentFlag.AlignTop)
        member_lay.addLayout(av_row)

        # Member attendance details
        ps_row = QHBoxLayout()
        ps_t = QLabel("ATTENDANCE STATUS")
        ps_t.setStyleSheet(label_style(9, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        ps_v = QLabel("TODAY")
        ps_v.setStyleSheet(label_style(14, "secondary", "bold", FONT_HEADLINE))
        ps_row.addWidget(ps_t)
        ps_row.addStretch()
        ps_row.addWidget(ps_v)
        member_lay.addLayout(ps_row)

        heatmap = WeekHeatmap([2, 4, 3, 4, 3, 5, 4])
        member_lay.addWidget(heatmap)

        # Plan info
        plan_card = QFrame()
        plan_card.setStyleSheet(card_style("surface_container_high"))
        plan_lay = QVBoxLayout(plan_card)
        plan_lay.setContentsMargins(12, 10, 12, 10)
        plan_lay.setSpacing(6)
        pr = QHBoxLayout()
        star = QLabel("●")
        star.setStyleSheet(f"color: {C['primary']}; font-size: 12px;")
        pn = QLabel("MEMBER INFO")
        pn.setStyleSheet(label_style(10, "on_surface", "bold", FONT_HEADLINE, 1))
        pe = QLabel(QDate.currentDate().toString("yyyy-MM-dd"))
        pe.setStyleSheet(label_style(9, "on_surface_variant"))
        pr.addWidget(star)
        pr.addSpacing(4)
        pr.addWidget(pn)
        pr.addStretch()
        pr.addWidget(pe)
        plan_lay.addLayout(pr)

        self.member_plan_lbl = QLabel("PLAN: --")
        self.member_plan_lbl.setStyleSheet(label_style(9, "on_surface", "medium"))
        self.member_start_lbl = QLabel("START DATE: --")
        self.member_start_lbl.setStyleSheet(label_style(9, "on_surface", "medium"))
        self.member_phone_lbl = QLabel("PHONE: --")
        self.member_phone_lbl.setStyleSheet(label_style(9, "on_surface", "medium"))
        plan_lay.addWidget(self.member_plan_lbl)
        plan_lay.addWidget(self.member_start_lbl)
        plan_lay.addWidget(self.member_phone_lbl)

        member_lay.addWidget(plan_card)
        right.addWidget(member_card)

        logs_card = QFrame()
        logs_card.setStyleSheet(card_style("surface_container"))
        logs_lay = QVBoxLayout(logs_card)
        logs_lay.setContentsMargins(14, 12, 14, 12)
        logs_lay.setSpacing(8)

        logs_head = QHBoxLayout()
        logs_title = QLabel("TODAY CHECK-INS")
        logs_title.setStyleSheet(label_style(10, "on_surface", "bold", FONT_HEADLINE, 1))
        self.today_count_lbl = QLabel("0 check-ins today")
        self.today_count_lbl.setStyleSheet(label_style(9, "on_surface_variant"))
        logs_head.addWidget(logs_title)
        logs_head.addStretch()
        logs_head.addWidget(self.today_count_lbl)
        logs_lay.addLayout(logs_head)

        self.today_table = QTableWidget()
        self.today_table.setColumnCount(3)
        self.today_table.setHorizontalHeaderLabels(["Member", "Member ID", "Time"])
        self.today_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.today_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.today_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.today_table.verticalHeader().setVisible(False)
        self.today_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.today_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.today_table.setStyleSheet(f"""
            QTableWidget {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                border: 1px solid {C['outline_variant']}66;
                border-radius: 6px;
                gridline-color: {C['outline_variant']}33;
            }}
            QHeaderView::section {{
                background: {C['surface_container_high']};
                color: {C['on_surface_variant']};
                border: none;
                padding: 6px;
                font-size: 9px;
                font-weight: 700;
            }}
        """)
        logs_lay.addWidget(self.today_table)
        right.addWidget(logs_card)
        right.addStretch()

        lay.addLayout(right, 2)


# ─── PAGE: REPORTS ────────────────────────────────────────────────────────────

class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C['background']};")
        self._build()

    def _build(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; }")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        # Header
        h1 = QLabel("Performance")
        h1.setStyleSheet(f"color: {C['on_surface']}; font-family: '{FONT_HEADLINE}'; font-size: 36px; font-weight: 700;")
        h2 = QLabel("Intelligence")
        h2.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 36px; font-weight: 700; font-style: italic;")
        sub = QLabel("Real-time data synchronization from the kinetic engine. Analyzing membership velocity and floor occupancy patterns.")
        sub.setStyleSheet(label_style(10, "on_surface_variant"))
        sub.setWordWrap(True)

        header_top = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        t_row = QHBoxLayout()
        t_row.setSpacing(8)
        t_row.addWidget(h1)
        t_row.addWidget(h2)
        t_row.addStretch()
        title_col.addLayout(t_row)
        title_col.addWidget(sub)
        header_top.addLayout(title_col, 3)

        # Filter
        filter_card = QFrame()
        filter_card.setStyleSheet(card_style("surface_container"))
        filter_card.setFixedHeight(56)
        fl = QHBoxLayout(filter_card)
        fl.setContentsMargins(12, 8, 8, 8)
        fl.setSpacing(8)
        date_lbl = QLabel("OCT 01 - OCT 31, 2023")
        date_lbl.setStyleSheet(label_style(9, "on_surface", "medium"))
        fl.addWidget(date_lbl)
        fl.addStretch()
        filter_btn = QPushButton("FILTER")
        filter_btn.setFixedHeight(34)
        filter_btn.setStyleSheet(btn_primary_style())
        fl.addWidget(filter_btn)
        header_top.addWidget(filter_card, 1, Qt.AlignmentFlag.AlignTop)

        lay.addLayout(header_top)

        # Mid row: Chart + Tier Mix
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        chart_card = QFrame()
        chart_card.setStyleSheet(card_style("surface_container"))
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(20, 18, 20, 18)
        chart_lay.setSpacing(10)

        ch = QHBoxLayout()
        ct = QLabel("Monthly Velocity")
        ct.setStyleSheet(label_style(15, "on_surface", "bold", FONT_HEADLINE))
        cs = QLabel("CHECK-IN FREQUENCY DISTRIBUTION")
        ch.addWidget(ct)
        ch.addStretch()
        legend = QHBoxLayout()
        for dot_c, lbl in [(C["secondary"], "ACTUAL"), (C["on_surface_variant"] + "60", "PROJECTED")]:
            d = QFrame()
            d.setFixedSize(8, 8)
            d.setStyleSheet(f"background: {dot_c}; border-radius: 4px;")
            l = QLabel(lbl)
            l.setStyleSheet(label_style(8, "on_surface_variant"))
            legend.addWidget(d)
            legend.addSpacing(2)
            legend.addWidget(l)
            legend.addSpacing(8)
        ch.addLayout(legend)
        chart_lay.addLayout(ch)
        chart_lay.addWidget(QLabel("CHECK-IN FREQUENCY DISTRIBUTION", styleSheet=label_style(8, "on_surface_variant", "normal", FONT_HEADLINE, 2)))

        vel_data = [35, 58, 72, 42, 30, 48, 38]
        vel_labels = ["WK 01", "WK 02", "WK 03", "WK 04", "", "FUTURE", ""]
        vel_chart = BarChart(vel_data, vel_labels, highlight_index=2)
        vel_chart.setMinimumHeight(160)
        chart_lay.addWidget(vel_chart)
        mid_row.addWidget(chart_card, 3)

        # Tier Mix
        tier_card = QFrame()
        tier_card.setStyleSheet(card_style("surface_container"))
        tier_lay = QVBoxLayout(tier_card)
        tier_lay.setContentsMargins(18, 16, 18, 16)
        tier_lay.setSpacing(10)
        tier_t = QLabel("Tier Mix")
        tier_t.setStyleSheet(label_style(14, "on_surface", "bold", FONT_HEADLINE))
        tier_s = QLabel("ASSET ALLOCATION")
        tier_s.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 2))
        tier_lay.addWidget(tier_t)
        tier_lay.addWidget(tier_s)

        for name, pct, color in [("ELITE", 42, "primary"), ("STANDARD", 48, "secondary"), ("TRIAL", 10, "tertiary")]:
            tr = QHBoxLayout()
            tl = QLabel(name)
            tl.setStyleSheet(label_style(9, color, "bold", FONT_HEADLINE, 1))
            tp = QLabel(f"{pct}%")
            tp.setStyleSheet(label_style(9, "on_surface_variant"))
            tr.addWidget(tl)
            tr.addStretch()
            tr.addWidget(tp)
            tier_lay.addLayout(tr)
            gauge = PowerGauge(pct, 100, name, color)
            tier_lay.addWidget(gauge)
            tier_lay.addSpacing(4)

        total_row = QHBoxLayout()
        total_n = QLabel("1,284")
        total_n.setStyleSheet(label_style(28, "on_surface", "bold", FONT_HEADLINE))
        total_sub = QVBoxLayout()
        total_sub.setSpacing(2)
        ts1 = QLabel("TOTAL ACTIVE")
        ts1.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        ts2 = QLabel("+12% vs LY")
        ts2.setStyleSheet(label_style(9, "secondary", "bold", FONT_BODY))
        total_sub.addWidget(ts1)
        total_sub.addWidget(ts2)
        total_row.addWidget(total_n)
        total_row.addLayout(total_sub)
        total_row.addStretch()
        tier_lay.addLayout(total_row)
        mid_row.addWidget(tier_card, 2)
        lay.addLayout(mid_row)

        # Bottom row: Donut + Leaderboard
        bot_row = QHBoxLayout()
        bot_row.setSpacing(16)

        # Peak Load
        peak_card = QFrame()
        peak_card.setStyleSheet(card_style("surface_container"))
        peak_lay = QVBoxLayout(peak_card)
        peak_lay.setContentsMargins(18, 16, 18, 16)
        peak_lay.setSpacing(10)
        peak_t = QLabel("Peak Load")
        peak_t.setStyleSheet(label_style(15, "on_surface", "bold", FONT_HEADLINE))
        peak_s = QLabel("DAILY AVERAGE OCCUPANCY")
        peak_s.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 2))
        peak_lay.addWidget(peak_t)
        peak_lay.addWidget(peak_s)

        donut = DonutChart(75, "CAPACITY")
        peak_lay.addWidget(donut, 0, Qt.AlignmentFlag.AlignCenter)

        prime_row = QHBoxLayout()
        prime_row.setSpacing(8)
        for title, value in [("PRIME TIME", "17:30"), ("AVG STAY", "68m")]:
            pc = QFrame()
            pc.setStyleSheet(card_style("surface_container_high"))
            pl = QVBoxLayout(pc)
            pl.setContentsMargins(10, 8, 10, 8)
            pl.setSpacing(2)
            pt = QLabel(title)
            pt.setStyleSheet(label_style(7, "on_surface_variant", "medium", FONT_HEADLINE, 1))
            pv = QLabel(value)
            pv.setStyleSheet(label_style(16, "on_surface", "bold", FONT_HEADLINE))
            pl.addWidget(pt)
            pl.addWidget(pv)
            prime_row.addWidget(pc)
        peak_lay.addLayout(prime_row)
        bot_row.addWidget(peak_card, 1)

        # Top Performance Members
        perf_card = QFrame()
        perf_card.setStyleSheet(card_style("surface_container"))
        perf_lay = QVBoxLayout(perf_card)
        perf_lay.setContentsMargins(18, 16, 18, 16)
        perf_lay.setSpacing(10)
        perf_t = QLabel("Top Performance Members")
        perf_t.setStyleSheet(label_style(15, "on_surface", "bold", FONT_HEADLINE))
        perf_s = QLabel("MONTHLY ACTIVITY INDEX")
        perf_s.setStyleSheet(label_style(8, "on_surface_variant", "medium", FONT_HEADLINE, 2))
        perf_lay.addWidget(perf_t)
        perf_lay.addWidget(perf_s)

        # Header
        cols = ["RANK", "ATHLETE", "CHECK-INS", "TOTAL POWER", ""]
        widths = [1, 3, 2, 3, 1]
        hr = QHBoxLayout()
        for c, w in zip(cols, widths):
            l = QLabel(c)
            l.setStyleSheet(label_style(7, "on_surface_variant", "medium", FONT_HEADLINE, 1))
            hr.addWidget(l, w)
        perf_lay.addLayout(hr)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['outline_variant']}30;")
        perf_lay.addWidget(div)

        members = [
            ("#01", "Marcus Thorne", "ELITE MEMBER", 28, 9.8, C["secondary"]),
            ("#02", "Elena Rodriguez", "ELITE MEMBER", 26, 9.2, C["secondary"]),
            ("#03", "Jameson Void", "STANDARD MEMBER", 24, 8.9, C["primary"]),
        ]
        for rank, name, tier, sessions, score, col in members:
            mr = QHBoxLayout()
            rk = QLabel(rank)
            rk.setStyleSheet(label_style(11, "primary", "bold", FONT_HEADLINE))

            av = QFrame()
            av.setFixedSize(32, 32)
            av.setStyleSheet(f"background: {C['surface_container_high']}; border-radius: 16px;")
            av_l = QVBoxLayout(av)
            av_l.setContentsMargins(0, 0, 0, 0)
            av_lbl = QLabel(name[0])
            av_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av_lbl.setStyleSheet(f"color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-weight: 700; font-size: 12px;")
            av_l.addWidget(av_lbl)

            info = QVBoxLayout()
            info.setSpacing(2)
            nl = QLabel(name)
            nl.setStyleSheet(label_style(11, "on_surface", "medium", FONT_BODY))
            tl = QLabel(tier)
            tl.setStyleSheet(label_style(7, "on_surface_variant"))
            info.addWidget(nl)
            info.addWidget(tl)

            sessions_col = QVBoxLayout()
            sessions_col.setSpacing(2)
            sl = QLabel(f"{sessions}")
            sl.setStyleSheet(label_style(12, "on_surface", "bold", FONT_HEADLINE))
            ss = QLabel("Sessions")
            ss.setStyleSheet(label_style(7, "on_surface_variant"))
            sessions_col.addWidget(sl)
            sessions_col.addWidget(ss)

            # Score bar
            score_col = QHBoxLayout()
            score_col.setSpacing(6)
            sg = PowerGauge(int(score * 10), 100, "", "secondary")
            sg.setFixedWidth(80)
            sv = QLabel(f"{score}")
            sv.setStyleSheet(label_style(11, "on_surface", "bold", FONT_HEADLINE))
            score_col.addWidget(sg)
            score_col.addWidget(sv)

            pill_c = QLabel("CR")
            pill_c.setFixedHeight(18)
            pill_c.setStyleSheet(f"background: {C['secondary_container']}; color: {C['secondary']}; font-size: 7px; font-weight: 700; border-radius: 9px; padding: 0 6px;")

            av_w = QWidget()
            av_w.setLayout(QHBoxLayout())
            av_w.layout().setContentsMargins(0, 0, 0, 0)
            av_w.layout().setSpacing(6)
            av_w.layout().addWidget(av)
            info_w = QWidget()
            info_w.setLayout(info)
            av_w.layout().addWidget(info_w)

            score_w = QWidget()
            score_w.setLayout(score_col)

            mr.addWidget(rk, 1)
            mr.addWidget(av_w, 3)
            sessions_w = QWidget()
            sessions_w.setLayout(sessions_col)
            mr.addWidget(sessions_w, 2)
            mr.addWidget(score_w, 3)
            mr.addWidget(pill_c, 1)
            perf_lay.addLayout(mr)
            d2 = QFrame()
            d2.setFixedHeight(1)
            d2.setStyleSheet(f"background: {C['outline_variant']}20;")
            perf_lay.addWidget(d2)

        view_all = QPushButton("VIEW ALL PERFORMANCE METRICS")
        view_all.setStyleSheet(f"background: transparent; color: {C['primary']}; font-family: '{FONT_HEADLINE}'; font-size: 9px; letter-spacing: 2px; border: none; font-weight: 700;")
        perf_lay.addWidget(view_all, 0, Qt.AlignmentFlag.AlignCenter)
        bot_row.addWidget(perf_card, 2)

        lay.addLayout(bot_row)

        # KPI bar
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        kpis = [
            ("CHURN RISK", "3.2%", "-0.8%", "tertiary"),
            ("REVENUE VELOCITY", "₱128k", "+14%", "secondary"),
            ("EQUIPMENT UTILIZATION", "92%", "MAX LOAD", "primary"),
            ("NEW ENROLLMENTS", "142", "+22", "secondary"),
        ]
        for title, val, sub, col in kpis:
            kc = QFrame()
            kc.setStyleSheet(card_style("surface_container"))
            kl = QVBoxLayout(kc)
            kl.setContentsMargins(14, 12, 14, 12)
            kl.setSpacing(4)
            kt = QLabel(title)
            kt.setStyleSheet(label_style(7, "on_surface_variant", "medium", FONT_HEADLINE, 1))
            kv = QLabel(val)
            kv.setStyleSheet(label_style(22, "on_surface", "bold", FONT_HEADLINE))
            ks = QLabel(sub)
            ks.setStyleSheet(label_style(8, col, "medium", FONT_BODY))
            kl.addWidget(kt)
            kl.addWidget(kv)
            kl.addWidget(ks)
            kpi_row.addWidget(kc)
        lay.addLayout(kpi_row)
        lay.addStretch()


# ─── RECORD USER PAGE: CHECK-IN RECORDS ──────────────────────────────────────

class RecordUserPage(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setStyleSheet(f"background: {C['background']};")
        self.current_filter = "ALL"  # ALL, MEMBERSHIP, WALKIN
        self.period_filter = "Overall"  # Overall, Weekly, Monthly
        self._build()
        self.refresh_records()

    def get_date_filter(self):
        """Get date filter based on period"""
        if self.period_filter == "Weekly":
            from datetime import datetime, timedelta
            return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        elif self.period_filter == "Monthly":
            from datetime import datetime, timedelta
            return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        return None

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("◈  CHECK-IN RECORDS")
        title.setStyleSheet(label_style(24, "on_surface", "bold", FONT_HEADLINE, 1))
        self.count_lbl = QLabel("0 records")
        self.count_lbl.setStyleSheet(label_style(10, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.count_lbl)
        lay.addLayout(title_row)

        # Period filter row
        self.period_row_widget = QWidget()
        period_row = QHBoxLayout(self.period_row_widget)
        period_row.setContentsMargins(0, 0, 0, 0)
        period_row.addStretch()
        self.period_lbl = QLabel("Period: ")
        self.period_lbl.setStyleSheet(label_style(10, "on_surface_variant", "medium", FONT_BODY))
        period_row.addWidget(self.period_lbl)

        self.period_combo = QComboBox()
        self.period_combo.addItems(["Overall", "Weekly", "Monthly"])
        self.period_combo.setCurrentText(self.period_filter)
        self.period_combo.setFixedWidth(130)
        self.period_combo.setFixedHeight(32)
        self.period_combo.setStyleSheet(f"""
            QComboBox {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                font-family: '{FONT_BODY}';
                font-size: 10px;
                border: 1px solid {C['outline_variant']};
                border-radius: 4px;
                padding: 4px 8px;
                padding-right: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
                background: transparent;
                border-left: 1px solid {C['outline_variant']};
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
                width: 12px;
                height: 8px;
                background: transparent;
                margin-right: 4px;
            }}
            QComboBox::down-arrow:on {{
                top: 2px;
            }}
            QAbstractItemView {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                selection-background-color: {C['primary_container']};
                border: 1px solid {C['outline_variant']};
                border-radius: 4px;
                outline: none;
            }}
            QAbstractItemView::item:hover {{
                background-color: {C['surface_container_high']};
            }}
            QAbstractItemView::item:selected {{
                background-color: {C['primary_container']};
                color: {C['on_primary']};
            }}
        """)
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        period_row.addWidget(self.period_combo)
        lay.addWidget(self.period_row_widget)

        # Date filter row
        date_filter_row = QHBoxLayout()
        date_filter_row.addStretch()
        
        date_lbl = QLabel("Date:")
        date_lbl.setStyleSheet(label_style(10, "on_surface_variant", "medium", FONT_BODY))
        date_filter_row.addWidget(date_lbl)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedWidth(140)
        self.date_edit.setFixedHeight(32)
        self.date_edit.setStyleSheet(f"""
            QDateEdit {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                font-family: '{FONT_BODY}';
                font-size: 10px;
                border: 1px solid {C['outline_variant']};
                border-radius: 4px;
                padding: 4px 8px;
                padding-right: 4px;
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 24px;
                background: transparent;
                border-left: 1px solid {C['outline_variant']};
            }}
            QDateEdit::down-arrow {{
                image: none;
                border: none;
                width: 12px;
                height: 8px;
                background: transparent;
                margin-right: 4px;
            }}
            QCalendarWidget {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
            }}
            QCalendarWidget QWidget {{
                color: {C['on_surface']};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {C['on_surface']};
                background: {C['surface_container_low']};
                alternate-background-color: {C['surface_container_high']};
                gridline-color: {C['outline_variant']};
            }}
            QCalendarWidget QAbstractItemView:enabled:hover {{
                background-color: {C['surface_container_high']};
            }}
            QCalendarWidget QAbstractItemView:enabled:selected {{
                background-color: {C['primary_container']};
            }}
        """)
        self.date_edit.dateChanged.connect(self.refresh_records)
        date_filter_row.addWidget(self.date_edit)
        date_filter_row.addSpacing(20)
        lay.addLayout(date_filter_row)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(14)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or ID...")
        self.search_input.setFixedHeight(38)
        self.search_input.setFixedWidth(300)
        self.search_input.setStyleSheet(input_style())
        self.search_input.textChanged.connect(self.refresh_records)
        filter_row.addWidget(self.search_input)

        filter_row.addSpacing(20)

        # Filter type combo box
        filter_label = QLabel("FILTER:")
        filter_label.setStyleSheet(label_style(10, "on_surface_variant", "medium", FONT_HEADLINE, 1))
        filter_row.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Check-ins", "Membership", "Walk-in"])
        self.filter_combo.setFixedWidth(140)
        self.filter_combo.setFixedHeight(38)
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                font-family: '{FONT_BODY}';
                font-size: 10px;
                border: 1px solid {C['outline_variant']};
                border-radius: 4px;
                padding: 6px 8px;
                padding-right: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
                background: transparent;
                border-left: 1px solid {C['outline_variant']};
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
                width: 12px;
                height: 8px;
                background: transparent;
                margin-right: 4px;
            }}
            QComboBox::down-arrow:on {{
                top: 2px;
            }}
            QAbstractItemView {{
                background: {C['surface_container_low']};
                color: {C['on_surface']};
                selection-background-color: {C['primary_container']};
                border: 1px solid {C['outline_variant']};
                border-radius: 4px;
                outline: none;
            }}
            QAbstractItemView::item:hover {{
                background-color: {C['surface_container_high']};
            }}
            QAbstractItemView::item:selected {{
                background-color: {C['primary_container']};
                color: {C['on_primary']};
            }}
        """)
        self.filter_combo.currentTextChanged.connect(self._on_filter_combo_changed)
        filter_row.addWidget(self.filter_combo)

        filter_row.addStretch()

        # Refresh button
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setFixedHeight(38)
        refresh_btn.setStyleSheet(btn_secondary_style())
        refresh_btn.clicked.connect(self.refresh_records)
        filter_row.addWidget(refresh_btn)

        lay.addLayout(filter_row)

        # Records table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Name", "Member ID", "Date", "Check-in Time", "Check-out Time", "Station",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {C['surface_container']};
                alternate-background-color: {C['surface_container_low']};
                color: {C['on_surface']};
                border: 1px solid {C['outline_variant']}66;
                border-radius: 6px;
                gridline-color: {C['outline_variant']}44;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background: {C['surface_container_high']};
                color: {C['on_surface_variant']};
                border: none;
                border-bottom: 1px solid {C['outline_variant']}66;
                padding: 8px;
                font-size: 10px;
                font-weight: 700;
            }}
            QTableWidget::item:selected {{
                background: {C['primary_container']}66;
                color: {C['on_surface']};
            }}
        """)
        lay.addWidget(self.table)

    def _on_filter_combo_changed(self, text):
        """Handle filter combo box change - convert display text to filter type"""
        filter_map = {
            "All Check-ins": "ALL",
            "Membership": "MEMBERSHIP",
            "Walk-in": "WALKIN"
        }
        filter_type = filter_map.get(text, "ALL")
        self._on_filter_changed(filter_type)

    def _on_filter_changed(self, filter_type):
        self.current_filter = filter_type

        # Show period filter only for ALL and MEMBERSHIP.
        show_period = filter_type in ("ALL", "MEMBERSHIP")
        self.period_row_widget.setVisible(show_period)
        if not show_period and self.period_filter != "Overall":
            # Walk-in ignores period; force overall to avoid hidden stale filter.
            self.period_filter = "Overall"
            self.period_combo.setCurrentText("Overall")
        
        # Update table columns based on filter type
        if filter_type == "MEMBERSHIP":
            # Membership: show Name, Member ID, Start Date, Expiration Date, Status
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels([
                "Name", "Member ID", "Start Date", "Expiration Date", "Status",
            ])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        else:
            # ALL and WALKIN: show Name, Member ID, Date, Check-in Time, Check-out Time, Station
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels([
                "Name", "Member ID", "Date", "Check-in Time", "Check-out Time", "Station",
            ])
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.refresh_records()

    def on_period_changed(self, period):
        """Handle period filter change"""
        self.period_filter = period
        self.refresh_records()

    def _membership_status(self, expiration_date):
        expiry = QDate.fromString(expiration_date or "", "MM/dd/yyyy")
        if not expiry.isValid():
            return "INACTIVE"
        return "ACTIVE" if QDate.currentDate() <= expiry else "INACTIVE"

    def refresh_records(self):
        # Get records from database based on filter
        search_text = self.search_input.text().lower().strip()
        all_records = []
        
        selected_qdate = self.date_edit.date()
        selected_date_iso = selected_qdate.toString("yyyy-MM-dd")

        # Normalize legacy date formats (YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, MM/DD/YYYY)
        normalized_checkin_date_expr = """
            CASE
                WHEN instr(checkin_date, '/') > 0 THEN
                    substr(checkin_date, 7, 4) || '-' || substr(checkin_date, 1, 2) || '-' || substr(checkin_date, 4, 2)
                ELSE
                    substr(checkin_date, 1, 10)
            END
        """

        with sqlite3.connect(self.db.db_path) as conn:
            if self.current_filter == "MEMBERSHIP":
                # Show registered members; separate Weekly and Monthly plans.
                if self.period_filter == "Weekly":
                    cur = conn.execute(
                        """
                        SELECT id, full_name, member_id, cycle_start_date, cycle_expiration_date, id
                        FROM member_registrations
                        WHERE protocol_name = 'Weekly'
                        ORDER BY id DESC
                        """,
                    )
                elif self.period_filter == "Monthly":
                    cur = conn.execute(
                        """
                        SELECT id, full_name, member_id, cycle_start_date, cycle_expiration_date, id
                        FROM member_registrations
                        WHERE protocol_name = 'Monthly'
                        ORDER BY id DESC
                        """
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT id, full_name, member_id, cycle_start_date, cycle_expiration_date, id
                        FROM member_registrations
                        ORDER BY id DESC
                        """
                    )
                all_records = cur.fetchall()
                
            elif self.current_filter == "WALKIN":
                # Only walk-in check-ins for the selected date
                cur = conn.execute(
                    f"""
                    SELECT id, member_name, member_id, checkin_date, checkin_time, 
                        checkout_time, station, registration_id
                    FROM daily_checkins
                    WHERE registration_id IS NULL
                    AND {normalized_checkin_date_expr} = ?
                    ORDER BY checkin_time DESC
                    """,
                    (selected_date_iso,),
                )
                all_records = cur.fetchall()
                
            else:  # ALL
                # ALL + Overall: show all check-ins on selected date.
                # ALL + Weekly/Monthly: show date window anchored to selected date.
                where_clause = f"WHERE {normalized_checkin_date_expr} = ?"
                params = (selected_date_iso,)
                if self.period_filter == "Weekly":
                    start_date_iso = selected_qdate.addDays(-6).toString("yyyy-MM-dd")
                    where_clause = f"WHERE {normalized_checkin_date_expr} BETWEEN ? AND ?"
                    params = (start_date_iso, selected_date_iso)
                elif self.period_filter == "Monthly":
                    start_date_iso = selected_qdate.addDays(-29).toString("yyyy-MM-dd")
                    where_clause = f"WHERE {normalized_checkin_date_expr} BETWEEN ? AND ?"
                    params = (start_date_iso, selected_date_iso)

                cur = conn.execute(
                    f"""
                    SELECT id, member_name, member_id, checkin_date, checkin_time, 
                        checkout_time, station, registration_id
                    FROM daily_checkins
                    {where_clause}
                    ORDER BY {normalized_checkin_date_expr} DESC, checkin_time DESC
                    """,
                    params,
                )
                all_records = cur.fetchall()

        # Filter based on search
        filtered_records = []
        for rec in all_records:
            # Unpack based on filter type
            if self.current_filter == "MEMBERSHIP":
                # MEMBERSHIP: id, name, member_id, start_date, expiration_date, reg_id
                rec_id, name, member_id, start_date, expiration_date, reg_id = rec
            else:
                # ALL and WALKIN: checkin_id, name, member_id, date, checkin_time, checkout_time, station, reg_id
                checkin_id, name, member_id, date, checkin_time, checkout_time, station, reg_id = rec
            
            searchable_name = (name or "").lower()
            searchable_member_id = (member_id or "").lower()
            if search_text and search_text not in (searchable_name + searchable_member_id):
                continue
            
            filtered_records.append(rec)

        self.table.setRowCount(len(filtered_records))
        self.count_lbl.setText(f"{len(filtered_records)} records")

        for r, rec in enumerate(filtered_records):
            # Display based on filter type - records have different structures
            if self.current_filter == "MEMBERSHIP":
                # MEMBERSHIP filter records: id, name, member_id, start_date, expiration_date, reg_id
                rec_id, name, member_id, start_date, expiration_date, reg_id = rec
                status = self._membership_status(expiration_date)
                
                values = [
                    name,
                    member_id or "--",
                    start_date or "--",
                    expiration_date or "--",
                    status,
                ]
            else:
                # ALL and WALKIN filter records: checkin_id, name, member_id, date, checkin_time, checkout_time, station, reg_id
                checkin_id, name, member_id, date, checkin_time, checkout_time, station, reg_id = rec
                
                # Parse date and time - handle cases where they might be concatenated
                display_date = date if date else "(Not checked in)"
                display_checkin = checkin_time if checkin_time else "--"
                
                # If date contains a space and checkin_time is empty/null, split them
                if date and " " in date and (not checkin_time or checkin_time == "--"):
                    parts = date.split(" ")
                    display_date = parts[0]  # Get date part
                    if len(parts) > 1:
                        display_checkin = parts[1]  # Get time part
                
                display_checkout = checkout_time or "--"
                
                values = [
                    name,
                    member_id or "--",
                    display_date,
                    display_checkin,
                    display_checkout,
                    station,
                ]
            
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.table.setItem(r, c, item)


# ─── MAIN APP WINDOW ──────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quad 8 GYM — Advanced Management Suite")
        self.setMinimumSize(1200, 800)
        self.resize(1440, 900)
        self.setStyleSheet(f"QMainWindow {{ background: {C['background']}; }}")

        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gymsys.db")
        self.db = RegistrationDatabase(db_path)

        # Central stack: login vs app
        self.root_stack = QStackedWidget()
        self.setCentralWidget(self.root_stack)

        # Login page
        self.login_page = LoginPage()
        self.login_page.login_success.connect(self._on_login)
        self.root_stack.addWidget(self.login_page)

        # App shell
        self.app_shell = QWidget()
        self.app_shell.setStyleSheet(f"background: {C['background']};")
        self._build_app_shell()
        self.root_stack.addWidget(self.app_shell)

        self.root_stack.setCurrentIndex(0)

    def _build_app_shell(self):
        main_lay = QVBoxLayout(self.app_shell)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Top bar - Hidden
        self.top_bar = TopBar("Command Center")
        # main_lay.addWidget(self.top_bar)  # Hidden

        # Body: sidebar + content
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._on_nav)
        self.sidebar.logout_requested.connect(self._on_logout)
        body.addWidget(self.sidebar)

        # Page stack
        self.page_stack = QStackedWidget()
        self.page_stack.setStyleSheet(f"background: {C['background']};")

        self.pages = [
            DashboardPage(self.db),
            RecordUserPage(self.db),
            RegisterPage(self.db),
            QRCheckInPage(self.db),
            ReportsPage(),
        ]
        page_titles = ["Command Center", "Record User", "Register Protocol", "Daily Check-In", "Performance Intelligence"]
        for p in self.pages:
            self.page_stack.addWidget(p)
        
        # Connect RegisterPage signal to refresh dashboard
        register_page = self.pages[2]
        register_page.registration_completed.connect(lambda: self.pages[0].update_stats())
        
        # Connect QRCheckInPage signal to refresh record user page and dashboard stats
        checkin_page = self.pages[3]
        checkin_page.checkin_completed.connect(lambda: self.pages[1].refresh_records())
        checkin_page.checkin_completed.connect(lambda: self.pages[0].update_stats())

        body.addWidget(self.page_stack)

        body_widget = QWidget()
        body_widget.setLayout(body)
        main_lay.addWidget(body_widget)
        self._page_titles = page_titles

    def _on_login(self):
        self.root_stack.setCurrentIndex(1)
        self.pages[0].update_stats()

    def _on_nav(self, idx):
        self.page_stack.setCurrentIndex(idx)
        # self.top_bar.title_lbl.setText(self._page_titles[idx])  # Hidden
        if idx == 0:
            self.pages[0].update_stats()
        if idx == 1:
            self.pages[1].refresh_records()

    def _on_logout(self):
        """Handle logout - return to login page"""
        self.login_page.username.clear()
        self.login_page.password.setText("")
        self.login_page.error_msg.setVisible(False)
        self.root_stack.setCurrentIndex(0)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette base
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(C["background"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(C["on_surface"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(C["surface_container_lowest"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(C["surface_container"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(C["on_surface"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(C["surface_container_high"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(C["on_surface"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(C["primary"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(C["on_primary"]))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()