"""
Construction Manager Pro
KivyMD UI — Android-ready rewrite of Tkinter main.py
database.py and export_utils.py are unchanged.
"""

import os
from datetime import datetime

# ── KivyMD / Kivy imports ────────────────────────────────────────────────────
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList, TwoLineListItem, OneLineListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationLayout
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.spinner import MDSpinner
from kivy.uix.widget import Widget

def MDDivider():
    """Thin horizontal separator line (replaces missing kivymd.uix.divider)."""
    from kivy.uix.boxlayout import BoxLayout
    from kivy.graphics import Color, Rectangle
    w = BoxLayout(size_hint_y=None, height=1)
    with w.canvas.before:
        Color(0.18, 0.30, 0.42, 1)
        rect = Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda *a: setattr(rect, 'pos', w.pos),
           size=lambda *a: setattr(rect, 'size', w.size))
    return w

# ── Local imports (unchanged) ─────────────────────────────────────────────────
import database as db
import export_utils as exp

# ── Constants ─────────────────────────────────────────────────────────────────
ROLES = [
    'Mason', 'Driver', 'Barbender', 'Plant Operator', 'JCB Operator',
    'AJAX Operator', 'Electrician', 'Plumber', 'Painter',
    'Helper', 'Supervisor', 'Engineer', 'Welder', 'Operator', 'Other'
]

ORANGE  = "#e8622a"
AMBER   = "#f49b2e"
NAVY    = "#0d1b2a"
GREEN   = "#4caf7d"
RED     = "#e05252"

# ─────────────────────────────────────────────────────────────────────────────
#  KV STRING  (layout declarations)
# ─────────────────────────────────────────────────────────────────────────────
KV = """
#:import Window kivy.core.window.Window


<SectionTitle@MDLabel>:
    font_style: "H6"
    theme_text_color: "Custom"
    text_color: app.theme_cls.primary_color
    padding: [dp(16), dp(8)]
    size_hint_y: None
    height: self.texture_size[1] + dp(16)

<FieldRow@BoxLayout>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(72)
    padding: [0, dp(4)]

ScreenManager:
    EmployeesScreen:
        name: "employees"
    MaterialsScreen:
        name: "materials"
    DieselScreen:
        name: "diesel"
    CementScreen:
        name: "cement"
    BillingScreen:
        name: "billing"
    SettingsScreen:
        name: "settings"
"""

# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: quick snackbar
# ─────────────────────────────────────────────────────────────────────────────
def snack(msg, color=None):
    sb = Snackbar(text=msg, snackbar_x="8dp", snackbar_y="8dp")
    sb.size_hint_x = 0.95
    if color:
        sb.bg_color = color
    sb.open()


def _field(hint, value="", **kw):
    """Return a styled MDTextField."""
    tf = MDTextField(
        hint_text=hint,
        text=str(value),
        mode="rectangle",
        size_hint_y=None,
        height=dp(56),
        **kw
    )
    return tf


# ─────────────────────────────────────────────────────────────────────────────
#  GENERIC LIST-ROW WIDGET
# ─────────────────────────────────────────────────────────────────────────────
class RowItem(BoxLayout):
    """Coloured row for custom lists/tables."""
    def __init__(self, cells, on_tap=None, even=True, **kw):
        super().__init__(orientation="horizontal",
                         size_hint_y=None, height=dp(40),
                         padding=[dp(8), 0], spacing=dp(4), **kw)
        bg = (0.09, 0.18, 0.27, 1) if even else (0.11, 0.23, 0.34, 1)
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*bg)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        for txt in cells:
            self.add_widget(MDLabel(
                text=str(txt), halign="center",
                theme_text_color="Custom",
                text_color=(0.91, 0.93, 0.95, 1),
                font_style="Body2",
            ))
        if on_tap:
            from kivy.uix.behaviors import ButtonBehavior
            self.bind(on_touch_down=lambda inst, touch:
                      on_tap(inst) if inst.collide_point(*touch.pos) else None)

    def _upd(self, *a):
        self._rect.pos  = self.pos
        self._rect.size = self.size


def table_header(cols):
    """Dark orange header row."""
    box = BoxLayout(orientation="horizontal",
                    size_hint_y=None, height=dp(36),
                    padding=[dp(8), 0], spacing=dp(4))
    with box.canvas.before:
        from kivy.graphics import Color, Rectangle
        Color(0.10, 0.24, 0.37, 1)
        box._rect = Rectangle(pos=box.pos, size=box.size)
    box.bind(pos=lambda *a: setattr(box._rect, 'pos', box.pos),
             size=lambda *a: setattr(box._rect, 'size', box.size))
    for h in cols:
        box.add_widget(MDLabel(
            text=h, halign="center", bold=True,
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            font_style="Caption",
        ))
    return box


# ─────────────────────────────────────────────────────────────────────────────
#  BASE SCREEN  (toolbar + nav drawer link)
# ─────────────────────────────────────────────────────────────────────────────
class BaseScreen(Screen):
    def __init__(self, title, **kw):
        super().__init__(**kw)
        self._title = title
        root = BoxLayout(orientation="vertical")

        # ── Top bar ──
        self.toolbar = MDTopAppBar(
            title=title,
            left_action_items=[["menu", self._open_nav]],
            md_bg_color=MDApp.get_running_app().theme_cls.primary_color,
        )
        root.add_widget(self.toolbar)

        # ── Scrollable body ──
        self.body = BoxLayout(orientation="vertical",
                              padding=[dp(12), dp(8)],
                              spacing=dp(8),
                              size_hint_y=None)
        self.body.bind(minimum_height=self.body.setter("height"))
        sv = ScrollView()
        sv.add_widget(self.body)
        root.add_widget(sv)
        self.add_widget(root)

    def _open_nav(self, *a):
        app = MDApp.get_running_app()
        app.nav_drawer.set_state("open")

    def go(self, screen):
        MDApp.get_running_app().root.current = screen


