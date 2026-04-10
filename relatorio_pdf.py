from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from datetime import datetime


def agrupar_por_cliente(lista):
    resultado = {}

    for item in lista:
        cliente = item["cliente"] or "Sem cliente"
        resultado.setdefault(cliente, []).append(item)

    return resultado


def gerar_pdf(pendencias, atrasados):

    file_path = "relatorio_monitoramento.pdf"

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # =========================
    # TÍTULO
    # =========================
    elements.append(Paragraph("ZECA MONITOR - RELATÓRIO", styles['Title']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Gerado em: {agora}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # =========================
    # RESUMO
    # =========================
    total_atrasados = len(atrasados["hoje"]) + len(atrasados["anteriores"])

    elements.append(Paragraph("RESUMO", styles['Heading2']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Pendências: {len(pendencias)}", styles['Normal']))
    elements.append(Paragraph(f"Atrasados Hoje: {len(atrasados['hoje'])}", styles['Normal']))
    elements.append(Paragraph(f"Atrasados Anteriores: {len(atrasados['anteriores'])}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # =========================
    # PENDÊNCIAS (por operador)
    # =========================
    elements.append(Paragraph("PENDÊNCIAS POR RESPONSÁVEL", styles['Heading2']))
    elements.append(Spacer(1, 10))

    agrupado_resp = {}

    for p in pendencias:
        resp = p["cliente"] or "Sem responsável"
        agrupado_resp.setdefault(resp, []).append(p)

    for resp, chamados in agrupado_resp.items():
        elements.append(Paragraph(f"<b>{resp}</b>", styles['Normal']))
        elements.append(Spacer(1, 5))

        for c in chamados:
            texto = f"""
            • <b>{c['key']}</b> - {c['data']} - 
            <link href="{c['link']}">Abrir chamado</link>
            """
            elements.append(Paragraph(texto, styles['Normal']))

        elements.append(Spacer(1, 10))

    elements.append(Spacer(1, 20))

    # =========================
    # ATRASADOS HOJE
    # =========================
    elements.append(Paragraph("🚨 ATRASADOS HOJE", styles['Heading2']))
    elements.append(Spacer(1, 10))

    atrasados_hoje = agrupar_por_cliente(atrasados["hoje"])

    for cliente, chamados in atrasados_hoje.items():
        elements.append(Paragraph(f"<b>{cliente}</b>", styles['Normal']))
        elements.append(Spacer(1, 5))

        for c in chamados:
            texto = f"""
            • <b>{c['key']}</b> - {c['data']} - 
            <link href="{c['link']}">Abrir chamado</link>
            """
            elements.append(Paragraph(texto, styles['Normal']))

        elements.append(Spacer(1, 10))

    elements.append(Spacer(1, 20))

    # =========================
    # ATRASADOS ANTERIORES
    # =========================
    elements.append(Paragraph("🔥 ATRASADOS DIAS ANTERIORES", styles['Heading2']))
    elements.append(Spacer(1, 10))

    atrasados_ant = agrupar_por_cliente(atrasados["anteriores"])

    for cliente, chamados in atrasados_ant.items():
        elements.append(Paragraph(f"<b>{cliente}</b>", styles['Normal']))
        elements.append(Spacer(1, 5))

        for c in chamados:
            texto = f"""
            • <b>{c['key']}</b> - {c['data']} - 
            <link href="{c['link']}">Abrir chamado</link>
            """
            elements.append(Paragraph(texto, styles['Normal']))

        elements.append(Spacer(1, 10))

    # =========================
    # BUILD
    # =========================
    doc.build(elements)

    return file_path