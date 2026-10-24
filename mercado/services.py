"""
Controladores do Sistema de Mercado (Camada Control <<control>>)
Implementa exatamente os métodos e regras de negócio definidos no diagrama do Astah
"""

from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import (
    Usuario, Produto, Lote, EntradaMercadoria,
    Caixa, Venda, ItemVenda, Perda, MovimentacaoEstoque, Alerta
)


class ControladorProduto:
    """
    <<control>> ControladorProduto
    """
    @staticmethod
    def cadastrar_produto(codigo: str, nome: str, categoria: str, unidade: str,
                          estoque_minimo: Decimal, preco_custo: Decimal, margem_lucro: Decimal,
                          usuario: Usuario = None) -> Produto:
        preco_custo = Decimal(str(preco_custo))
        margem_lucro = Decimal(str(margem_lucro))
        preco_venda = (preco_custo * (Decimal('1') + (margem_lucro / Decimal('100')))).quantize(Decimal('0.01'))

        produto = Produto.objects.create(
            codigo=codigo.strip(),
            nome=nome.strip(),
            categoria=categoria,
            unidade=unidade,
            estoque_minimo=Decimal(str(estoque_minimo)),
            preco_custo=preco_custo,
            margem_lucro=margem_lucro,
            preco_venda=preco_venda
        )

        MovimentacaoEstoque.objects.create(
            produto=produto,
            tipo='AJUSTE',
            quantidade=0,
            justificativa=f"Cadastro inicial do produto pelo usuário {usuario.username if usuario else 'Sistema'}",
            usuario=usuario
        )

        ControladorAlertas.verificar_alertas_produto(produto)
        return produto

    @staticmethod
    def atualizar_preco(codigo: str, novo_preco: Decimal, usuario: Usuario = None) -> Produto:
        produto = Produto.objects.get(codigo=codigo)
        preco_antigo = produto.preco_venda
        produto.atualizar_preco_venda(novo_preco)

        MovimentacaoEstoque.objects.create(
            produto=produto,
            tipo='AJUSTE',
            quantidade=0,
            justificativa=f"Preço alterado de R$ {preco_antigo} para R$ {produto.preco_venda}",
            usuario=usuario
        )
        return produto


class ControladorEntradaMercadoria:
    """
    <<control>> ControladorEntradaMercadoria
    """
    @staticmethod
    @transaction.atomic
    def processar_entrada(numero_nota: str, fornecedor: str, lotes_dados: list, responsavel: Usuario) -> EntradaMercadoria:
        entrada = EntradaMercadoria.objects.create(
            numero_nota_fiscal=numero_nota,
            fornecedor=fornecedor,
            responsavel=responsavel
        )

        for item in lotes_dados:
            produto = item['produto']
            qtd = Decimal(str(item['quantidade']))
            custo = Decimal(str(item['custo_unitario']))
            validade = item['data_validade']
            num_lote = item.get('numero_lote') or f"L-{timezone.now().strftime('%y%m%d%H%M%S')}"

            lote = Lote.objects.create(
                produto=produto,
                entrada=entrada,
                numero_lote=num_lote,
                quantidade=qtd,
                custo_unitario=custo,
                data_validade=validade
            )

            # Atualiza o preço de custo do produto para o custo da última entrada se for maior
            if custo > 0:
                produto.preco_custo = custo
                # Recalcula o preço de venda sugerido
                produto.preco_venda = (custo * (Decimal('1') + (produto.margem_lucro / Decimal('100')))).quantize(Decimal('0.01'))
                produto.save()

            # Registra auditoria de movimentação de estoque
            MovimentacaoEstoque.objects.create(
                produto=produto,
                tipo='ENTRADA',
                quantidade=qtd,
                justificativa=f"Entrada NF {numero_nota} - Fornecedor: {fornecedor} (Lote: {num_lote})",
                usuario=responsavel
            )

            ControladorAlertas.verificar_alertas_produto(produto)

        return entrada