# ─────────────────────────────────────────────────────────────────────────────
#  EMPLOYEES SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class EmployeesScreen(BaseScreen):
    def __init__(self, **kw):
        super().__init__("👷 Employees", name="employees", **kw)
        self._selected_emp = None
        self._build()

    def _build(self):
        # Search + Add row
        top = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        self.search_tf = MDTextField(hint_text="Search name / role…",
                                     mode="rectangle", size_hint_y=None,
                                     height=dp(48))
        self.search_tf.bind(text=lambda *a: self._load())
        top.add_widget(self.search_tf)
        top.add_widget(MDRaisedButton(
            text="+ ADD", md_bg_color=ORANGE,
            on_release=self._dlg_add_emp,
            size_hint=(None, None), size=(dp(90), dp(48))
        ))
        self.body.add_widget(top)

        # Employee list card
        self.list_card = MDCard(orientation="vertical",
                                padding=dp(4), elevation=2,
                                size_hint_y=None, height=dp(300))
        self.emp_list  = MDList()
        sv = ScrollView()
        sv.add_widget(self.emp_list)
        self.list_card.add_widget(sv)
        self.body.add_widget(self.list_card)

        # Detail card (hidden until employee selected)
        self.detail_card = MDCard(orientation="vertical",
                                  padding=dp(12), elevation=2,
                                  size_hint_y=None, height=dp(0))
        self.body.add_widget(self.detail_card)

        self._load()

    def on_enter(self):
        self._load()

    def _load(self):
        q = self.search_tf.text.lower()
        emps = [e for e in db.get_all_employees()
                if q in e["name"].lower() or q in e["role"].lower()]
        self.emp_list.clear_widgets()
        self._employees = emps
        for emp in emps:
            item = TwoLineListItem(
                text=emp["name"],
                secondary_text=f"{emp['role']}  |  ₹{emp.get('daily_wage',0)}/day",
            )
            item._emp = emp
            item.bind(on_release=self._on_emp_tap)
            self.emp_list.add_widget(item)

    def _on_emp_tap(self, item):
        self._selected_emp = item._emp
        self._show_detail(item._emp)

    def _show_detail(self, emp):
        dc = self.detail_card
        dc.clear_widgets()

        attendance = db.get_attendance(emp["id"])
        fuel_logs  = db.get_fuel_logs(emp["id"])
        settings   = db.get_settings()

        present = sum(1 for a in attendance if a["status"] == "present")
        absent  = sum(1 for a in attendance if a["status"] == "absent")
        half    = sum(1 for a in attendance if a["status"] == "half_day")
        wages   = (present + half * 0.5) * emp.get("daily_wage", 0)

        # Header
        dc.add_widget(MDLabel(
            text=f"[b]{emp['name']}[/b]  —  {emp['role']}",
            markup=True, font_style="H6",
            theme_text_color="Custom", text_color=(0.91, 0.93, 0.95, 1),
            size_hint_y=None, height=dp(36)
        ))
        dc.add_widget(MDLabel(
            text=f"📞 {emp.get('phone','—')}   Joined: {emp.get('joining_date','—')}",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(24)
        ))
        dc.add_widget(MDDivider())

        # Stats row
        stats = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(6))
        for lbl, val, col in [
            ("Present", present, GREEN),
            ("Absent",  absent,  RED),
            ("Half Day",half,    AMBER),
            ("Est. Wages", f"₹{wages:.0f}", ORANGE),
        ]:
            card = MDCard(orientation="vertical", padding=dp(4),
                          md_bg_color=(0.10, 0.24, 0.37, 1))
            card.add_widget(MDLabel(text=str(val), halign="center", bold=True,
                                    theme_text_color="Custom",
                                    text_color=(*[int(col[i:i+2], 16)/255
                                                  for i in (1, 3, 5)], 1)))
            card.add_widget(MDLabel(text=lbl, halign="center", font_style="Caption",
                                    theme_text_color="Secondary"))
            stats.add_widget(card)
        dc.add_widget(stats)

        # Action buttons
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btns.add_widget(MDRaisedButton(
            text="Mark Attendance", md_bg_color=GREEN,
            on_release=lambda *a: self._dlg_attendance(emp)))
        btns.add_widget(MDRaisedButton(
            text="Fuel Entry", md_bg_color=AMBER,
            on_release=lambda *a: self._dlg_fuel(emp)))
        btns.add_widget(MDRaisedButton(
            text="Edit", md_bg_color=NAVY,
            on_release=lambda *a: self._dlg_edit_emp(emp)))
        btns.add_widget(MDRaisedButton(
            text="Delete", md_bg_color=RED,
            on_release=lambda *a: self._confirm_delete(emp)))
        dc.add_widget(btns)

        # Export buttons
        exp_btns = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        exp_btns.add_widget(MDFlatButton(
            text="📄 PDF",
            on_release=lambda *a: self._export_pdf(emp, attendance, fuel_logs, settings)))
        exp_btns.add_widget(MDFlatButton(
            text="📊 Excel",
            on_release=lambda *a: self._export_excel(emp, attendance, fuel_logs, settings)))
        dc.add_widget(exp_btns)

        # Recent attendance table
        if attendance:
            dc.add_widget(MDLabel(text="Recent Attendance", font_style="Subtitle2",
                                  size_hint_y=None, height=dp(28)))
            dc.add_widget(table_header(["Date", "Status", "Notes"]))
            for i, a in enumerate(attendance[:15]):
                dc.add_widget(RowItem(
                    [a["date"], a["status"].replace("_"," ").title(),
                     a.get("notes","") or ""],
                    even=(i % 2 == 0)
                ))

        # Fuel table
        if fuel_logs:
            dc.add_widget(MDLabel(text="Fuel Log", font_style="Subtitle2",
                                  size_hint_y=None, height=dp(28)))
            dc.add_widget(table_header(["Date", "Vehicle", "Litres", "Amount"]))
            for i, f in enumerate(fuel_logs[:15]):
                dc.add_widget(RowItem(
                    [f["date"], f.get("vehicle","-"),
                     f"{f['liters']:.2f}", f"₹{f['amount']:.2f}"],
                    even=(i % 2 == 0)
                ))

        # Resize card to fit content
        dc.height = dc.minimum_height if hasattr(dc, "minimum_height") else dp(500)
        dc.bind(minimum_height=dc.setter("height"))

    # ── Dialogs ──────────────────────────────────────────────────────────────

    def _dlg_add_emp(self, *a):
        self._emp_dlg(None)

    def _dlg_edit_emp(self, emp):
        self._emp_dlg(emp)

    def _emp_dlg(self, emp):
        box = BoxLayout(orientation="vertical", spacing=dp(8),
                        size_hint_y=None, padding=[0, dp(8)])
        box.bind(minimum_height=box.setter("height"))

        tf_name    = _field("Name *",        emp["name"]             if emp else "")
        tf_phone   = _field("Phone",         emp.get("phone","")     if emp else "")
        tf_address = _field("Address",       emp.get("address","")   if emp else "")
        tf_wage    = _field("Daily Wage ₹",  emp.get("daily_wage","")if emp else "",
                            input_filter="float")
        tf_joined  = _field("Joining Date (YYYY-MM-DD)",
                            emp.get("joining_date","")               if emp else
                            datetime.now().strftime("%Y-%m-%d"))

        # Role dropdown
        role_tf = MDTextField(hint_text="Role *",
                              text=emp["role"] if emp else ROLES[0],
                              mode="rectangle", size_hint_y=None, height=dp(56))
        role_items = [{"text": r,
                       "viewclass": "OneLineListItem",
                       "on_release": lambda r=r: _set_role(r)}
                      for r in ROLES]
        role_menu = MDDropdownMenu(caller=role_tf, items=role_items, width_mult=4)

        def _set_role(r):
            role_tf.text = r
            role_menu.dismiss()

        role_tf.bind(focus=lambda inst, foc: role_menu.open() if foc else None)

        for w in [tf_name, role_tf, tf_phone, tf_address, tf_wage, tf_joined]:
            box.add_widget(w)

        sv = ScrollView(size_hint_y=None, height=dp(380))
        sv.add_widget(box)

        def _save(*a):
            name = tf_name.text.strip()
            role = role_tf.text.strip()
            if not name or not role:
                snack("Name and Role are required!", RED); return
            try: wage = float(tf_wage.text or 0)
            except ValueError: snack("Wage must be a number!", RED); return

            if emp:
                db.update_employee(emp["id"], name, role, tf_phone.text,
                                   tf_address.text, wage, tf_joined.text)
                snack("Employee updated ✓", GREEN)
            else:
                db.add_employee(name, role, tf_phone.text,
                                tf_address.text, wage, tf_joined.text)
                snack("Employee added ✓", GREEN)
            dlg.dismiss()
            self._load()

        dlg = MDDialog(
            title="Edit Employee" if emp else "Add Employee",
            type="custom", content_cls=sv,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dlg.dismiss()),
                MDRaisedButton(text="SAVE", md_bg_color=ORANGE, on_release=_save),
            ]
        )
        dlg.open()

    def _dlg_attendance(self, emp):
        box = BoxLayout(orientation="vertical", spacing=dp(8),
                        size_hint_y=None, height=dp(190), padding=[0, dp(8)])
        tf_date   = _field("Date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
        tf_notes  = _field("Notes")
        status_tf = MDTextField(hint_text="Status", text="present",
                                mode="rectangle", size_hint_y=None, height=dp(56))
        statuses  = ["present", "absent", "half_day", "holiday"]
        s_items   = [{"text": s, "viewclass": "OneLineListItem",
                      "on_release": lambda s=s: _set_status(s)}
                     for s in statuses]
        s_menu = MDDropdownMenu(caller=status_tf, items=s_items, width_mult=3)

        def _set_status(s):
            status_tf.text = s; s_menu.dismiss()

        status_tf.bind(focus=lambda inst, foc: s_menu.open() if foc else None)

        for w in [tf_date, status_tf, tf_notes]:
            box.add_widget(w)

        def _save(*a):
            db.add_attendance(emp["id"], tf_date.text.strip(),
                              status_tf.text.strip(), tf_notes.text)
            snack("Attendance saved ✓", GREEN)
            dlg.dismiss()
            self._show_detail(emp)

        dlg = MDDialog(
            title=f"Attendance — {emp['name']}",
            type="custom", content_cls=box,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dlg.dismiss()),
                MDRaisedButton(text="SAVE", md_bg_color=GREEN, on_release=_save),
            ]
        )
        dlg.open()

    def _dlg_fuel(self, emp):
        box = BoxLayout(orientation="vertical", spacing=dp(8),
                        size_hint_y=None, height=dp(270), padding=[0, dp(8)])
        tf_date    = _field("Date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
        tf_vehicle = _field("Vehicle No.")
        tf_liters  = _field("Litres", input_filter="float")
        tf_amount  = _field("Amount ₹", input_filter="float")
        tf_notes   = _field("Notes")

        for w in [tf_date, tf_vehicle, tf_liters, tf_amount, tf_notes]:
            box.add_widget(w)

        def _save(*a):
            try:
                liters = float(tf_liters.text or 0)
                amount = float(tf_amount.text or 0)
            except ValueError:
                snack("Litres and Amount must be numbers!", RED); return
            db.add_fuel_log(emp["id"], tf_date.text.strip(),
                            tf_vehicle.text.strip(), liters, amount, tf_notes.text)
            snack("Fuel entry saved ✓", GREEN)
            dlg.dismiss()
            self._show_detail(emp)

        dlg = MDDialog(
            title=f"Fuel Log — {emp['name']}",
            type="custom", content_cls=box,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dlg.dismiss()),
                MDRaisedButton(text="SAVE", md_bg_color=AMBER, on_release=_save),
            ]
        )
        dlg.open()

    def _confirm_delete(self, emp):
        dlg = MDDialog(
            title="Delete Employee?",
            text=f"Delete '{emp['name']}'? All attendance & fuel logs will be removed.",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dlg.dismiss()),
                MDRaisedButton(text="DELETE", md_bg_color=RED,
                               on_release=lambda *a: self._do_delete(emp, dlg)),
            ]
        )
        dlg.open()

    def _do_delete(self, emp, dlg):
        db.delete_employee(emp["id"])
        dlg.dismiss()
        self.detail_card.clear_widgets()
        self.detail_card.height = dp(0)
        self._load()
        snack("Employee deleted", RED)

    def _export_pdf(self, emp, attendance, fuel_logs, settings):
        path, err = exp.export_employee_pdf(emp, attendance, fuel_logs, settings)
        if err: snack(f"PDF error: {err}", RED)
        else:   snack(f"PDF saved: {path}", GREEN)

    def _export_excel(self, emp, attendance, fuel_logs, settings):
        path, err = exp.export_employee_excel(emp, attendance, fuel_logs, settings)
        if err: snack(f"Excel error: {err}", RED)
        else:   snack(f"Excel saved: {path}", GREEN)


