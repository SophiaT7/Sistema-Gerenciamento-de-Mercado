from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.units import cm
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
IMG_DIR = ROOT / 'report_images'
IMG_DIR.mkdir(exist_ok=True)
PDF_PATH = ROOT / 'relatorio_sistema_mercado.pdf'
ERROR_IMAGE = Path(r'C:\Users\Blast\AppData\Roaming\Code\agentSessionData\b0f04d95-f68b-4e26-a249-1f13119fc521\attachments\09124702-4f8b-4b59-b252-a6fede1f7edd\Pasted Image.png')


def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1200})
        page.goto('http://127.0.0.1:8000/', timeout=30000)
        page.screenshot(path=str(IMG_DIR / 'login.png'), full_page=True)

        page.fill('#username', 'dono')
        page.fill('#password', 'dono123')
        page.locator("button[type='submit']").click()
        page.wait_for_url('**/dashboard', timeout=30000)
        page.screenshot(path=str(IMG_DIR / 'dashboard.png'), full_page=True)

        page.goto('http://127.0.0.1:8000/produtos/', timeout=30000)
        page.screenshot(path=str(IMG_DIR / 'produtos.png'), full_page=True)

        page.goto('http://127.0.0.1:8000/entradas/', timeout=30000)
        page.screenshot(path=str(IMG_DIR / 'entradas.png'), full_page=True)

        page.goto('http://127.0.0.1:8000/pdv/', timeout=30000)
        page.screenshot(path=str(IMG_DIR / 'pdv.png'), full_page=True)

        browser.close()


def build_pdf():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=body_style,
        leftIndent=18,
        bulletIndent=10,
        bulletFontName='Helvetica-Bold',
        spaceAfter=4,
    )
    note_style = ParagraphStyle(
        'NoteStyle',
        parent=body_style,
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        leftIndent=8,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph('Relatório do Sistema de Gerenciamento de Mercado', title_style))
    story.append(Paragraph('Projeto Django | Gestão de estoque, caixa, PDV e alertas', body_style))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph('1. O que foi implementado', h2_style))
    story.append(Paragraph('O sistema foi estruturado em Django com modelagem de domínio para gestão de produtos, lotes, entradas, caixa, PDV, perdas e alertas. A aplicação possui interface web com login, painel de controle, autenticação por perfis e regras de negócio centralizadas em serviços.', body_style))
    story.append(Paragraph('Principais funcionalidades entregues:', bullet_style))
    story.append(Paragraph('- Autenticação por usuário e papéis: dono, gerente, operador e estoquista.', bullet_style))
    story.append(Paragraph('- Cadastro e atualização de produtos com código, categoria, preço de custo, margem, preço de venda e controle de estoque mínimo.', bullet_style))
    story.append(Paragraph('- Registro de entradas de mercadoria com números de nota e controle por lotes e validade.', bullet_style))
    story.append(Paragraph('- Fluxo de caixa com abertura, fechamento e diferencas de valor.', bullet_style))
    story.append(Paragraph('- PDV com busca por produto, cálculo de pagamentos e baixa inteligente por lote (FEFO).', bullet_style))
    story.append(Paragraph('- Registro de perdas e alertas automáticos de estoque baixo e vencimento.', bullet_style))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph('2. Prints das telas principais', h2_style))
    images = [
        ('login.png', 'Tela de login'),
        ('dashboard.png', 'Dashboard principal'),
        ('produtos.png', 'Cadastro / listagem de produtos'),
    ]

    for filename, caption in images:
        path = IMG_DIR / filename
        if path.exists():
            img = Image(str(path), width=15 * cm, height=9 * cm)
            story.append(img)
            story.append(Paragraph(caption, note_style))
            story.append(Spacer(1, 0.18 * cm))

    story.append(PageBreak())
    story.append(Paragraph('3. O que ficou de fora', h2_style))
    story.append(Paragraph('A aplicação já entrega a base do sistema de mercado, porém ainda há lacunas em relação a um ambiente mais completo de produção. Entre os itens não implementados nesta etapa, destacam-se:', body_style))
    story.append(Paragraph('- Integração com uma API pública de notas fiscais legítimas, que exigiria autorização e mapeamento de regras do emissor.', bullet_style))
    story.append(Paragraph('- Emissão de documentos fiscais eletrônicos em conformidade com a legislação local.', bullet_style))
    story.append(Paragraph('- Módulo de relatórios financeiros mais robustos e exportação para CSV/PDF em diferentes filtros.', bullet_style))
    story.append(Paragraph('- Fluxo de gestão de múltiplas filiais e usuários com permissões segmentadas em maior profundidade.', bullet_style))

    story.append(Paragraph('4. Mudanças em relação à modelagem e dificuldades encontradas', h2_style))
    story.append(Paragraph('A modelagem foi adaptada para um escopo prático de mercado e PDV, com foco em persistência e regras de negócio. Em vez de uma estrutura extremamente genérica, priorizou-se uma solução direta com entidades centrais: Usuário, Produto, Lote, EntradaMercadoria, Caixa, Venda, ItemVenda, Perda, MovimentacaoEstoque e Alerta.', body_style))
    story.append(Paragraph('Dificuldades principais:', bullet_style))
    story.append(Paragraph('- Achar um servidor estável e coerente para o projeto e configurar corretamente os caminhos dos templates e arquivos estáticos.', bullet_style))
    story.append(Paragraph('- Erros de renderização em páginas que retornavam problemas ao invés de conteúdo visual, apontando para problemas em imports, CSS e paths.', bullet_style))
    story.append(Paragraph('- Problemas com a configuração de servidor render, especialmente na gestão de sessões, CSRF e rotas quando a aplicação não carregava de forma consistente.', bullet_style))
    story.append(Paragraph('A imagem abaixo ilustra um erro do tipo CSRF/Render encontrado durante a validação, que reforça a necessidade de revisar o ambiente de execução e a configuração de templates e endpoints.', note_style))

    if ERROR_IMAGE.exists():
        try:
            err_img = Image(str(ERROR_IMAGE), width=15 * cm, height=9 * cm)
            story.append(err_img)
        except Exception:
            pass

    story.append(Paragraph('5. Qualidades do que foi implementado', h2_style))
    story.append(Paragraph('Mesmo com as dificuldades de configuração, a aplicação apresenta pontos fortes relevantes: organização por camadas (BCE), regras de negócio centralizadas em serviços, uso de SQLite em desenvolvimento, autenticação e gestão por perfis, controle de estoque por lote e baixa FEFO, além de dashboard com indicadores úteis para operação do mercado.', body_style))
    story.append(Paragraph('Em resumo, o projeto já funciona como base sólida para operação de um pequeno ou médio mercado, com boa base para evoluir para integração de fornecedores, emissão fiscal e uso em ambiente de produção mais robusto.', body_style))

    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    doc.build(story)


if __name__ == '__main__':
    capture_screenshots()
    build_pdf()
    print(f'PDF gerado em: {PDF_PATH}')
