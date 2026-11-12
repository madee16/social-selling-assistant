import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.order import Order

STATUS_TRANSLATIONS = {
    "pending": ("EN ATTENTE", "#D97706"),
    "confirmed": ("CONFIRMÉE", "#2563EB"),
    "preparing": ("EN PRÉPARATION", "#7C3AED"),
    "shipped": ("EXPÉDIÉE / EN TRANSIT", "#0284C7"),
    "delivered": ("LIVRÉE", "#16A34A"),
    "cancelled": ("ANNULÉE", "#DC2626"),
}


def generate_order_invoice_pdf(
    order: Order,
    merchant: Any = None,
    store: Any = None,
    buyer: Any = None,
) -> bytes:
    """Generate a professional French Bon de Livraison / Facture PDF for Tunisian e-commerce."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()

    # Typography styles
    s_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0F172A"),
    )
    s_sub = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748B"),
    )
    s_bold = ParagraphStyle(
        "DocBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
    )
    s_val = ParagraphStyle(
        "DocVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )
    s_th = ParagraphStyle(
        "DocTH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )
    s_th_r = ParagraphStyle("DocTHR", parent=s_th, alignment=2)
    s_td = ParagraphStyle(
        "DocTD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
    )
    s_td_r = ParagraphStyle("DocTDR", parent=s_td, alignment=2)
    s_td_rb = ParagraphStyle("DocTDRB", parent=s_td_r, fontName="Helvetica-Bold")

    story = []

    # 1. Header: Merchant / Store info on left, Document details on right
    store_name = "Boutique Social Selling"
    store_phone = ""
    store_email = ""

    if store and getattr(store, "name", None):
        store_name = store.name
    elif merchant and getattr(merchant, "company_name", None):
        store_name = merchant.company_name

    if merchant:
        store_phone = getattr(merchant, "phone", "") or ""
        store_email = getattr(merchant, "email", "") or ""

    header_left = [
        Paragraph(f"<b>{store_name}</b>", s_title),
        Paragraph("Commerce Électronique & Vente Sociale - Tunisie", s_sub),
    ]
    if store_phone or store_email:
        contact_line = " • ".join(filter(None, [store_phone, store_email]))
        header_left.append(Paragraph(contact_line, s_sub))
    header_left.append(Paragraph("Mode : Paiement à la livraison (COD)", s_sub))

    order_ref = f"BON-{str(order.id)[:8].upper()}"
    status_text, status_color = STATUS_TRANSLATIONS.get(
        (order.status or "").lower(),
        ((order.status or "PENDING").upper(), "#1E3A8A"),
    )

    date_str = (
        order.created_at.strftime("%d/%m/%Y %H:%M")
        if getattr(order, "created_at", None)
        else datetime.now().strftime("%d/%m/%Y %H:%M")
    )

    header_right = [
        Paragraph(
            "<b>BON DE LIVRAISON / FACTURE</b>",
            ParagraphStyle(
                "DocHeaderRightTitle",
                parent=s_bold,
                fontSize=12,
                leading=15,
                textColor=colors.HexColor("#1E3A8A"),
                alignment=2,
            ),
        ),
        Paragraph(
            f"<b>Réf :</b> {order_ref}",
            ParagraphStyle("DocHeaderRef", parent=s_val, alignment=2),
        ),
        Paragraph(
            f"<b>Date :</b> {date_str}",
            ParagraphStyle("DocHeaderDate", parent=s_val, alignment=2),
        ),
        Paragraph(
            f"<b>Statut :</b> {status_text}",
            ParagraphStyle(
                "DocHeaderStat",
                parent=s_bold,
                textColor=colors.HexColor(status_color),
                alignment=2,
            ),
        ),
    ]

    header_table = Table([[header_left, header_right]], colWidths=[270, 240])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 14))

    # 2. Buyer & Shipping Details Box
    cust_name = order.customer_name or (buyer.name if buyer and getattr(buyer, "name", None) else "Client")
    cust_phone = order.customer_phone or (buyer.phone if buyer and getattr(buyer, "phone", None) else "—")
    cust_address = order.customer_address or "Adresse de livraison non spécifiée"

    customer_data = [
        [
            Paragraph(
                "<b>DESTINATAIRE & ADRESSE DE LIVRAISON</b>",
                ParagraphStyle("DocCustHead1", parent=s_bold, fontSize=9, leading=12, textColor=colors.HexColor("#1E3A8A")),
            ),
            Paragraph(
                "<b>MODALITÉS DE LIVRAISON</b>",
                ParagraphStyle("DocCustHead2", parent=s_bold, fontSize=9, leading=12, textColor=colors.HexColor("#1E3A8A")),
            ),
        ],
        [
            [
                Paragraph(f"<b>Nom :</b> {cust_name}", s_val),
                Paragraph(f"<b>Téléphone :</b> {cust_phone}", s_val),
                Paragraph(f"<b>Adresse :</b> {cust_address}", s_val),
            ],
            [
                Paragraph("<b>Mode d'expédition :</b> Livraison à domicile (Standard)", s_val),
                Paragraph("<b>Mode de règlement :</b> En espèces au livreur (Cash On Delivery)", s_val),
                Paragraph("<b>Destination :</b> Tunisie (TN)", s_val),
            ],
        ],
    ]
    cust_table = Table(customer_data, colWidths=[255, 255])
    cust_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(cust_table)
    story.append(Spacer(1, 14))

    # 3. Line Items Table
    items_header = [
        Paragraph("<b>Désignation de l'article</b>", s_th),
        Paragraph("<b>Qté</b>", s_th_r),
        Paragraph("<b>Prix unit. (TND)</b>", s_th_r),
        Paragraph("<b>Total (TND)</b>", s_th_r),
    ]
    table_data = [items_header]

    items = getattr(order, "items", []) or []
    computed_subtotal = 0.0

    if items:
        for item in items:
            p_name = getattr(item, "product_name", None)
            if not p_name and getattr(item, "product", None):
                p_name = getattr(item.product, "name", None)
            if not p_name:
                p_name = f"Article #{str(getattr(item, 'product_id', ''))[:8]}"

            qty = getattr(item, "quantity", 1)
            u_price = float(getattr(item, "unit_price", 0.0))
            sub = float(getattr(item, "subtotal", qty * u_price))
            computed_subtotal += sub

            table_data.append(
                [
                    Paragraph(p_name, s_td),
                    Paragraph(str(qty), s_td_r),
                    Paragraph(f"{u_price:.2f}", s_td_r),
                    Paragraph(f"{sub:.2f}", s_td_rb),
                ]
            )
    else:
        table_data.append(
            [
                Paragraph("Commande directe sans articles détaillés", s_td),
                Paragraph("1", s_td_r),
                Paragraph(f"{float(order.total_amount):.2f}", s_td_r),
                Paragraph(f"{float(order.total_amount):.2f}", s_td_rb),
            ]
        )
        computed_subtotal = float(order.total_amount)

    items_table = Table(table_data, colWidths=[270, 50, 95, 95])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8FAFC")],
                ),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Summary Table aligned to right
    total_val = float(order.total_amount) if order.total_amount is not None else computed_subtotal
    summary_data = [
        [
            Paragraph("<b>Sous-total :</b>", s_val),
            Paragraph(f"{computed_subtotal:.2f} TND", s_td_r),
        ],
        [
            Paragraph("<b>Frais de livraison :</b>", s_val),
            Paragraph("0.00 TND (Inclus)", s_td_r),
        ],
        [
            Paragraph(
                "<b>TOTAL À PAYER (TTC) :</b>",
                ParagraphStyle("DocTotLabel", parent=s_bold, fontSize=10, leading=13, textColor=colors.HexColor("#0F172A")),
            ),
            Paragraph(
                f"<b>{total_val:.2f} TND</b>",
                ParagraphStyle("DocTotVal", parent=s_bold, fontSize=11, leading=14, textColor=colors.HexColor("#1E3A8A"), alignment=2),
            ),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[140, 100])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 2), (-1, 2), 1, colors.HexColor("#BFDBFE")),
            ]
        )
    )

    outer_summary = Table([["", summary_table]], colWidths=[270, 240])
    outer_summary.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(outer_summary)
    story.append(Spacer(1, 16))

    # 5. Instructions & Delivery Notes Box
    footer_data = [
        [
            Paragraph(
                "<b>Consignes de livraison & mentions légales :</b><br/>"
                "• <b>Paiement contre remboursement (COD) :</b> Le client s'engage à régler le montant exact au transporteur lors de la livraison.<br/>"
                "• <b>Vérification du colis :</b> Veuillez vérifier l'état du paquet en présence du livreur avant le règlement.<br/>"
                "• <b>Assistance & réclamation :</b> En cas de question, contactez notre service client en rappelant la référence de votre commande.<br/>"
                "<i>Document officiel généré électroniquement par la plateforme Social Selling Tunisie.</i>",
                ParagraphStyle("DocFootText", parent=s_sub, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#475569")),
            )
        ]
    ]
    footer_table = Table(footer_data, colWidths=[510])
    footer_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(footer_table)

    doc.build(story)
    return buffer.getvalue()