# ─────────────────────────────────────────────────────────────────────────────
#  MATERIALS SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class MaterialsScreen(BaseScreen):
    def __init__(self, **kw):
        super().__init__("🧱 Material Register", name="materials", **kw)
        self._records = []
        self._build()

    def _build(self):
        # Filter row
        frow = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        self.tf_from = MDTextField(hint_text="From date", mode="rectangle",
                                   size_hint_y=None, height=dp(48), size_hint_x=0.3)
        self.tf_to   = MDTextField(hint_text="To date",   mode="rectangle",
                                   size_hint_y=None, height=dp(48), size_hint_x=0.3)
        self.tf_mat  = MDTextField(hint_text="Material",  mode="rectangle",
                                   size_hint_y=None, height=dp(48), size_hint_x=0.4)
        for w in [self.tf_from, self.tf_to, self.tf_mat]: frow.add_widget(w)
        self.body.add_widget(frow)

        # Buttons
        brow = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        for lbl, fn, col in [
            ("🔍 Filter", self._load, ORANGE),
            ("↺ Reset",   self._reset, NAVY),
            ("+ ADD",     self._dlg_add, GREEN),
            ("📄 PDF",    self._export_pdf, AMBER),
            ("📊 Excel",  self._export_excel, AMBER),
        ]:
            brow.add_widget(MDRaisedButton(text=lbl, md_bg_color=col,
                                           on_release=lambda *a, f=fn: f()))
        self.body.add_widget(brow)

        # Summary strip
        self.summary = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(8))
        self.body.add_widget(self.summary)

        # Table
        self.tbl_box = BoxLayout(orientation="vertical",
                                 size_hint_y=None, spacing=dp(1))
        self.tbl_box.bind(minimum_height=self.tbl_box.setter("height"))
        self.body.add_widget(self.tbl_box)

        self._load()

    def on_enter(self): self._load()

    def _load(self):
        self._records = db.get_materials(
            self.tf_from.text or None,
            self.tf_to.text   or None,
            self.tf_mat.text  or None,
        )
        self._refresh_table()
        self._refresh_summary()

    def _reset(self):
        self.tf_from.text = self.tf_to.text = self.tf_mat.text = ""
        self._load()

    def _refresh_summary(self):
        self.summary.clear_widgets()
        total_net = sum(r.get("net_weight", 0) for r in self._records)
        total_amt = sum(r.get("amount", 0)     for r in self._records)
        for lbl, val in [
            ("Records", len(self._records)),
            ("Net Weight", f"{total_net:.2f}"),
            ("Total ₹", f"₹{total_amt:,.2f}"),
        ]:
            c = MDCard(md_bg_color=(0.10, 0.24, 0.37, 1), padding=dp(6))
            c.add_widget(MDLabel(text=str(val), halign="center", bold=True,
                                 theme_text_color="Custom",
                                 text_color=(0.94, 0.61, 0.17, 1)))
            c.add_widget(MDLabel(text=lbl, halign="center", font_style="Caption",
                                 theme_text_color="Secondary"))
            self.summary.add_widget(c)

    def _refresh_table(self):
        self.tbl_box.clear_widgets()
        cols = ["Date", "Material", "Load", "Empty", "Net", "Supplier", "Amount"]
        self.tbl_box.add_widget(table_header(cols))
        for i, m in enumerate(self._records):
            row = RowItem([
                m["date"], m["material_name"],
                f"{m.get('load_weight',0):.1f}",
                f"{m.get('empty_weight',0):.1f}",
                f"{m.get('net_weight',0):.1f}",
                m.get("supplier", "-"),
                f"₹{m.get('amount',0):.0f}",
            ], even=(i % 2 == 0))
            self.tbl_box.add_widget(row)

    def _dlg_add(self):
        box = BoxLayout(orientation="vertical", spacing=dp(8),
                        size_hint_y=None, padding=[0, dp(8)])
        box.bind(minimum_height=box.setter("height"))

        tf = {k: _field(h) for k, h in [
            ("date",     "Date * (YYYY-MM-DD)"),
            ("material", "Material Name *"),
            ("load",     "Load Weight"),
            ("empty",    "Empty Weight"),
            ("net",      "Net Weight (auto)"),
            ("supplier", "Supplier"),
            ("vehicle",  "Vehicle No."),
            ("rate",     "Rate ₹/unit"),
            ("notes",    "Notes"),
        ]}
        tf["date"].text = datetime.now().strftime("%Y-%m-%d")
        tf["net"].readonly = True

        def _calc(*a):
            try:
                n = float(tf["load"].text or 0) - float(tf["empty"].text or 0)
                tf["net"].text = f"{n:.2f}"
            except: pass

        tf["load"].bind(text=_calc)
        tf["empty"].bind(text=_calc)

        sv = ScrollView(size_hint_y=None, height=dp(420))
        for w in tf.values(): box.add_widget(w)
        sv.add_widget(box)

        def _save(*a):
            if not tf["date"].text.strip() or not tf["material"].text.strip():
                snack("Date and Material Name required!", RED); return
            try:
                load = float(tf["load"].text or 0)
                empty= float(tf["empty"].text or 0)
                net  = float(tf["net"].text  or 0)
                rate = float(tf["rate"].text or 0)
            except ValueError:
                snack("Weight/rate must be numbers!", RED); return
            db.add_material(tf["date"].text.strip(), tf["material"].text.strip(),
                            load, empty, net, tf["supplier"].text,
                            tf["vehicle"].text, rate, net * rate, tf["notes"].text)
            snack("Material entry saved ✓", GREEN)
            dlg.dismiss()
            self._load()

        dlg = MDDialog(
            title="Add Material Entry", type="custom", content_cls=sv,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dlg.dismiss()),
                MDRaisedButton(text="SAVE", md_bg_color=ORANGE, on_release=_save),
            ]
        )
        dlg.open()

    def _export_pdf(self):
        s = db.get_settings()
        path, err = exp.export_materials_pdf(self._records, s,
                                             self.tf_from.text, self.tf_to.text)
        snack(f"PDF saved: {path}" if not err else f"PDF error: {err}",
              GREEN if not err else RED)

    def _export_excel(self):
        s = db.get_settings()
        path, err = exp.export_materials_excel(self._records, s,
                                               self.tf_from.text, self.tf_to.text)
        snack(f"Excel saved: {path}" if not err else f"Excel error: {err}",
              GREEN if not err else RED)