class ControladorCaixa:
    """
    <<control>> ControladorCaixa
    """
    @staticmethod
    def abrir_caixa(operador: Usuario, fundo_troco_inicial: Decimal) -> Caixa:
        # Verifica se já há um caixa aberto para esse operador
        caixa_existente = Caixa.objects.filter(operador=operador, aberto=True).first()
        if caixa_existente:
            raise ValueError(f"O operador {operador.username} já possui o Caixa #{caixa_existente.id} aberto.")

        caixa = Caixa.objects.create(
            operador=operador,
            fundo_troco_inicial=Decimal(str(fundo_troco_inicial)),
            valor_sistema=Decimal(str(fundo_troco_inicial)),
            aberto=True
        )
        return caixa

    @staticmethod
    def fechar_caixa(caixa: Caixa, valor_fisico_conferido: Decimal, observacao: str = "") -> Caixa:
        if not caixa.aberto:
            raise ValueError(f"O Caixa #{caixa.id} já está fechado.")

        caixa.fechar_caixa(valor_fisico_conferido, observacao)

        # Se houver diferença significativa (quebra ou sobra), cria um alerta
        if abs(caixa.diferenca) > Decimal('0.01'):
            tipo_dif = "SOBRA" if caixa.diferenca > 0 else "QUEBRA"
            Alerta.objects.create(
                tipo='DIFERENCA_CAIXA',
                mensagem=f"Fechamento do Caixa #{caixa.id} ({caixa.operador.username}) com {tipo_dif} de R$ {abs(caixa.diferenca):.2f}. Esperado: R$ {caixa.valor_sistema:.2f}, Conferido: R$ {caixa.valor_fisico_conferido:.2f}."
            )

        return caixa


class ControladorVenda:
    """
    <<control>> ControladorVenda
    Gerencia venda no PDV e baixa inteligente de estoque pelo lote mais próximo do vencimento (FEFO)
    """
    @staticmethod
    @transaction.atomic
    def processar_venda(operador: Usuario, meio_pagamento: str, itens: list, caixa: Caixa = None) -> Venda:
        if not caixa:
            caixa = Caixa.objects.filter(operador=operador, aberto=True).first()

        if not caixa:
            raise ValueError("Não há nenhum Caixa aberto para este operador. Abra o caixa antes de realizar vendas.")

        venda = Venda.objects.create(
            caixa=caixa,
            operador=operador,
            meio_pagamento=meio_pagamento
        )

        for item_info in itens:
            produto = item_info['produto']
            quantidade_desejada = Decimal(str(item_info['quantidade']))
            preco_unitario = Decimal(str(item_info.get('preco_unitario') or produto.preco_venda))

            # Verificar se o estoque total atende
            if produto.estoque_atual < quantidade_desejada:
                raise ValueError(f"Estoque insuficiente para o produto {produto.nome}. Solicitado: {quantidade_desejada}, Disponível: {produto.estoque_atual}")

            # Baixa de estoque usando método FEFO (First Expired, First Out - Primeiro que Vence é o Primeiro que Sai)
            lotes_disponiveis = produto.lotes.filter(quantidade__gt=0).order_by('data_validade')
            restante_a_baixar = quantidade_desejada

            for lote in lotes_disponiveis:
                if restante_a_baixar <= 0:
                    break

                if lote.quantidade >= restante_a_baixar:
                    lote.baixar_quantidade(restante_a_baixar)
                    ItemVenda.objects.create(
                        venda=venda,
                        produto=produto,
                        lote=lote,
                        quantidade=restante_a_baixar,
                        preco_unitario=preco_unitario
                    )
                    restante_a_baixar = Decimal('0')
                else:
                    baixado = lote.quantidade
                    lote.baixar_quantidade(baixado)
                    ItemVenda.objects.create(
                        venda=venda,
                        produto=produto,
                        lote=lote,
                        quantidade=baixado,
                        preco_unitario=preco_unitario
                    )
                    restante_a_baixar -= baixado

            MovimentacaoEstoque.objects.create(
                produto=produto,
                tipo='SAIDA_VENDA',
                quantidade=quantidade_desejada,
                justificativa=f"Venda PDV #{venda.id} - Operador: {operador.username}",
                usuario=operador
            )

            ControladorAlertas.verificar_alertas_produto(produto)

        venda.recalcular_total()
        return venda


