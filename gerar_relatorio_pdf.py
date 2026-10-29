from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
IMG_DIR = ROOT / "report_images"
PDF_PATH = ROOT / "relatorio_sistema_mercado.pdf"


def build_pdf():
    page_width, _ = A4
    navy = colors.HexColor("#14213d")
    purple = colors.HexColor("#5145e5")
    muted = colors.HexColor("#526174")
    pale = colors.HexColor("#f3f5fb")
    border = colors.HexColor("#dce2ee")

    sample = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=23,
            textColor=navy,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=muted,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=navy,
            spaceBefore=7,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#263449"),
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "SmallNote",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=muted,
            spaceAfter=2,
        ),
        "caption": ParagraphStyle(
            "ImageCaption",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=navy,
        ),
        "bullet": ParagraphStyle(
            "ReportBullet",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            leftIndent=12,
            firstLineIndent=-8,
            textColor=colors.HexColor("#263449"),
            spaceAfter=2,
        ),
    }

    story = [
        Paragraph("Relatório do Sistema de Gerenciamento de Mercado", styles["title"]),
        Paragraph(
            "Aplicação web em Django | Gestão de estoque, caixa e ponto de venda",
            styles["subtitle"],
        ),
        Paragraph("1. Objetivo e implementação", styles["heading"]),
        Paragraph(
            "O projeto foi pensado para pequenos comércios que precisam controlar vendas, "
            "estoque e validade sem depender de um sistema comercial caro. A aplicação "
            "reúne essas rotinas em uma interface web e organiza o código no padrão "
            "BCE (Boundary–Control–Entity).",
            styles["body"],
        ),
        Paragraph(
            "<b>Funcionalidades implementadas</b>: acesso por perfis (dono, gerente, "
            "estoquista e operador); cadastro e precificação de produtos; entradas "
            "registradas com fornecedor, número de nota e lotes; abertura e fechamento "
            "de caixa com conferência; PDV com busca e pagamentos; registro de perdas; "
            "e alertas de estoque baixo e vencimento.",
            styles["body"],
        ),
        Paragraph(
            "Na venda, o estoque é baixado por lote com prioridade para o vencimento "
            "mais próximo (FEFO). As movimentações e itens de venda permitem acompanhar "
            "o histórico operacional.",
            styles["body"],
        ),
        Paragraph("2. Telas da aplicação", styles["heading"]),
    ]

    screenshot_specs = [
        ("dashboard.png", "Painel: vendas, estoque crítico e alertas"),
        ("produtos.png", "Produtos: preços, quantidades e situação do estoque"),
    ]
    screenshot_cells = []
    image_width = 8.45 * cm
    for filename, caption in screenshot_specs:
        image_path = IMG_DIR / filename
        if image_path.exists():
            image = Image(str(image_path), width=image_width, height=7.04 * cm)
            screenshot_cells.append(
                [image, Spacer(1, 3), Paragraph(caption, styles["caption"])]
            )

    if screenshot_cells:
        screenshots = Table(
            [screenshot_cells],
            colWidths=[8.75 * cm] * len(screenshot_cells),
            hAlign="CENTER",
        )
        screenshots.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), pale),
                    ("BOX", (0, 0), (-1, -1), 0.6, border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, border),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(screenshots)

    story.extend(
        [
            Spacer(1, 5),
            Paragraph(
                "Qualidades: interface visual consistente, perfis de acesso, regras de "
                "negócio separadas das telas e controle por lotes. O painel dá visibilidade "
                "rápida de vendas e situações que precisam de atenção.",
                styles["small"],
            ),
            PageBreak(),
            Paragraph("3. Modelagem e escopo", styles["heading"]),
            Paragraph(
                "A modelagem BCE foi concretizada em entidades Django (por exemplo, "
                "Produto, Lote, EntradaMercadoria, Caixa, Venda, ItemVenda, Perda, "
                "MovimentacaoEstoque e Alerta), regras nos controladores de "
                "<i>services.py</i> e interação nas views e templates. O detalhamento "
                "de lotes, itens de venda, movimentações e alertas dá suporte à "
                "rastreabilidade do estoque e da operação.",
                styles["body"],
            ),
            Paragraph(
                "<b>Ficou de fora:</b> integração com uma API autorizada para consultar "
                "ou emitir notas fiscais eletrônicas legítimas. O sistema registra "
                "informações de entrada e nota fornecidas pelo usuário, mas isso não "
                "equivale a validar ou emitir documento fiscal. Também não foram "
                "implementados gestão de múltiplas filiais nem relatórios avançados "
                "com exportação.",
                styles["body"],
            ),
            Paragraph("4. Hospedagem e dificuldades", styles["heading"]),
            Paragraph(
                "O guia complementar da equipe recomenda o Render pela integração com "
                "GitHub e publicação simplificada. Ele descreve a coleta de arquivos "
                "estáticos com <i>collectstatic</i>, migrações e inicialização via "
                "<i>gunicorn config.wsgi:application</i>; o projeto inclui Gunicorn e "
                "WhiteNoise nas dependências/configuração. PostgreSQL é citado como "
                "alternativa para persistência em produção, mas a configuração atual "
                "do projeto usa SQLite.",
                styles["body"],
            ),
            Paragraph(
                "A principal dificuldade foi escolher e configurar um servidor, "
                "incluindo caminhos de páginas e arquivos CSS/estáticos. Houve páginas "
                "que apresentavam erro em vez do conteúdo esperado; a equipe suspeitou "
                "de imports ou paths. A captura abaixo documenta também um erro 403 "
                "do Render por falha na verificação CSRF (token POST incorreto). "
                "Esse erro confirma um problema de implantação/formulário, mas não "
                "prova que CSS ou paths fossem a causa dos outros erros.",
                styles["body"],
            ),
        ]
    )

    error_image_path = IMG_DIR / "render_csrf_403.png"
    if error_image_path.exists():
        error_image = Image(str(error_image_path), width=17.5 * cm, height=9.85 * cm)
        story.append(error_image)
        story.append(
            Paragraph(
                "Evidência do teste de hospedagem: resposta 403 — falha CSRF no POST.",
                styles["small"],
            )
        )

    story.extend(
        [
            Paragraph("5. Síntese", styles["heading"]),
            Paragraph(
                "A aplicação entrega uma base funcional para gestão de um pequeno "
                "mercado e deixa espaço para evolução. Como próximos passos, recomenda-se "
                "estabilizar o deploy e a configuração CSRF/arquivos estáticos, adotar "
                "banco persistente em produção e avaliar a integração fiscal somente "
                "após obter as autorizações necessárias.",
                styles["body"],
            ),
            Paragraph(
                "Fonte complementar: <i>Guia de Hospedagem para Sistema de "
                "Gerenciamento de Estoque</i>, material da equipe enviado para "
                "enriquecer este relatório. As recomendações de hospedagem são "
                "apresentadas como plano técnico, não como funcionalidades fiscais "
                "ou configuração de produção já concluídas.",
                styles["small"],
            ),
        ]
    )

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(border)
        canvas.line(1.5 * cm, 1.0 * cm, page_width - 1.5 * cm, 1.0 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(muted)
        canvas.drawString(1.5 * cm, 0.65 * cm, "Sistema de Gerenciamento de Mercado")
        canvas.drawRightString(page_width - 1.5 * cm, 0.65 * cm, f"Página {doc.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.15 * cm,
        bottomMargin=1.3 * cm,
        title="Relatório do Sistema de Gerenciamento de Mercado",
        author="Equipe do projeto",
    )
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(f"PDF gerado: {PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
