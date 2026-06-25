"""
pdf_generator.py
تولید گزارش PDF برای تمام پنل‌های سیستم
کتابخانه: reportlab
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Union, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ==================== تابع کمکی برای اطمینان از وجود پوشه ====================
def _ensure_reports_dir():
    """اطمینان از وجود پوشه خروجی reports/output"""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports', 'output')
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return REPORTS_DIR


# ──────────────────────────────────────
#  مسیر پوشه reports (کنار فایل‌های پروژه)
# ──────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports', 'output')
os.makedirs(REPORTS_DIR, exist_ok=True)

# ──────────────────────────────────────
#  فونت: اگر فونت فارسی موجود بود load می‌کنیم
#  وگرنه از Helvetica (latin) استفاده می‌شود
# ──────────────────────────────────────
FONT_NAME = 'Helvetica'   # پیش‌فرض


def _try_register_font():
    """تلاش برای بارگذاری فونت فارسی"""
    global FONT_NAME
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        os.path.join(BASE_DIR, 'assets', 'fonts', 'Vazir.ttf'),
        os.path.join(BASE_DIR, 'assets', 'fonts', 'IRANSans.ttf'),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('CustomFont', path))
                FONT_NAME = 'CustomFont'
                print(f"Font loaded successfully: {path}")
                break
            except Exception as e:
                print(f"Failed to load font {path}: {e}")


_try_register_font()


def _filename(role: str, report_type: str) -> str:
    """ساخت نام فایل استاندارد"""
    _ensure_reports_dir()
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_type = report_type.replace(' ', '_')
    safe_role = role.replace(' ', '_')
    return os.path.join(REPORTS_DIR, f"{safe_role}_{safe_type}_{now}.pdf")


def _get_value(obj: Union[tuple, dict, Any], index: int, key: str, default: str = '—') -> str:
    """
    دریافت مقدار از دیکشنری یا tuple
    - اگر دیکشنری بود با کلید
    - اگر tuple بود با ایندکس
    """
    if isinstance(obj, dict):
        return str(obj.get(key, default))
    elif isinstance(obj, (tuple, list)):
        if index < len(obj):
            return str(obj[index])
        return default
    return str(obj)


def _get_provider_name(obj: Union[tuple, dict], default: str = 'نامشخص') -> str:
    """
    دریافت نام ارائه‌دهنده از دیکشنری یا tuple
    """
    if isinstance(obj, dict):
        # بررسی کلیدهای مختلف
        provider = obj.get('provider_name', '')
        if not provider:
            provider = obj.get('provider', '')
        if not provider:
            provider = obj.get('provider_name_alt', '')
        return provider if provider else default
    elif isinstance(obj, (tuple, list)):
        # اگر tuple بود، ایندکس 2 (محل provider)
        return str(obj[2]) if len(obj) > 2 else default
    return default


def _base_style():
    """بازگرداندن استایل‌های پایه"""
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        'NormalRTL',
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
    )
    title_style = ParagraphStyle(
        'TitleRTL',
        fontName=FONT_NAME,
        fontSize=16,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'SubtitleRTL',
        fontName=FONT_NAME,
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#7f8c8d'),
        spaceAfter=4,
    )
    return normal, title_style, subtitle_style


def _build_table(data: List[List], col_widths: List[float], 
                 header_color=colors.HexColor('#2980b9')) -> Table:
    """ساخت جدول با استایل یکنواخت"""
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.HexColor('#f8f9fa'), colors.white]),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ])
    tbl.setStyle(style)
    return tbl


def _doc_header(elements: list, title: str, subtitle: str = ''):
    """اضافه کردن هدر به سند"""
    normal, title_style, subtitle_style = _base_style()
    now_str = datetime.now().strftime('%Y-%m-%d  %H:%M')
    elements.append(Paragraph(title, title_style))
    if subtitle:
        elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Paragraph(f"Generated: {now_str}", subtitle_style))
    elements.append(HRFlowable(width='100%', thickness=1,
                                color=colors.HexColor('#2980b9'), spaceAfter=10))


# ══════════════════════════════════════════════════════════
#  ۱. گزارش رزروهای مشتری
# ══════════════════════════════════════════════════════════
def generate_customer_bookings_report(username: str, 
                                       bookings: List[Union[tuple, dict]]) -> str:
    """
    گزارش رزروهای مشتری
    
    bookings: list of tuples or dicts
        tuple: (id, service_title, provider, start_time, status, payment_status)
        dict: {'id':..., 'service_title':..., 'provider_name':..., ...}
    """
    _ensure_reports_dir()
    filepath = _filename('Customer', 'Bookings_Report')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    _doc_header(elements,
                title='Customer Bookings Report',
                subtitle=f'Customer: {username}')

    # خلاصه
    normal, _, sub = _base_style()
    total = len(bookings)
    
    confirmed = 0
    paid = 0
    pending = 0
    
    for b in bookings:
        status = _get_value(b, 4, 'status')
        payment = _get_value(b, 5, 'payment_status')
        
        if status == 'Confirmed':
            confirmed += 1
        elif status == 'Pending':
            pending += 1
        if payment == 'Paid':
            paid += 1
    
    rejected_canceled = total - confirmed - pending
    
    elements.append(Spacer(1, 6))
    for line in [
        f"Total Bookings: {total}",
        f"Confirmed: {confirmed}    Pending: {pending}    Other: {rejected_canceled}",
        f"Paid: {paid}    Unpaid: {total - paid}",
    ]:
        elements.append(Paragraph(line, normal))
    elements.append(Spacer(1, 12))

    # جدول
    headers = ['ID', 'Service', 'Provider', 'Start Time', 'Status', 'Payment']
    data = [headers]
    
    for b in bookings:
        # استفاده از تابع کمکی برای دریافت نام ارائه‌دهنده
        provider_name = _get_provider_name(b)
        
        data.append([
            _get_value(b, 0, 'id'),
            _get_value(b, 1, 'service_title'),
            provider_name,
            _get_value(b, 3, 'start_time')[:19] if _get_value(b, 3, 'start_time') else '',
            _get_value(b, 4, 'status'),
            _get_value(b, 5, 'payment_status')
        ])

    col_w = [1.2*cm, 5*cm, 3.5*cm, 4.5*cm, 2.5*cm, 2.3*cm]
    elements.append(_build_table(data, col_w))

    doc.build(elements)
    return filepath


# ══════════════════════════════════════════════════════════
#  ۲. فاکتور / رسید پرداخت مشتری
# ══════════════════════════════════════════════════════════
def generate_payment_receipt(username: str, booking_info: dict) -> str:
    """
    booking_info keys:
        booking_id, service_title, provider_name, start_time,
        price, paid_at, status
    """
    _ensure_reports_dir()
    filepath = _filename('Customer', 'Payment_Receipt')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    normal, title_style, sub_style = _base_style()

    # عنوان
    elements.append(Paragraph('PAYMENT RECEIPT', title_style))
    elements.append(Paragraph('Booking & Service Management System', sub_style))
    elements.append(HRFlowable(width='100%', thickness=2,
                                color=colors.HexColor('#27ae60'), spaceAfter=14))

    # دریافت نام ارائه‌دهنده از دیکشنری
    provider_name = booking_info.get('provider_name', '')
    if not provider_name:
        provider_name = booking_info.get('provider', '')
    if not provider_name:
        provider_name = 'نامشخص'

    # اطلاعات رسید
    paid_at = booking_info.get('paid_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    receipt_data = [
        ['Receipt No:', f"REC-{booking_info.get('booking_id', '—')}"],
        ['Issue Date:', str(paid_at)[:19]],
        ['Customer:', str(username)],
        ['Service:', str(booking_info.get('service_title', '—'))],
        ['Provider:', str(provider_name)],
        ['Appointment:', str(booking_info.get('start_time', '—'))[:19]],
        ['Status:', str(booking_info.get('status', '—'))],
    ]
    tbl = Table(receipt_data, colWidths=[5*cm, 11*cm])
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), FONT_NAME),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 20))

    # مبلغ
    price = booking_info.get('price', 0)
    price_tbl = Table(
        [['AMOUNT PAID', f"{price:,.0f}  Toman"]],
        colWidths=[8*cm, 8*cm]
    )
    price_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#27ae60')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(price_tbl)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        'This receipt confirms successful payment. Thank you for your booking.',
        ParagraphStyle('foot', fontName=FONT_NAME, fontSize=9,
                       textColor=colors.HexColor('#7f8c8d'), alignment=TA_CENTER)
    ))

    doc.build(elements)
    return filepath


# ══════════════════════════════════════════════════════════
#  ۳. گزارش خدمات و بازه‌های Provider
# ══════════════════════════════════════════════════════════
def generate_provider_services_report(username: str,
                                       services: List[Union[tuple, dict]],
                                       slots_map: dict) -> str:
    """
    گزارش خدمات و بازه‌های زمانی ارائه‌دهنده
    
    services: list of (id, title, price, duration, status, category) or dict
    slots_map: {service_id: list of slots}
               هر slot می‌تواند tuple یا dict باشد
    """
    _ensure_reports_dir()
    filepath = _filename('Provider', 'Services_Report')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    normal, title_style, sub = _base_style()

    _doc_header(elements,
                title='Provider Services Report',
                subtitle=f'Provider: {username}')

    for svc in services:
        # دریافت اطلاعات سرویس (پشتیبانی از tuple و dict)
        if isinstance(svc, dict):
            sid = svc.get('id')
            title = svc.get('title', '—')
            price = svc.get('price', 0)
            status = svc.get('status', '—')
            category = svc.get('category', 'بدون دسته‌بندی')
        else:
            sid, title, price, duration, status, category = svc
        
        # هدر سرویس
        svc_hdr_style = ParagraphStyle(
            'SvcHdr', fontName=FONT_NAME, fontSize=11,
            textColor=colors.HexColor('#2980b9'),
            spaceAfter=4, spaceBefore=10,
        )
        elements.append(Paragraph(
            f"Service: {title}  |  Price: {price:,.0f} Toman"
            f"  |  Status: {status}  | Category: {category}",
            svc_hdr_style
        ))

        slots = slots_map.get(sid, [])
        if slots:
            slot_headers = ['Slot ID', 'Start Time', 'End Time', 'Status']
            slot_data = [slot_headers]
            for sl in slots:
                if isinstance(sl, dict):
                    slot_data.append([
                        str(sl.get('id', '—')),
                        str(sl.get('start_time', '—')),
                        str(sl.get('end_time', '—')),
                        str(sl.get('status', '—'))
                    ])
                else:
                    slot_data.append([
                        str(sl[0]) if len(sl) > 0 else '—',
                        str(sl[1]) if len(sl) > 1 else '—',
                        str(sl[2]) if len(sl) > 2 else '—',
                        str(sl[3]) if len(sl) > 3 else '—'
                    ])
            col_w = [2*cm, 6*cm, 6*cm, 3*cm]
            elements.append(_build_table(slot_data, col_w,
                                          header_color=colors.HexColor('#16a085')))
        else:
            elements.append(Paragraph('  No time slots defined.', normal))

        elements.append(Spacer(1, 6))

    doc.build(elements)
    return filepath


# ══════════════════════════════════════════════════════════
#  ۴. گزارش آماری ادمین
# ══════════════════════════════════════════════════════════
def generate_admin_stats_report(stats: dict,
                                 all_bookings: List[Union[tuple, dict]],
                                 top_services: List[Union[tuple, dict]]) -> str:
    """
    گزارش آماری برای ادمین
    
    stats: dict از StatsModel.get_admin_stats()
    all_bookings: list از BookingModel.get_all_bookings()
    top_services: list از StatsModel.get_top_services()
    """
    _ensure_reports_dir()
    filepath = _filename('Admin', 'Statistics_Report')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    normal, title_style, sub = _base_style()

    _doc_header(elements,
                title='Admin Statistics Report',
                subtitle='System Overview')

    # ── کارت‌های آمار ──
    stat_rows = [
        ['Metric', 'Value'],
        ['Total Users', str(stats.get('total_users', 0))],
        ['Total Bookings', str(stats.get('total_bookings', 0))],
        ['Confirmed Bookings', str(stats.get('confirmed_bookings', 0))],
        ['Today Bookings', str(stats.get('daily_bookings', 0))],
        ['This Week Bookings', str(stats.get('weekly_bookings', 0))],
        ['Active Services', str(stats.get('active_services', 0))],
        ['Inactive Services', str(stats.get('inactive_services', 0))],
        ['Total Income (Toman)', f"{stats.get('total_income', 0):,.0f}"],
        ['Today Income (Toman)', f"{stats.get('daily_income', 0):,.0f}"],
        ['Week Income (Toman)', f"{stats.get('weekly_income', 0):,.0f}"],
    ]
    # تفکیک نقش
    for role, cnt in stats.get('users_by_role', {}).items():
        stat_rows.append([f'Users - {role}', str(cnt)])

    elements.append(_build_table(stat_rows, [10*cm, 7*cm]))
    elements.append(Spacer(1, 14))

    # ── سرویس‌های برتر ──
    if top_services:
        elements.append(Paragraph('Top Services', ParagraphStyle(
            'sec', fontName=FONT_NAME, fontSize=12,
            textColor=colors.HexColor('#8e44ad'), spaceBefore=8, spaceAfter=4)))
        top_data = [['Service Title', 'Bookings', 'Revenue (Toman)']]
        for s in top_services:
            if isinstance(s, dict):
                title = s.get('title', '—')
                count = s.get('booking_count', 0)
                revenue = s.get('revenue', 0)
            else:
                title = s[0] if len(s) > 0 else '—'
                count = s[1] if len(s) > 1 else 0
                revenue = s[2] if len(s) > 2 else 0
            top_data.append([str(title), str(count), f"{revenue:,.0f}"])
        elements.append(_build_table(top_data, [9*cm, 4*cm, 5*cm],
                                      header_color=colors.HexColor('#8e44ad')))
        elements.append(Spacer(1, 14))

    # ── لیست رزروها ──
    if all_bookings:
        elements.append(Paragraph('All Bookings', ParagraphStyle(
            'sec2', fontName=FONT_NAME, fontSize=12,
            textColor=colors.HexColor('#2c3e50'), spaceBefore=8, spaceAfter=4)))
        bk_data = [['ID', 'Customer', 'Provider', 'Service', 'Time', 'Status', 'Payment']]
        for b in all_bookings:
            bk_data.append([
                _get_value(b, 0, 'id'),
                _get_value(b, 1, 'customer_name'),
                _get_value(b, 2, 'provider_name'),
                str(_get_value(b, 3, 'service_title'))[:18],
                str(_get_value(b, 4, 'start_time'))[:16],
                _get_value(b, 5, 'status'),
                _get_value(b, 6, 'payment_status')
            ])
        col_w = [1.2*cm, 3*cm, 3*cm, 4*cm, 4*cm, 2.2*cm, 2.1*cm]
        elements.append(_build_table(bk_data, col_w))

    doc.build(elements)
    return filepath

# ══════════════════════════════════════════════════════════
#  ۵. گزارش رزروهای دریافتی Provider
# ══════════════════════════════════════════════════════════
def generate_provider_bookings_report(username: str, bookings: List[Union[tuple, dict]]) -> str:
    """گزارش رزروهای دریافتی برای ارائه‌دهنده"""
    _ensure_reports_dir()
    filepath = _filename('Provider', 'Bookings_Report')
    
    # کاهش حاشیه‌های صفحه برای فضای بیشتر
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=1*cm, leftMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []
    _doc_header(elements,
                title='Provider Bookings Report',
                subtitle=f'Provider: {username}')

    normal, _, _ = _base_style()
    total = len(bookings)
    
    confirmed = 0
    pending = 0
    rejected = 0
    canceled = 0
    paid = 0
    
    for b in bookings:
        status = _get_value(b, 5, 'status')
        payment = _get_value(b, 6, 'payment_status')
        
        if status == 'Confirmed':
            confirmed += 1
        elif status == 'Pending':
            pending += 1
        elif status == 'Rejected':
            rejected += 1
        elif status == 'Canceled':
            canceled += 1
        if payment == 'Paid':
            paid += 1
    
    elements.append(Spacer(1, 6))
    for line in [
        f"Total Bookings: {total}",
        f"Confirmed: {confirmed}    Pending: {pending}    Rejected: {rejected}    Canceled: {canceled}",
        f"Paid: {paid}    Unpaid: {total - paid}",
    ]:
        elements.append(Paragraph(line, normal))
    elements.append(Spacer(1, 12))

    headers = ['ID', 'Customer', 'Service', 'Start Time', 'End Time', 'Status', 'Payment']
    data = [headers]
    
    for b in bookings:
        # محدود کردن طول متن سرویس
        service_title = _get_value(b, 2, 'service_title')
        if len(service_title) > 25:
            service_title = service_title[:22] + '...'
        
        # محدود کردن طول نام مشتری
        customer_name = _get_value(b, 1, 'customer_name')
        if len(customer_name) > 15:
            customer_name = customer_name[:12] + '...'
        
        data.append([
            _get_value(b, 0, 'id'),
            customer_name,
            service_title,
            (_get_value(b, 3, 'start_time')[:16] if _get_value(b, 3, 'start_time') else ''),
            (_get_value(b, 4, 'end_time')[:16] if _get_value(b, 4, 'end_time') else ''),
            _get_value(b, 5, 'status'),
            _get_value(b, 6, 'payment_status')
        ])

    # عرض بهینه ستون‌ها (کاهش یافته)
    col_w = [0.8*cm, 2.5*cm, 3.5*cm, 2.8*cm, 2.8*cm, 1.8*cm, 1.5*cm]
    elements.append(_build_table(data, col_w))

    doc.build(elements)
    return filepath