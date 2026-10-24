from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from decimal import Decimal


class Usuario(AbstractUser):
    """
    Entidade Usuario (<<entity>>)
    Papeis: Dono do Mercado, Gerente, Operador de Caixa, Estoquista
    """
    PAPEIS = (
        ('DONO', 'Dono do Mercado'),
        ('GERENTE', 'Gerente'),
        ('OPERADOR', 'Operador de Caixa'),
        ('ESTOQUISTA', 'Estoquista'),
    )
    papel = models.CharField(max_length=20, choices=PAPEIS, default='OPERADOR', verbose_name='Papel')

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def tem_permissao(self, acao: str) -> bool:
        """
        Regra de permissões conforme diagrama de classes
        """
        if self.is_superuser or self.papel == 'DONO':
            return True
        if self.papel == 'GERENTE':
            return acao in [
                'cadastrar_produto', 'alterar_preco', 'entrada_mercadoria',
                'registrar_perda', 'ver_alertas', 'abrir_caixa', 'fechar_caixa', 'vender'
            ]
        if self.papel == 'ESTOQUISTA':
            return acao in ['cadastrar_produto', 'entrada_mercadoria', 'registrar_perda', 'ver_alertas']
        if self.papel == 'OPERADOR':
            return acao in ['vender', 'abrir_caixa', 'fechar_caixa']
        return False

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_papel_display()})"


class Produto(models.Model):
    """
    Entidade Produto (<<entity>>)
    """
    CATEGORIAS = (
        ('MERCEARIA', 'Mercearia'),
        ('BEBIDAS', 'Bebidas'),
        ('HORTIFRUTI', 'Hortifruti'),
        ('PADARIA', 'Padaria'),
        ('AÇOUGUE', 'Açougue'),
        ('FRIOS', 'Frios e Laticínios'),
        ('LIMPEZA', 'Limpeza'),
        ('HIGIENE', 'Higiene Pessoal'),
        ('OUTROS', 'Outros'),
    )
    UNIDADES = (
        ('UN', 'Unidade (UN)'),
        ('KG', 'Quilo (KG)'),
        ('L', 'Litro (L)'),
        ('CX', 'Caixa (CX)'),
        ('PCT', 'Pacote (PCT)'),
    )

    codigo = models.CharField(max_length=50, unique=True, verbose_name='Código de Barras / Código')
    nome = models.CharField(max_length=150, verbose_name='Nome do Produto')
    categoria = models.CharField(max_length=30, choices=CATEGORIAS, default='MERCEARIA', verbose_name='Categoria')
    unidade = models.CharField(max_length=10, choices=UNIDADES, default='UN', verbose_name='Unidade de Medida')
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=5, verbose_name='Estoque Mínimo')
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Preço de Custo (R$)')
    margem_lucro = models.DecimalField(max_digits=5, decimal_places=2, default=30.00, verbose_name='Margem de Lucro (%)')
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Preço de Venda (R$)')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    def save(self, *args, **kwargs):
        if self.preco_custo is None:
            self.preco_custo = Decimal('0.00')
        if self.margem_lucro is None:
            self.margem_lucro = Decimal('30.00')
        # Se preco_venda não for informado ou for zero, calcula com base na margem de lucro
        if not self.preco_venda or self.preco_venda == 0:
            custo = Decimal(str(self.preco_custo or 0))
            margem = Decimal(str(self.margem_lucro or 0))
            self.preco_venda = (custo * (Decimal('1') + (margem / Decimal('100')))).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    def atualizar_preco_venda(self, novo_preco: Decimal):
        self.preco_venda = Decimal(str(novo_preco)).quantize(Decimal('0.01'))
        if self.preco_custo and self.preco_custo > 0:
            # Recalcula a margem de lucro
            self.margem_lucro = (((self.preco_venda - self.preco_custo) / self.preco_custo) * Decimal('100')).quantize(Decimal('0.01'))
        self.save()

    @property
    def estoque_atual(self) -> Decimal:
        """Soma a quantidade de todos os lotes ativos com quantidade > 0"""
        total = self.lotes.filter(quantidade__gt=0).aggregate(total=models.Sum('quantidade'))['total']
        return Decimal(str(total or 0))

    def precisa_alerta_estoque(self) -> bool:
        return self.estoque_atual <= self.estoque_minimo

    def __str__(self):
        return f"{self.codigo} - {self.nome} (R$ {self.preco_venda})"


class EntradaMercadoria(models.Model):
    """
    Entidade EntradaMercadoria (<<entity>>)
    """
    numero_nota_fiscal = models.CharField(max_length=60, verbose_name='Número da Nota Fiscal')
    fornecedor = models.CharField(max_length=150, verbose_name='Fornecedor')
    data_entrada = models.DateTimeField(default=timezone.now, blank=True, verbose_name='Data de Entrada')
    responsavel = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Responsável')
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')

    class Meta:
        verbose_name = 'Entrada de Mercadoria'
        verbose_name_plural = 'Entradas de Mercadorias'
        ordering = ['-data_entrada']

    def __str__(self):
        return f"NF {self.numero_nota_fiscal} - {self.fornecedor} ({self.data_entrada.strftime('%d/%m/%Y')})"


