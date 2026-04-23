from datetime import datetime, timedelta

from PyQt6.QtCore import QDate, QDateTime, QTime

import db_connection
from db_connection import MYSQL_CONFIG


def _parse_any_date(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.split(" ", 1)[0]
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _to_ui_date(value):
    parsed = _parse_any_date(value)
    if not parsed:
        return (str(value).strip() if value is not None else "")
    return parsed.strftime("%m/%d/%Y")


def _to_db_date(value):
    parsed = _parse_any_date(value)
    if not parsed:
        return (str(value).strip() if value is not None else "")
    return parsed.strftime("%Y-%m-%d")


def _to_qdate(value):
    parsed = _parse_any_date(value)
    if not parsed:
        return QDate()
    return QDate(parsed.year, parsed.month, parsed.day)


class RegistrationDatabase:
    def __init__(self, db_path=None):
        self.db_path = db_path or MYSQL_CONFIG["database"]
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
        with db_connection.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS member_registrations (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    full_name VARCHAR(150) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    phone VARCHAR(30) NOT NULL,
                    member_id VARCHAR(40),
                    cycle_start_date DATE NOT NULL,
                    cycle_expiration_date DATE,
                    protocol_name VARCHAR(20) NOT NULL,
                    protocol_price_php DECIMAL(10,2) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    INDEX idx_member_created_at (created_at),
                    INDEX idx_member_phone (phone),
                    INDEX idx_member_member_id (member_id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_checkins (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    registration_id INT UNSIGNED,
                    member_name VARCHAR(150) NOT NULL,
                    member_id VARCHAR(40) NOT NULL,
                    checkin_date DATE NOT NULL,
                    checkin_time TIME NOT NULL,
                    checkout_time TIME,
                    station VARCHAR(40) NOT NULL DEFAULT 'STATION 04',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_member_checkin_per_day (member_id, checkin_date),
                    INDEX idx_checkin_date (checkin_date),
                    INDEX idx_checkin_registration_id (registration_id),
                    CONSTRAINT fk_checkin_registration
                        FOREIGN KEY (registration_id)
                        REFERENCES member_registrations(id)
                        ON DELETE SET NULL
                        ON UPDATE CASCADE
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_inventory (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    product_name VARCHAR(150) NOT NULL,
                    sku VARCHAR(50) NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    quantity_in_stock INT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_product_inventory_sku (sku),
                    INDEX idx_product_name (product_name)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sales_records (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    sale_ref VARCHAR(64) NOT NULL,
                    product_id INT UNSIGNED NOT NULL,
                    quantity INT NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total_price DECIMAL(10,2) NOT NULL,
                    sold_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_sales_ref (sale_ref),
                    INDEX idx_sales_sold_at (sold_at),
                    CONSTRAINT fk_sales_product
                        FOREIGN KEY (product_id)
                        REFERENCES product_inventory(id)
                        ON DELETE RESTRICT
                        ON UPDATE CASCADE
                )
                """
            )

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
        member_id = payload.get("member_id") or self._build_member_id(payload["full_name"], payload["phone"])

        start_date = datetime.strptime(payload["cycle_start_date"], "%m/%d/%Y")
        protocol = payload["protocol_name"]

        if protocol == "Weekly":
            expiration_date = (start_date + timedelta(days=7)).strftime("%Y-%m-%d")
        elif protocol == "Monthly":
            expiration_date = (start_date + timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            expiration_date = start_date.strftime("%Y-%m-%d")

        cycle_start_date_db = start_date.strftime("%Y-%m-%d")

        with db_connection.connect(self.db_path) as conn:
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
                    cycle_start_date_db,
                    expiration_date,
                    payload["protocol_name"],
                    payload["protocol_price_php"],
                ),
            )
            conn.commit()

    def get_registrations(self):
        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, full_name, email, phone, member_id, cycle_start_date,
                    protocol_name, protocol_price_php, created_at
                FROM member_registrations
                ORDER BY id DESC
                """
            )
            rows = cur.fetchall()

        normalized = []
        for row in rows:
            row_list = list(row)
            row_list[5] = _to_ui_date(row_list[5])
            normalized.append(tuple(row_list))
        return normalized

    def find_member_for_checkin(self, search_text):
        token = (search_text or "").strip()
        if not token:
            return None

        normalized_member_id = token.upper()
        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, full_name, email, phone, member_id, cycle_start_date,
                    cycle_expiration_date,
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

            rec_id, full_name, email, phone, member_id, cycle_start_date, cycle_expiration_date, protocol_name, protocol_price_php = row
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
                "cycle_start_date": _to_ui_date(cycle_start_date),
                "cycle_expiration_date": _to_ui_date(cycle_expiration_date),
                "protocol_name": protocol_name,
                "protocol_price_php": protocol_price_php,
            }

    def reactivate_membership(self, member_id, protocol_name, protocol_price_php=None):
        plan = (protocol_name or "").strip()
        if plan not in ("Weekly", "Monthly"):
            return False, "Invalid plan selected."

        plan_prices = {"Weekly": 500.0, "Monthly": 1800.0}
        if protocol_price_php is None:
            protocol_price_php = plan_prices[plan]
        else:
            protocol_price_php = float(protocol_price_php)

        start_date = datetime.now().date()
        if plan == "Weekly":
            expiry_date = start_date + timedelta(days=7)
        else:
            expiry_date = start_date + timedelta(days=30)

        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id
                FROM member_registrations
                WHERE member_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (member_id,),
            )
            row = cur.fetchone()
            if not row:
                return False, "Member not found in membership records."

            rec_id = row[0]
            conn.execute(
                """
                UPDATE member_registrations
                SET cycle_start_date = ?,
                    cycle_expiration_date = ?,
                    protocol_name = ?,
                    protocol_price_php = ?
                WHERE id = ?
                """,
                (
                    start_date.strftime("%Y-%m-%d"),
                    expiry_date.strftime("%Y-%m-%d"),
                    plan,
                    protocol_price_php,
                    rec_id,
                ),
            )
            conn.commit()

        return True, f"Membership reactivated to {plan} until {expiry_date.strftime('%m/%d/%Y')}."

    def record_daily_checkin(self, member, station="STATION 04"):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        now_time = QDateTime.currentDateTime().toString("HH:mm:ss")

        try:
            with db_connection.connect(self.db_path) as conn:
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
        except db_connection.IntegrityError:
            return False, "Already checked in today."

    def record_walkin_checkin(self, walkin_name, station="STATION 04"):
        clean_name = " ".join((walkin_name or "").strip().split())
        if not clean_name:
            return False, "Walk-in name is required."

        today = QDate.currentDate().toString("yyyy-MM-dd")
        now_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        walkin_member_id = self._build_walkin_member_id(clean_name)

        try:
            with db_connection.connect(self.db_path) as conn:
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
        except db_connection.IntegrityError:
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

        with db_connection.connect(self.db_path) as conn:
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

    def record_walkin_checkout(self, checkin_id, checkout_time=None):
        input_time = (checkout_time or "").strip()
        if input_time:
            parsed_time = QTime.fromString(input_time, "HH:mm:ss")
            if not parsed_time.isValid():
                parsed_time = QTime.fromString(input_time, "HH:mm")
            if not parsed_time.isValid():
                return False, "Invalid checkout time. Use HH:MM or HH:MM:SS.", None
            final_checkout_time = parsed_time.toString("HH:mm:ss")
        else:
            final_checkout_time = QDateTime.currentDateTime().toString("HH:mm:ss")

        with db_connection.connect(self.db_path) as conn:
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
                (final_checkout_time, checkin_id),
            )
            conn.commit()

        return True, f"Walk-in check-out saved at {final_checkout_time}.", final_checkout_time

    def get_today_checkins(self):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT member_name, member_id, checkin_time, checkout_time
                FROM daily_checkins
                WHERE checkin_date = ?
                ORDER BY checkin_time DESC
                """,
                (today,),
            )
            return cur.fetchall()

    def get_total_checkins(self):
        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM daily_checkins")
            row = cur.fetchone()
            return row[0] if row else 0

    def get_checkin_totals_per_date(self, days=5):
        today = QDate.currentDate()
        start_date = today.addDays(-(days - 1))
        start_str = start_date.toString("yyyy-MM-dd")
        end_str = today.toString("yyyy-MM-dd")

        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT DATE(created_at) AS avail_date, COUNT(*)
                FROM member_registrations
                WHERE protocol_name IN ('Weekly', 'Monthly')
                AND DATE(created_at) BETWEEN ? AND ?
                GROUP BY DATE(created_at)
                """,
                (start_str, end_str),
            )
            rows = cur.fetchall()

        count_map = {date_str: count for date_str, count in rows}
        labels = []
        values = []
        for i in range(days):
            date = start_date.addDays(i)
            date_str = date.toString("yyyy-MM-dd")
            labels.append(date.toString("MM/dd"))
            values.append(count_map.get(date_str, 0))

        return values, labels, days - 1

    def get_checkins_by_date(self, date_str):
        with db_connection.connect(self.db_path) as conn:
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
        with db_connection.connect(self.db_path) as conn:
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
        with db_connection.connect(self.db_path) as conn:
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

    def get_member_week_checkins(self, member_id):
        today = QDate.currentDate()
        monday = today.addDays(-(today.dayOfWeek() - 1))

        counts = []
        for i in range(7):
            date = monday.addDays(i)
            date_str = date.toString("yyyy-MM-dd")
            with db_connection.connect(self.db_path) as conn:
                cur = conn.execute(
                    """SELECT COUNT(*) FROM daily_checkins WHERE member_id = ? AND checkin_date = ?""",
                    (member_id, date_str),
                )
                count = cur.fetchone()[0]
                counts.append(count if count > 0 else 0)

        return counts

    def get_daily_checkins_past_days(self, days=7):
        today = QDate.currentDate()
        daily_counts = []
        daily_dates = []

        before_days = days // 2
        after_days = days - before_days - 1

        for i in range(-before_days, after_days + 1):
            date = today.addDays(i)
            date_str = date.toString("yyyy-MM-dd")

            with db_connection.connect(self.db_path) as conn:
                cur = conn.execute(
                    """SELECT COUNT(*) FROM daily_checkins WHERE checkin_date = ?""",
                    (date_str,),
                )
                count = cur.fetchone()[0]
                daily_counts.append(count)
                daily_dates.append(date)

        today_index = before_days
        return daily_counts, daily_dates, today_index

    def get_daily_checkins_around_date(self, center_date, days=7):
        daily_counts = []
        daily_dates = []

        before_days = days // 2
        after_days = days - before_days - 1

        for i in range(-before_days, after_days + 1):
            date = center_date.addDays(i)
            date_str = date.toString("yyyy-MM-dd")

            with db_connection.connect(self.db_path) as conn:
                cur = conn.execute(
                    """SELECT COUNT(*) FROM daily_checkins WHERE checkin_date = ?""",
                    (date_str,),
                )
                count = cur.fetchone()[0]
                daily_counts.append(count)
                daily_dates.append(date)

        center_index = before_days
        return daily_counts, daily_dates, center_index

    def get_daily_memberships_around_date(self, center_date, days=7):
        daily_counts = []
        daily_dates = []

        before_days = days // 2
        after_days = days - before_days - 1

        for i in range(-before_days, after_days + 1):
            date = center_date.addDays(i)
            date_str = date.toString("yyyy-MM-dd")

            with db_connection.connect(self.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT COUNT(*) FROM member_registrations
                    WHERE DATE(created_at) = ?
                    """,
                    (date_str,),
                )
                count = cur.fetchone()[0]
                daily_counts.append(count)
                daily_dates.append(date)

        center_index = before_days
        return daily_counts, daily_dates, center_index

    def add_or_update_product(self, product_name, sku, unit_price, quantity_in_stock):
        name = (product_name or "").strip()
        clean_sku = (sku or "").strip().upper()
        if not name:
            return False, "Product name is required."
        if not clean_sku:
            return False, "SKU is required."

        try:
            price = float(unit_price)
            qty = int(quantity_in_stock)
        except (TypeError, ValueError):
            return False, "Unit price and quantity must be numeric values."

        if price < 0:
            return False, "Unit price cannot be negative."
        if qty < 0:
            return False, "Quantity cannot be negative."

        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id
                FROM product_inventory
                WHERE UPPER(sku) = UPPER(?)
                LIMIT 1
                """,
                (clean_sku,),
            )
            existing = cur.fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE product_inventory
                    SET product_name = ?,
                        unit_price = ?,
                        quantity_in_stock = ?
                    WHERE id = ?
                    """,
                    (name, price, qty, existing[0]),
                )
                conn.commit()
                return True, "Product inventory updated."

            conn.execute(
                """
                INSERT INTO product_inventory (
                    product_name, sku, unit_price, quantity_in_stock
                ) VALUES (?, ?, ?, ?)
                """,
                (name, clean_sku, price, qty),
            )
            conn.commit()
            return True, "Product added to inventory."

    def get_inventory_products(self):
        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, product_name, sku, unit_price, quantity_in_stock, updated_at
                FROM product_inventory
                ORDER BY product_name ASC
                """
            )
            return cur.fetchall()

    def get_saleable_products(self):
        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, product_name, sku, unit_price, quantity_in_stock
                FROM product_inventory
                WHERE quantity_in_stock > 0
                ORDER BY product_name ASC
                """
            )
            return cur.fetchall()

    def record_sale(self, product_id, quantity):
        try:
            pid = int(product_id)
            qty = int(quantity)
        except (TypeError, ValueError):
            return False, "Product and quantity are required."

        if qty <= 0:
            return False, "Quantity must be greater than zero."

        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, product_name, sku, unit_price, quantity_in_stock
                FROM product_inventory
                WHERE id = ?
                LIMIT 1
                """,
                (pid,),
            )
            row = cur.fetchone()
            if not row:
                return False, "Selected product was not found."

            _, product_name, sku, unit_price, stock = row
            if qty > int(stock):
                return False, f"Insufficient stock. Available: {stock}."

            unit_price_num = float(unit_price)
            total_price = round(unit_price_num * qty, 2)
            sale_ref = f"SALE-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"

            conn.execute(
                """
                INSERT INTO sales_records (
                    sale_ref, product_id, quantity, unit_price, total_price
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (sale_ref, pid, qty, unit_price_num, total_price),
            )

            conn.execute(
                """
                UPDATE product_inventory
                SET quantity_in_stock = quantity_in_stock - ?
                WHERE id = ?
                """,
                (qty, pid),
            )
            conn.commit()

        return True, f"Sale recorded: {qty} x {product_name} ({sku})"

    def get_sales_records(self, limit=200):
        row_limit = int(limit) if int(limit) > 0 else 200
        with db_connection.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT sr.sale_ref, sr.sold_at, pi.product_name, pi.sku,
                       sr.quantity, sr.unit_price, sr.total_price
                FROM sales_records sr
                JOIN product_inventory pi ON pi.id = sr.product_id
                ORDER BY sr.sold_at DESC
                LIMIT ?
                """,
                (row_limit,),
            )
            return cur.fetchall()

    def get_sales_summary(self):
        with db_connection.connect(self.db_path) as conn:
            overall_cur = conn.execute(
                """
                SELECT COALESCE(SUM(total_price), 0), COUNT(*), COALESCE(SUM(quantity), 0)
                FROM sales_records
                """
            )
            overall = overall_cur.fetchone() or (0, 0, 0)

            today_cur = conn.execute(
                """
                SELECT COALESCE(SUM(total_price), 0), COUNT(*)
                FROM sales_records
                WHERE DATE(sold_at) = CURRENT_DATE
                """
            )
            today = today_cur.fetchone() or (0, 0)

        return {
            "overall_sales_php": float(overall[0] or 0),
            "overall_transactions": int(overall[1] or 0),
            "overall_units": int(overall[2] or 0),
            "today_sales_php": float(today[0] or 0),
            "today_transactions": int(today[1] or 0),
        }