# ─────────────────────────────────────────────────────────────────────────────
#  DIESEL FUEL LOG SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class DieselScreen(BaseScreen):
    def __init__(self, **kw):
        super().__init__("⛽ Diesel Fuel Log", name="diesel", **kw)
        self._records    = []
        self._editing_id = None
        self._build()

    def _build(self):
        # ── Entry Form Card ──
        form = MDCard(orientation="vertical", padding=dp(12),
                      elevation=2, size_hint_y=None, height=dp(310))
        form.add_widget(MDLabel(text="Add / Edit Entry", font_style="Subtitle1",
                                theme_text_color="Custom",
                                text_color=(0.94, 0.61, 0.17, 1),
                                size_hint_y=None, height=dp(32)))

        self.tf_date    = _field("Date * (YYYY-MM-DD)",
                                  datetime.now().strftime("%Y-%m-%d"))
        self.tf_vehicle = _field("Vehicle No. *")
        self.tf_qty     = _field("Qty (Litres) *", input_filter="float")
        self.tf_amount  = _field("Amount ₹ *",     input_filter="float")

        for w in [self.tf_date, self.tf_vehicle, self.tf_qty, self.tf_amount]:
            form.add_widget(w)

        self.edit_lbl = MDLabel(text="", font_style="Caption",
                                theme_text_color="Custom",
                                text_color=(0.94, 0.61, 0.17, 1),
                                size_hint_y=None, height=dp(20))
        form.add_widget(self.edit_lbl)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.save_btn = MDRaisedButton(text="💾 SAVE", md_bg_color=ORANGE,
                                       on_release=self._save)
        btn_row.add_widget(self.save_btn)
        btn_row.add_widget(MDFlatButton(text="✖ CLEAR", on_release=self._clear_form))
        form.add_widget(btn_row)
        self.body.add_widget(form)

        # ── Filters ──
        frow = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        self.f_from    = MDTextField(hint_text="From", mode="rectangle",
                                     size_hint_y=None, height=dp(48), size_hint_x=0.3)
        self.f_to      = MDTextField(hint_text="To",   mode="rectangle",
                                     size_hint_y=None, height=dp(48), size_hint_x=0.3)
        self.f_vehicle = MDTextField(hint_text="Vehicle", mode="rectangle",
                                     size_hint_y=None, height=dp(48), size_hint_x=0.4)
        for w in [self.f_from, self.f_to, self.f_vehicle]: frow.add_widget(w)
        self.body.add_widget(frow)

        brow = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        for lbl, fn, col in [
            ("🔍 Filter", self._load, ORANGE),
            ("↺ Reset",  self._reset_filter, NAVY),
            ("📄 PDF",   self._export_pdf, AMBER),
            ("📊 Excel", self._export_excel, AMBER),
        ]:
            brow.add_widget(MDRaisedButton(text=lbl, md_bg_color=col,
                                           on_release=lambda *a, f=fn: f()))
        self.body.add_widget(brow)

        # Summary
        self.summary = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(8))
        self.body.add_widget(self.summary)

        # Table
        self.tbl_box = BoxLayout(orientation="vertical",
                                 size_hint_y=None, spacing=dp(1))
        self.tbl_box.bind(minimum_height=self.tbl_box.setter("height"))
        self.body.add_widget(MDLabel(
            text="Tap a row to edit it",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(20)))
        self.body.add_widget(self.tbl_box)

        self._load()

    def on_enter(self): self._load()

    def _load(self):
        self._records = db.get_diesel_fuels(
            self.f_from.text or None,
            self.f_to.text   or None,
            self.f_vehicle.text or None,
        )
        self._refresh_summary()
        self._refresh_table()

    def _reset_filter(self):
        self.f_from.text = self.f_to.text = self.f_vehicle.text = ""
        self._load()

    def _refresh_summary(self):
        self.summary.clear_widgets()
        total_qty = sum(r["qty_liters"] for r in self._records)
        total_amt = sum(r["amount"]     for r in self._records)
        for lbl, val, col in [
            ("Entries", len(self._records), (0.91,0.93,0.95,1)),
            ("Total Litres", f"{total_qty:.2f} L", (0.94,0.61,0.17,1)),
            ("Total ₹", f"₹{total_amt:,.2f}", (0.91,0.38,0.17,1)),
        ]:
            c = MDCard(md_bg_color=(0.10, 0.24, 0.37, 1), padding=dp(6))
            c.add_widget(MDLabel(text=str(val), halign="center", bold=True,
                                 theme_text_color="Custom", text_color=col))
            c.add_widget(MDLabel(text=lbl, halign="center", font_style="Caption",
                                 theme_text_color="Secondary"))
            self.summary.add_widget(c)

    def _refresh_table(self):
        self.tbl_box.clear_widgets()
        self.tbl_box.add_widget(table_header(["I.No", "Date", "Vehicle", "Litres", "Amount"]))
        for i, r in enumerate(self._records):
            def on_tap(inst, rec=r):
                self._edit_record(rec)
            row = RowItem(
                [r["sl_no"], r["date"], r["vehicle_no"],
                 f"{r['qty_liters']:.2f}", f"₹{r['amount']:.2f}"],
                on_tap=on_tap, even=(i % 2 == 0)
            )
            self.tbl_box.add_widget(row)

    def _edit_record(self, rec):
        self._editing_id      = rec["id"]
        self.tf_date.text    = rec["date"]
        self.tf_vehicle.text = rec["vehicle_no"]
        self.tf_qty.text     = str(rec["qty_liters"])
        self.tf_amount.text  = str(rec["amount"])
        self.save_btn.text   = "✏️ UPDATE"
        self.edit_lbl.text   = f"Editing I.No {rec['sl_no']} — tap UPDATE to save"

    def _save(self, *a):
        date_v   = self.tf_date.text.strip()
        vehicle  = self.tf_vehicle.text.strip()
        if not date_v or not vehicle:
            snack("Date and Vehicle No. required!", RED); return
        try:
            qty    = float(self.tf_qty.text or 0)
            amount = float(self.tf_amount.text or 0)
        except ValueError:
            snack("Qty and Amount must be numbers!", RED); return

        if self._editing_id:
            db.update_diesel_fuel(self._editing_id, date_v, vehicle, qty, amount)
            snack("Entry updated ✓", GREEN)
        else:
            db.add_diesel_fuel(date_v, vehicle, qty, amount)
            snack("Entry saved ✓", GREEN)
        self._clear_form()
        self._load()

    def _clear_form(self, *a):
        self.tf_date.text    = datetime.now().strftime("%Y-%m-%d")
        self.tf_vehicle.text = self.tf_qty.text = self.tf_amount.text = ""
        self._editing_id     = None
        self.save_btn.text   = "💾 SAVE"
        self.edit_lbl.text   = ""

    def _export_pdf(self):
        s = db.get_settings()
        path, err = exp.export_diesel_pdf(self._records, s,
                                          self.f_from.text, self.f_to.text)
        snack(f"PDF: {path}" if not err else f"Error: {err}",
              GREEN if not err else RED)

    def _export_excel(self):
        s = db.get_settings()
        path, err = exp.export_diesel_excel(self._records, s,
                                            self.f_from.text, self.f_to.text)
        snack(f"Excel: {path}" if not err else f"Error: {err}",
              GREEN if not err else RED)