class Lote(models.Model):
    """
    Entidade Lote (<<entity>>)
    """
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='lotes', verbose_name='Produto')
    entrada = models.ForeignKey(EntradaMercadoria, on_delete=models.CASCADE, related_name='lotes_recebidos', null=True, blank=True, verbose_name='Entrada NF')
    numero_lote = models.CharField(max_length=60, verbose_name='Número do Lote')
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Quantidade em Estoque')
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Custo Unitário (R$)')
    data_validade = models.DateField(verbose_name='Data de Validade')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['data_validade', 'id']

    @property
    def vencido(self) -> bool:
        return self.is_vencido()

    def is_vencido(self) -> bool:
        if not self.data_validade:
            return False
        return self.data_validade < timezone.now().date()

    @property
    def dias_para_vencer(self) -> int:
        if not self.data_validade:
            return 0
        hoje = timezone.now().date()
        return (self.data_validade - hoje).days

    def baixar_quantidade(self, qtd: Decimal):
        qtd = Decimal(str(qtd))
        if qtd > self.quantidade:
            raise ValueError(f"Quantidade a baixar ({qtd}) maior que disponível no lote {self.numero_lote} ({self.quantidade})")
        self.quantidade -= qtd
        self.save()

    def __str__(self):
        status = "VENCIDO" if self.is_vencido() else f"Val: {self.data_validade.strftime('%d/%m/%Y') if self.data_validade else 'N/A'}"
        return f"Lote {self.numero_lote} | {self.produto.nome} | Qtd: {self.quantidade} | {status}"


class Caixa(models.Model):
    """
    Entidade Caixa (<<entity>>)
    """
    operador = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='caixas', verbose_name='Operador')
    aberto = models.BooleanField(default=True, verbose_name='Caixa Aberto?')
    data_abertura = models.DateTimeField(default=timezone.now, blank=True, verbose_name='Data de Abertura')
    data_fechamento = models.DateTimeField(null=True, blank=True, verbose_name='Data de Fechamento')
    fundo_troco_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Fundo de Troco Inicial (R$)')
    valor_fisico_conferido = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Valor Físico Conferido (R$)')
    valor_sistema = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Valor Esperado no Sistema (R$)')
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação do Fechamento')

    class Meta:
        verbose_name = 'Caixa'
        verbose_name_plural = 'Caixas'
        ordering = ['-data_abertura']

    @property
    def total_vendas_periodo(self) -> Decimal:
        total = self.vendas.aggregate(total=models.Sum('total'))['total']
        return Decimal(str(total or 0))

    @property
    def total_dinheiro(self) -> Decimal:
        total = self.vendas.filter(meio_pagamento='DINHEIRO').aggregate(total=models.Sum('total'))['total']
        return Decimal(str(total or 0))

    def atualizar_valor_sistema(self):
        """O valor do sistema em caixa é o fundo inicial + vendas em dinheiro"""
        self.valor_sistema = Decimal(str(self.fundo_troco_inicial or 0)) + self.total_dinheiro
        self.save()

    def fechar_caixa(self, valor_fisico: Decimal, observacao: str = ""):
        self.atualizar_valor_sistema()
        self.valor_fisico_conferido = Decimal(str(valor_fisico))
        self.observacao = observacao
        self.aberto = False
        self.data_fechamento = timezone.now()
        self.save()

    @property
    def diferenca(self) -> Decimal:
        """Diferença entre o que foi contado e o que o sistema esperava (Quebra ou Sobra)"""
        if self.valor_fisico_conferido is None:
            return Decimal('0')
        return self.valor_fisico_conferido - self.valor_sistema

    def __str__(self):
        status = "ABERTO" if self.aberto else "FECHADO"
        data_str = self.data_abertura.strftime('%d/%m/%Y %H:%M') if self.data_abertura else ""
        return f"Caixa #{self.id} - {self.operador.username} ({status}) - {data_str}"


class Venda(models.Model):
    """
    Entidade Venda (<<entity>>)
    """
    MEIOS_PAGAMENTO = (
        ('DINHEIRO', 'Dinheiro'),
        ('CARTAO_DEBITO', 'Cartão de Débito'),
        ('CARTAO_CREDITO', 'Cartão de Crédito'),
        ('PIX', 'PIX'),
    )

    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name='vendas', null=True, blank=True, verbose_name='Caixa')
    operador = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='vendas_realizadas', verbose_name='Operador')
    meio_pagamento = models.CharField(max_length=30, choices=MEIOS_PAGAMENTO, default='DINHEIRO', verbose_name='Meio de Pagamento')
    data_venda = models.DateTimeField(default=timezone.now, blank=True, verbose_name='Data da Venda')
    sincronizado_offline = models.BooleanField(default=False, verbose_name='Sincronizado Offline?')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Valor Total (R$)')

    class Meta:
        verbose_name = 'Venda'
        verbose_name_plural = 'Vendas'
        ordering = ['-data_venda']

    def recalcular_total(self):
        soma = sum([item.subtotal for item in self.itens.all()])
        self.total = Decimal(str(soma)).quantize(Decimal('0.01'))
        self.save()
        if self.caixa and self.caixa.aberto:
            self.caixa.atualizar_valor_sistema()

    def __str__(self):
        data_str = self.data_venda.strftime('%d/%m/%Y %H:%M') if self.data_venda else ""
        return f"Venda #{self.id} - R$ {self.total} ({self.get_meio_pagamento_display()}) - {data_str}"