class ControladorPerda:
    """
    <<control>> ControladorPerda
    """
    @staticmethod
    @transaction.atomic
    def registrar_perda(codigo_produto: str, quantidade: Decimal, motivo: str,
                        responsavel: Usuario, numero_lote: str = None, justificativa: str = "") -> Perda:
        produto = Produto.objects.get(codigo=codigo_produto)
        quantidade = Decimal(str(quantidade))
        lote = None

        if numero_lote:
            lote = produto.lotes.filter(numero_lote=numero_lote).first()

        # Se especificou lote, baixa dele; caso contrário baixa do lote mais antigo
        if lote:
            if lote.quantidade < quantidade:
                raise ValueError(f"O lote {numero_lote} possui apenas {lote.quantidade} em estoque.")
            lote.baixar_quantidade(quantidade)
        else:
            if produto.estoque_atual < quantidade:
                raise ValueError(f"Estoque insuficiente de {produto.nome} para registrar perda de {quantidade}.")
            restante = quantidade
            for l in produto.lotes.filter(quantidade__gt=0).order_by('data_validade'):
                if restante <= 0:
                    break
                if l.quantidade >= restante:
                    l.baixar_quantidade(restante)
                    restante = Decimal('0')
                else:
                    restante -= l.quantidade
                    l.baixar_quantidade(l.quantidade)

        perda = Perda.objects.create(
            produto=produto,
            lote=lote,
            quantidade=quantidade,
            motivo=motivo,
            responsavel=responsavel,
            justificativa=justificativa
        )

        MovimentacaoEstoque.objects.create(
            produto=produto,
            tipo='PERDA',
            quantidade=quantidade,
            justificativa=f"Perda registrada: {motivo}. {justificativa}",
            usuario=responsavel
        )

        ControladorAlertas.verificar_alertas_produto(produto)
        return perda


class ControladorAlertas:
    """
    <<control>> ControladorAlertas
    """
    @staticmethod
    def verificar_alertas():
        """Varre todo o catálogo e lotes para criar alertas pertinentes"""
        for produto in Produto.objects.filter(ativo=True):
            ControladorAlertas.verificar_alertas_produto(produto)

    @staticmethod
    def verificar_alertas_produto(produto: Produto):
        # 1. Alerta de Estoque Mínimo
        if produto.precisa_alerta_estoque():
            msg = f"O produto '{produto.nome}' (cód: {produto.codigo}) está com estoque crítico: {produto.estoque_atual} {produto.unidade} (Mínimo: {produto.estoque_minimo})."
            alerta_existente = Alerta.objects.filter(produto=produto, tipo='ESTOQUE_BAIXO', visto=False).first()
            if not alerta_existente:
                Alerta.objects.create(
                    produto=produto,
                    tipo='ESTOQUE_BAIXO',
                    mensagem=msg
                )

        # 2. Alertas de Validade de Lotes
        hoje = timezone.now().date()
        for lote in produto.lotes.filter(quantidade__gt=0):
            dias = (lote.data_validade - hoje).days
            if dias < 0:
                msg = f"Lote {lote.numero_lote} do produto '{produto.nome}' está VENCIDO desde {lote.data_validade.strftime('%d/%m/%Y')} ({lote.quantidade} em estoque!)."
                if not Alerta.objects.filter(lote=lote, tipo='VENCIDO', visto=False).exists():
                    Alerta.objects.create(produto=produto, lote=lote, tipo='VENCIDO', mensagem=msg)
            elif dias <= 15:
                msg = f"Lote {lote.numero_lote} de '{produto.nome}' vence em {dias} dia(s) ({lote.data_validade.strftime('%d/%m/%Y')}). Quantidade: {lote.quantidade}."
                if not Alerta.objects.filter(lote=lote, tipo='VENCIMENTO_PROXIMO', visto=False).exists():
                    Alerta.objects.create(produto=produto, lote=lote, tipo='VENCIMENTO_PROXIMO', mensagem=msg)

    @staticmethod
    def marcar_como_visto(alerta_id: int):
        alerta = Alerta.objects.get(id=alerta_id)
        alerta.marcar_como_visto()
        return alerta


class ControladorAutenticacao:
    """
    <<control>> ControladorAutenticacao
    """
    @staticmethod
    def verificar_permissao(usuario: Usuario, acao: str) -> bool:
        if not usuario or not usuario.is_authenticated:
            return False
        return usuario.tem_permissao(acao)