# ─────────────────────────────────────────────────────────────────────────────
#  CEMENT LOG SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class CementScreen(BaseScreen):
    def __init__(self, **kw):
        super().__init__("🪨 Cement Details Log", name="cement", **kw)
        self._records    = []
        self._editing_id = None
        self._build()

    def _build(self):
        # Form card
        form = MDCard(orientation="vertical", padding=dp(12),
                      elevation=2, size_hint_y=None, height=dp(350))
        form.add_widget(MDLabel(text="Add / Edit Entry", font_style="Subtitle1",
                                theme_text_color="Custom",
                                text_color=(0.94, 0.61, 0.17, 1),
                                size_hint_y=None, height=dp(32)))

        self.tf_date    = _field("Date * (YYYY-MM-DD)",
                                  datetime.now().strftime("%Y-%m-%d"))
        self.tf_qty     = _field("Qty (Bags) *",   input_filter="float")
        self.tf_from    = _field("From (Source) *")
        self.tf_to      = _field("To (Destination) *")
        self.tf_details = _field("Details / Notes")

        for w in [self.tf_date, self.tf_qty, self.tf_from,
                  self.tf_to, self.tf_details]:
            form.add_widget(w)

        self.edit_lbl = MDLabel(text="", font_style="Caption",
                                theme_text_color="Custom",
                                text_color=(0.94, 0.61, 0.17, 1),
                                size_hint_y=None, height=dp(20))
        form.add_widget(self.edit_lbl)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.save_btn = MDRaisedButton(text="💾 SAVE", md_bg_color=ORANGE,
                                       on_release=self._save)
        btn_row.add_widget(self.save_btn)
        btn_row.add_widget(MDFlatButton(text="✖ CLEAR", on_release=self._clear_form))
        form.add_widget(btn_row)
        self.body.add_widget(form)

        # Filters
        frow = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        self.f_from = MDTextField(hint_text="From date", mode="rectangle",
                                  size_hint_y=None, height=dp(48), size_hint_x=0.33)
        self.f_to   = MDTextField(hint_text="To date",   mode="rectangle",
                                  size_hint_y=None, height=dp(48), size_hint_x=0.33)
        self.f_loc  = MDTextField(hint_text="Location",  mode="rectangle",
                                  size_hint_y=None, height=dp(48), size_hint_x=0.34)
        for w in [self.f_from, self.f_to, self.f_loc]: frow.add_widget(w)
        self.body.add_widget(frow)

        brow = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        for lbl, fn, col in [
            ("🔍 Filter", self._load, ORANGE),
            ("↺ Reset",  self._reset_filter, NAVY),
            ("📄 PDF",   self._export_pdf, AMBER),
            ("📊 Excel", self._export_excel, AMBER),
        ]:
            brow.add_widget(MDRaisedButton(text=lbl, md_bg_color=col,
                                           on_release=lambda *a, f=fn: f()))
        self.body.add_widget(brow)

        # Summary
        self.summary = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(8))
        self.body.add_widget(self.summary)

        # Table
        self.tbl_box = BoxLayout(orientation="vertical",
                                 size_hint_y=None, spacing=dp(1))
        self.tbl_box.bind(minimum_height=self.tbl_box.setter("height"))
        self.body.add_widget(MDLabel(
            text="Tap a row to edit it",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(20)))
        self.body.add_widget(self.tbl_box)
        self._load()

    def on_enter(self): self._load()

    def _load(self):
        self._records = db.get_cement_logs(
            self.f_from.text or None,
            self.f_to.text   or None,
            self.f_loc.text  or None,
        )
        self._refresh_summary()
        self._refresh_table()

    def _reset_filter(self):
        self.f_from.text = self.f_to.text = self.f_loc.text = ""
        self._load()

    def _refresh_summary(self):
        self.summary.clear_widgets()
        total_qty = sum(r["qty"] for r in self._records)
        for lbl, val in [
            ("Entries", len(self._records)),
            ("Total Bags", f"{total_qty:.0f}"),
        ]:
            c = MDCard(md_bg_color=(0.10, 0.24, 0.37, 1), padding=dp(6))
            c.add_widget(MDLabel(text=str(val), halign="center", bold=True,
                                 theme_text_color="Custom",
                                 text_color=(0.94, 0.61, 0.17, 1)))
            c.add_widget(MDLabel(text=lbl, halign="center", font_style="Caption",
                                 theme_text_color="Secondary"))
            self.summary.add_widget(c)

    def _refresh_table(self):
        self.tbl_box.clear_widgets()
        self.tbl_box.add_widget(table_header(["Date", "Qty", "From", "To", "Details"]))
        for i, r in enumerate(self._records):
            def on_tap(inst, rec=r): self._edit_record(rec)
            row = RowItem(
                [r["date"], f"{r['qty']:.0f}",
                 r.get("from_location","-"), r.get("to_location","-"),
                 (r.get("details","") or "")[:30]],
                on_tap=on_tap, even=(i % 2 == 0)
            )
            self.tbl_box.add_widget(row)

    def _edit_record(self, rec):
        self._editing_id     = rec["id"]
        self.tf_date.text    = rec["date"]
        self.tf_qty.text     = str(rec["qty"])
        self.tf_from.text    = rec.get("from_location","")
        self.tf_to.text      = rec.get("to_location","")
        self.tf_details.text = rec.get("details","") or ""
        self.save_btn.text   = "✏️ UPDATE"
        self.edit_lbl.text   = f"Editing row {rec['id']} — tap UPDATE to save"

    def _save(self, *a):
        date_v   = self.tf_date.text.strip()
        from_loc = self.tf_from.text.strip()
        to_loc   = self.tf_to.text.strip()
        if not date_v or not from_loc or not to_loc:
            snack("Date, From, and To are required!", RED); return
        try:
            qty = float(self.tf_qty.text or 0)
        except ValueError:
            snack("Qty must be a number!", RED); return

        if self._editing_id:
            db.update_cement_log(self._editing_id, date_v, qty,
                                 from_loc, to_loc, self.tf_details.text)
            snack("Entry updated ✓", GREEN)
        else:
            db.add_cement_log(date_v, qty, from_loc, to_loc, self.tf_details.text)
            snack("Entry saved ✓", GREEN)
        self._clear_form()
        self._load()

    def _clear_form(self, *a):
        self.tf_date.text    = datetime.now().strftime("%Y-%m-%d")
        self.tf_qty.text = self.tf_from.text = self.tf_to.text = \
            self.tf_details.text = ""
        self._editing_id   = None
        self.save_btn.text = "💾 SAVE"
        self.edit_lbl.text = ""

    def _export_pdf(self):
        s = db.get_settings()
        path, err = exp.export_cement_pdf(self._records, s,
                                          self.f_from.text, self.f_to.text)
        snack(f"PDF: {path}" if not err else f"Error: {err}",
              GREEN if not err else RED)

    def _export_excel(self):
        s = db.get_settings()
        path, err = exp.export_cement_excel(self._records, s,
                                            self.f_from.text, self.f_to.text)
        snack(f"Excel: {path}" if not err else f"Error: {err}",
              GREEN if not err else RED)