class ItemVenda(models.Model):
    """
    Entidade ItemVenda (<<entity>>)
    """
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens', verbose_name='Venda')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_vendidos', verbose_name='Produto')
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Lote Utilizado')
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name='Quantidade')
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Preço Unitário (R$)')

    class Meta:
        verbose_name = 'Item da Venda'
        verbose_name_plural = 'Itens da Venda'

    @property
    def subtotal(self) -> Decimal:
        if self.quantidade is None or self.preco_unitario is None:
            return Decimal('0.00')
        try:
            return (Decimal(str(self.quantidade)) * Decimal(str(self.preco_unitario))).quantize(Decimal('0.01'))
        except Exception:
            return Decimal('0.00')

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} (R$ {self.preco_unitario})"


class Perda(models.Model):
    """
    Entidade Perda (<<entity>>)
    """
    MOTIVOS = (
        ('VENCIMENTO', 'Produto Vencido'),
        ('AVARIA', 'Avaria / Danificado'),
        ('FURTO', 'Furto / Extravio'),
        ('DESCARTE', 'Descarte / Qualidade'),
        ('OUTRO', 'Outro Motivo'),
    )

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='perdas', verbose_name='Produto')
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Lote')
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Quantidade Perdida')
    motivo = models.CharField(max_length=30, choices=MOTIVOS, default='AVARIA', verbose_name='Motivo da Perda')
    responsavel = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='perdas_registradas', verbose_name='Responsável')
    data_hora = models.DateTimeField(default=timezone.now, blank=True, verbose_name='Data e Hora')
    justificativa = models.TextField(blank=True, null=True, verbose_name='Justificativa Detalhada')

    class Meta:
        verbose_name = 'Registro de Perda'
        verbose_name_plural = 'Registros de Perdas'
        ordering = ['-data_hora']

    def __str__(self):
        return f"Perda {self.produto.nome} - Qtd: {self.quantidade} ({self.get_motivo_display()})"


class MovimentacaoEstoque(models.Model):
    """
    Entidade MovimentacaoEstoque (<<entity>>)
    Rastreamento de auditoria de qualquer alteração no estoque
    """
    TIPOS = (
        ('ENTRADA', 'Entrada por Nota Fiscal'),
        ('SAIDA_VENDA', 'Saída por Venda PDV'),
        ('PERDA', 'Saída por Perda/Avaria'),
        ('AJUSTE', 'Ajuste Manual de Inventário'),
    )

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes', verbose_name='Produto')
    tipo = models.CharField(max_length=30, choices=TIPOS, verbose_name='Tipo de Movimentação')
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Quantidade')
    justificativa = models.CharField(max_length=255, verbose_name='Justificativa / Documento')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Usuário Autor')
    data_hora = models.DateTimeField(default=timezone.now, blank=True, verbose_name='Data/Hora')

    class Meta:
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        ordering = ['-data_hora']

    def __str__(self):
        data_str = self.data_hora.strftime('%d/%m/%Y %H:%M') if self.data_hora else ""
        return f"[{self.tipo}] {self.produto.nome} ({self.quantidade}) em {data_str}"


class Alerta(models.Model):
    """
    Entidade Alerta (<<entity>>)
    """
    TIPOS = (
        ('ESTOQUE_BAIXO', 'Estoque Baixo'),
        ('VENCIMENTO_PROXIMO', 'Produto Próximo do Vencimento'),
        ('VENCIDO', 'Produto Vencido em Estoque'),
        ('DIFERENCA_CAIXA', 'Diferença no Fechamento de Caixa'),
        ('SISTEMA', 'Aviso do Sistema'),
    )

    tipo = models.CharField(max_length=30, choices=TIPOS, default='ESTOQUE_BAIXO', verbose_name='Tipo de Alerta')
    mensagem = models.TextField(verbose_name='Mensagem do Alerta')
    visto = models.BooleanField(default=False, verbose_name='Visto pelo Dono?')
    data_criacao = models.DateTimeField(default=timezone.now, blank=True, verbose_name='Data de Criação')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, null=True, blank=True, related_name='alertas')
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, null=True, blank=True, related_name='alertas')

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['visto', '-data_criacao']

    def marcar_como_visto(self):
        self.visto = True
        self.save()

    def __str__(self):
        status = "Lido" if self.visto else "PENDENTE"
        return f"[{status}] [{self.get_tipo_display()}] {self.mensagem[:50]}"
