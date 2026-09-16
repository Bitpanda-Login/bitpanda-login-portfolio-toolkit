import locale
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import cm

def format_eur(amount):
    """Formats a float as a Spanish Euro string (1.234,56)."""
    try:
        # Try to use Spanish locale for proper formatting
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
        return locale.format_string("%.2f", amount, grouping=True)
    except locale.Error:
        # Fallback if locale is not available
        s = f"{amount:,.2f}"
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return s

def format_qty(amount):
    """Formats a crypto quantity with up to 8 decimals."""
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
        return locale.format_string("%.8f", amount, grouping=True).rstrip('0').rstrip(',')
    except locale.Error:
        s = f"{amount:,.8f}"
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return s.rstrip('0').rstrip(',')

def create_table_style():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ])

def generate_pdf(output_path, metadata, results, year):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CustomTitle', parent=styles['Heading1'], textColor=colors.HexColor('#1a237e')))
    styles.add(ParagraphStyle(name='CustomH2', parent=styles['Heading2'], textColor=colors.HexColor('#1a237e')))
    
    elements = []
    
    # 1. Cover Page
    elements.append(Paragraph("BitpandaTax", styles['CustomTitle']))
    elements.append(Spacer(1, 1*cm))
    
    user_info = f"""
    <b>Contribuyente:</b> {metadata.get('user', 'Desconocido')}<br/>
    <b>Email:</b> {metadata.get('email', 'Desconocido')}<br/>
    <b>Jurisdicción:</b> España<br/>
    <b>Plataforma:</b> {metadata.get('venue', 'Bitpanda')}
    """
    elements.append(Paragraph(user_info, styles['Normal']))
    elements.append(Spacer(1, 2*cm))
    
    elements.append(Paragraph(f"Informe Fiscal de {year}", styles['CustomH2']))
    elements.append(Spacer(1, 0.5*cm))
    
    intro_text = f"""
    Estimado cliente,<br/><br/>
    Adjuntamos el informe fiscal de {year}.<br/>
    El informe contiene todas las transacciones relevantes en el período del 01.01.{year} al 31.12.{year}.<br/><br/>
    Componentes del informe:<br/>
    1. Hoja de Resumen<br/>
    2. Asistencia para completar el formulario AEAT (Renta Web)<br/>
    3. Resumen de ganancias y pérdidas por activo<br/>
    4. Extracto de transacciones<br/>
    5. Notas explicativas
    """
    elements.append(Paragraph(intro_text, styles['Normal']))
    elements.append(PageBreak())
    
    # 2. Summary Page
    elements.append(Paragraph(f"Determinación de bases imponibles en {year}", styles['CustomH2']))
    elements.append(Spacer(1, 0.5*cm))
    
    cg_net = results['capital_gains'] + results['capital_losses']
    data_summary = [
        ["Categoría", "Valor (EUR)"],
        ["Suma de las ganancias de capital", format_eur(results['capital_gains'])],
        ["Suma de las pérdidas de capital", format_eur(abs(results['capital_losses']))],
        ["Total ganancias/pérdidas de capital", format_eur(cg_net)],
        ["", ""],
        ["Total rendimiento capital mobiliario", format_eur(results['mobile_capital_income'])],
        ["", ""],
        ["Total ganancias no derivadas (airdrops)", format_eur(results['non_transmission_gains'])],
        ["", ""],
        ["Fees no deducidos", format_eur(results['fees_not_deducted'])]
    ]
    t = Table(data_summary, colWidths=[12*cm, 4*cm])
    t.setStyle(create_table_style())
    elements.append(t)
    elements.append(PageBreak())
    
    # 3. AEAT Form Assistance
    elements.append(Paragraph("Asistencia para completar el formulario AEAT", styles['CustomH2']))
    elements.append(Spacer(1, 0.5*cm))
    
    aeat_data = [
        ["Casilla / Sección", "Descripción", "Importe a declarar"],
        ["1800 - 1814", "Ganancias y pérdidas patrimoniales (Transmisiones)", format_eur(cg_net)],
        ["0033", "Rendimientos del capital mobiliario (Staking)", format_eur(results['mobile_capital_income'])],
        ["0304", "Ganancias no derivadas (Airdrops/Bounties)", format_eur(results['non_transmission_gains'])]
    ]
    t_aeat = Table(aeat_data, colWidths=[4*cm, 8*cm, 4*cm])
    t_aeat.setStyle(create_table_style())
    elements.append(t_aeat)
    elements.append(PageBreak())
    
    # 4. Asset Summary
    elements.append(Paragraph("Resumen de ganancias y pérdidas por activo", styles['CustomH2']))
    elements.append(Spacer(1, 0.5*cm))
    
    asset_data = [["Asset", "Ganancias", "Pérdidas", "Neto"]]
    for asset, vals in sorted(results['asset_summary'].items()):
        asset_data.append([
            asset, 
            format_eur(vals['gains']), 
            format_eur(vals['losses']), 
            format_eur(vals['net'])
        ])
    
    t_asset = Table(asset_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    t_asset.setStyle(create_table_style())
    elements.append(t_asset)
    elements.append(PageBreak())
    
    # 5. Transactions Extract
    elements.append(Paragraph("Extracto de Transacciones", styles['CustomH2']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Filter only target year transactions and reverse chronologically for display?
    # Blockpit usually chronological. We have them chronological.
    # Take only transactions from target year
    txs = [tx for tx in results['transactions'] if tx['Date'].year == int(year)]
    
    # To avoid huge tables blowing up memory, we process in chunks or standard table.
    # reportlab can paginate tables automatically.
    
    tx_header = ["Fecha", "Tipo", "Asset", "Cantidad", "Valor EUR", "Coste Adq.", "G/P"]
    tx_data = [tx_header]
    
    for tx in txs:
        tx_data.append([
            tx['Date'].strftime("%d.%m.%Y %H:%M:%S"),
            tx['Type'],
            tx['Asset'],
            format_qty(tx['Quantity']),
            format_eur(tx['Value EUR']),
            format_eur(tx['Cost Basis']),
            format_eur(tx['Gain/Loss']) if tx['Gain/Loss'] != 0 else "-"
        ])
        
    t_tx = Table(tx_data, colWidths=[4*cm, 2*cm, 2*cm, 3*cm, 2*cm, 2*cm, 2*cm], repeatRows=1)
    
    tx_style = create_table_style()
    tx_style.add('FONTSIZE', (0, 1), (-1, -1), 8)
    t_tx.setStyle(tx_style)
    
    elements.append(t_tx)
    elements.append(PageBreak())
    
    # 6. Explanatory Notes
    elements.append(Paragraph("Notas explicativas fiscales", styles['CustomH2']))
    elements.append(Spacer(1, 0.5*cm))
    
    notes = """
    <b>Art. 33.1 de la Ley del IRPF (Plusvalía):</b><br/>
    La alteración del patrimonio neto se clasifica como plusvalía. Los ingresos por transferencia de activos digitales (incluyendo intercambios cripto-cripto) son plusvalías derivadas de transferencias.<br/><br/>
    
    <b>Art. 34 de la Ley del IRPF (Cálculo):</b><br/>
    La plusvalía es la diferencia entre el valor de transmisión y el coste de adquisición. Las comisiones están incluidas en el coste de adquisición.<br/><br/>
    
    <b>Art. 37.2 de la Ley del IRPF (Método PEPS/FIFO):</b><br/>
    Para activos homogéneos, se aplica Primero en Entrar, Primero en Salir. Si no hay coste histórico rastreable, el coste base se asume en 0 EUR.<br/><br/>
    
    <b>Art. 25.1 y 25.2 (Rendimiento Capital Mobiliario):</b><br/>
    Los ingresos por cesión a terceros (Staking, Masternodos, Lending) se tratan como rendimiento de capital mobiliario (Casilla 0033).<br/><br/>
    
    <b>Ganancias no derivadas de transmisiones:</b><br/>
    Airdrops, Bounties, y Minería no comercial tributan por su valor de mercado en el día de recepción (Casilla 0304).
    """
    
    elements.append(Paragraph(notes, styles['Normal']))
    
    doc.build(elements)