# ─────────────────────────────────────────────────────────────────────────────
#  GST BILLING SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class BillingScreen(BaseScreen):
    def __init__(self, **kw):
        super().__init__("📋 GST Billing", name="billing", **kw)
        self._bills = []
        self._build()

    def _build(self):
        top = BoxLayout(size_hint_y=None, height=dp(44))
        top.add_widget(MDRaisedButton(text="+ NEW BILL", md_bg_color=ORANGE,
                                      on_release=self._dlg_new_bill))
        self.body.add_widget(top)

        self.tbl_box = BoxLayout(orientation="vertical",
                                 size_hint_y=None, spacing=dp(1))
        self.tbl_box.bind(minimum_height=self.tbl_box.setter("height"))
        self.body.add_widget(MDLabel(
            text="Tap a bill to view / export",
            font_style="Caption", theme_text_color="Secondary",
            size_hint_y=None, height=dp(20)))
        self.body.add_widget(self.tbl_box)
        self._load()

    def on_enter(self): self._load()

    def _load(self):
        self._bills = db.get_all_bills()
        self.tbl_box.clear_widgets()
        self.tbl_box.add_widget(table_header(
            ["Bill No", "Date", "Client", "Subtotal", "GST", "Total"]))
        for i, b in enumerate(self._bills):
            def on_tap(inst, bill=b): self._view_bill(bill)
            row = RowItem(
                [b["bill_no"], b["bill_date"], b["client_name"],
                 f"₹{b['subtotal']:.0f}",
                 f"₹{b['cgst_amount']+b['sgst_amount']:.0f}",
                 f"₹{b['total']:.0f}"],
                on_tap=on_tap, even=(i % 2 == 0)
            )
            self.tbl_box.add_widget(row)

    def _view_bill(self, bill_row):
        bill_data, items = db.get_bill_with_items(bill_row["id"])
        settings = db.get_settings()

        box = BoxLayout(orientation="vertical", spacing=dp(6),
                        size_hint_y=None, height=dp(340), padding=[0, dp(8)])

        for lbl, val in [
            ("Bill No",   bill_data["bill_no"]),
            ("Date",      bill_data["bill_date"]),
            ("Client",    bill_data["client_name"]),
            ("GSTIN",     bill_data.get("client_gstin","-")),
            ("Sub Total", f"₹ {bill_data['subtotal']:.2f}"),
            (f"CGST {bill_data['cgst_rate']}%",
             f"₹ {bill_data['cgst_amount']:.2f}"),
            (f"SGST {bill_data['sgst_rate']}%",
             f"₹ {bill_data['sgst_amount']:.2f}"),
            ("GRAND TOTAL", f"₹ {bill_data['total']:.2f}"),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(30))
            row.add_widget(MDLabel(text=f"[b]{lbl}:[/b]", markup=True,
                                   size_hint_x=0.45,
                                   theme_text_color="Secondary"))
            row.add_widget(MDLabel(text=val,
                                   theme_text_color="Custom" if "TOTAL" in lbl else "Primary",
                                   text_color=(0.91,0.38,0.17,1) if "TOTAL" in lbl else (0.91,0.93,0.95,1)))
            box.add_widget(row)

        def _pdf(*a):
            path, err = exp.export_gst_bill_pdf(bill_data, items, settings)
            snack(f"PDF: {path}" if not err else f"Error: {err}",
                  GREEN if not err else RED)
            dlg.dismiss()

        def _excel(*a):
            path, err = exp.export_gst_bill_excel(bill_data, items, settings)
            snack(f"Excel: {path}" if not err else f"Error: {err}",
                  GREEN if not err else RED)
            dlg.dismiss()

        def _delete(*a):
            db.delete_bill(bill_row["id"])
            dlg.dismiss()
            self._load()
            snack("Bill deleted", RED)

        dlg = MDDialog(
            title=f"Bill: {bill_data['bill_no']}",
            type="custom", content_cls=box,
            buttons=[
                MDFlatButton(text="CLOSE",  on_release=lambda *a: dlg.dismiss()),
                MDRaisedButton(text="📄 PDF",   md_bg_color=AMBER,   on_release=_pdf),
                MDRaisedButton(text="📊 Excel", md_bg_color=NAVY,    on_release=_excel),
                MDRaisedButton(text="🗑 DELETE",md_bg_color=RED,     on_release=_delete),
            ]
        )
        dlg.open()

    def _dlg_new_bill(self, *a):
        # Client info fields
        outer = BoxLayout(orientation="vertical", spacing=dp(6),
                          size_hint_y=None, padding=[0, dp(8)])
        outer.bind(minimum_height=outer.setter("height"))

        tf_client = _field("Client Name *")
        tf_addr   = _field("Client Address")
        tf_gstin  = _field("Client GSTIN")
        tf_date   = _field("Bill Date", datetime.now().strftime("%Y-%m-%d"))
        tf_cgst   = _field("CGST %", "9", input_filter="float")
        tf_sgst   = _field("SGST %", "9", input_filter="float")
        tf_notes  = _field("Notes")

        for w in [tf_client, tf_addr, tf_gstin, tf_date, tf_cgst, tf_sgst, tf_notes]:
            outer.add_widget(w)

        # Items
        outer.add_widget(MDLabel(text="─── Bill Items ───", font_style="Subtitle2",
                                 theme_text_color="Custom",
                                 text_color=(0.94, 0.61, 0.17, 1),
                                 size_hint_y=None, height=dp(28)))

        items_box = BoxLayout(orientation="vertical",
                              size_hint_y=None, spacing=dp(4))
        items_box.bind(minimum_height=items_box.setter("height"))
        outer.add_widget(items_box)

        item_rows = []

        def _add_item_row(*a):
            row_box = BoxLayout(orientation="vertical",
                                size_hint_y=None, height=dp(290), spacing=dp(4))
            i_desc = _field("Description *")
            i_hsn  = _field("HSN Code")
            i_qty  = _field("Qty", "1", input_filter="float")
            i_unit = _field("Unit", "Nos")
            i_rate = _field("Rate ₹", input_filter="float")
            i_amt  = MDTextField(hint_text="Amount (auto)", mode="rectangle",
                                 readonly=True, size_hint_y=None, height=dp(48))

            def _calc(*a):
                try:
                    i_amt.text = f"{float(i_qty.text or 1)*float(i_rate.text or 0):.2f}"
                except: pass

            i_qty.bind(text=_calc)
            i_rate.bind(text=_calc)

            def _remove(*a):
                item_rows.remove(item_data)
                items_box.remove_widget(row_box)

            rm_btn = MDFlatButton(text="✕ Remove Item", on_release=_remove)
            for w in [i_desc, i_hsn, i_qty, i_unit, i_rate, i_amt, rm_btn]:
                row_box.add_widget(w)

            item_data = dict(desc=i_desc, hsn=i_hsn, qty=i_qty,
                             unit=i_unit, rate=i_rate)
            item_rows.append(item_data)
            items_box.add_widget(row_box)

        outer.add_widget(MDFlatButton(text="+ ADD ITEM", on_release=_add_item_row))
        _add_item_row()  # start with one row

        sv = ScrollView(size_hint_y=None, height=dp(480))
        sv.add_widget(outer)

        def _save(*a):
            if not tf_client.text.strip():
                snack("Client Name required!", RED); return
            items = []
            for row in item_rows:
                desc = row["desc"].text.strip()
                if not desc: continue
                try:
                    qty  = float(row["qty"].text or 1)
                    rate = float(row["rate"].text or 0)
                except ValueError:
                    snack(f"Invalid qty/rate for: {desc}", RED); return
                items.append(dict(description=desc, hsn_code=row["hsn"].text,
                                  quantity=qty, unit=row["unit"].text or "Nos",
                                  rate=rate, amount=qty*rate))
            if not items:
                snack("Add at least one item!", RED); return
            try:
                cgst = float(tf_cgst.text or 9)
                sgst = float(tf_sgst.text or 9)
            except ValueError:
                cgst = sgst = 9

            bill_no = db.add_gst_bill(
                tf_date.text, tf_client.text,
                tf_addr.text, tf_gstin.text,
                items, cgst, sgst, tf_notes.text
            )
            snack(f"Bill {bill_no} created ✓", GREEN)
            dlg.dismiss()
            self._load()

            # Auto PDF
            bills = db.get_all_bills()
            for b in bills:
                if b["bill_no"] == bill_no:
                    bd, bi = db.get_bill_with_items(b["id"])
                    exp.export_gst_bill_pdf(bd, bi, db.get_settings())
                    break

        dlg = MDDialog(
            title="Create GST Bill", type="custom", content_cls=sv,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dlg.dismiss()),
                MDRaisedButton(text="CREATE BILL", md_bg_color=ORANGE, on_release=_save),
            ]
        )
        dlg.open()


# ─────────────────────────────────────────────────────────────────────────────
#  SETTINGS SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class SettingsScreen(BaseScreen):
    def __init__(self, **kw):
        super().__init__("⚙️ Company Settings", name="settings", **kw)
        self._build()

    def _build(self):
        settings = db.get_settings()
        fields = [
            ("company_name",    "Company Name"),
            ("company_address", "Address"),
            ("company_gstin",   "GSTIN"),
            ("company_phone",   "Phone"),
            ("company_email",   "Email"),
        ]
        self._fields = {}
        for key, hint in fields:
            tf = MDTextField(hint_text=hint, text=settings.get(key,""),
                             mode="rectangle", size_hint_y=None, height=dp(56))
            self._fields[key] = tf
            self.body.add_widget(tf)

        self.body.add_widget(MDRaisedButton(
            text="💾 SAVE SETTINGS", md_bg_color=ORANGE,
            size_hint_y=None, height=dp(48),
            on_release=self._save
        ))

        # Info card
        card = MDCard(orientation="vertical", padding=dp(12),
                      elevation=2, size_hint_y=None, height=dp(120))
        card.add_widget(MDLabel(text="📁 Export Location", font_style="Subtitle2",
                                theme_text_color="Custom",
                                text_color=(0.94, 0.61, 0.17, 1),
                                size_hint_y=None, height=dp(28)))
        card.add_widget(MDLabel(text=exp.get_export_dir(),
                                theme_text_color="Secondary",
                                font_style="Caption"))
        card.add_widget(MDLabel(text="📂 Database: " + db.DB_PATH,
                                theme_text_color="Secondary",
                                font_style="Caption"))
        self.body.add_widget(card)

    def _save(self, *a):
        for key, tf in self._fields.items():
            db.update_setting(key, tf.text)
        snack("Settings saved ✓", GREEN)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class ConstructionApp(MDApp):
    def build(self):
        db.init_db()

        self.theme_cls.primary_palette = "DeepOrange"
        self.theme_cls.primary_hue     = "700"
        self.theme_cls.theme_style     = "Dark"
        self.title = "Construction Manager Pro"

        # Root layout: nav drawer + screen manager
        nav_layout = MDNavigationLayout()

        # Screen manager
        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.add_widget(EmployeesScreen())
        self.sm.add_widget(MaterialsScreen())
        self.sm.add_widget(DieselScreen())
        self.sm.add_widget(CementScreen())
        self.sm.add_widget(BillingScreen())
        self.sm.add_widget(SettingsScreen())

        nav_layout.add_widget(self.sm)

        # Nav drawer
        self.nav_drawer = MDNavigationDrawer(radius=(0, 16, 16, 0))
        drawer_box = BoxLayout(orientation="vertical", spacing=dp(4),
                               padding=[dp(8), dp(12)])

        # Logo
        logo = MDLabel(
            text="🏗️ Construction\nManager Pro",
            font_style="H6", halign="left",
            theme_text_color="Custom",
            text_color=(0.91, 0.38, 0.17, 1),
            size_hint_y=None, height=dp(72)
        )
        drawer_box.add_widget(logo)
        drawer_box.add_widget(MDDivider())

        nav_items = [
            ("employees", "👷 Employees",       "account-hard-hat"),
            ("materials", "🧱 Materials",        "package-variant"),
            ("diesel",    "⛽ Diesel Fuel Log",  "gas-station"),
            ("cement",    "🪨 Cement Log",       "package"),
            ("billing",   "📋 GST Billing",      "receipt"),
            ("settings",  "⚙️ Settings",         "cog"),
        ]

        for screen, label, icon in nav_items:
            item = OneLineListItem(
                text=label,
                on_release=lambda x, s=screen: self._goto(s)
            )
            drawer_box.add_widget(item)

        sv = ScrollView()
        sv.add_widget(drawer_box)
        self.nav_drawer.add_widget(sv)
        nav_layout.add_widget(self.nav_drawer)

        return nav_layout

    def _goto(self, screen):
        self.sm.current = screen
        self.nav_drawer.set_state("close")


def main():
    ConstructionApp().run()


if __name__ == "__main__":
    main()