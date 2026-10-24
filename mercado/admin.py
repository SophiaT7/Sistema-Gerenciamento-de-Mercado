from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Produto, Lote, EntradaMercadoria,
    Caixa, Venda, ItemVenda, Perda, MovimentacaoEstoque, Alerta
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'papel_badge', 'is_active', 'is_staff')
    list_filter = ('papel', 'is_active', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Controle de Acesso do Mercado', {'fields': ('papel',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Controle de Acesso do Mercado', {'fields': ('papel',)}),
    )

    def papel_badge(self, obj):
        cores = {
            'DONO': '#4f46e5',
            'GERENTE': '#0891b2',
            'OPERADOR': '#16a34a',
            'ESTOQUISTA': '#ea580c',
        }
        cor = cores.get(obj.papel, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 9999px; font-weight: 600; font-size: 11px;">{}</span>',
            cor, obj.get_papel_display()
        )
    papel_badge.short_description = 'Papel'


class ProdutoLoteInline(admin.TabularInline):
    """Inline de Lotes dentro do Produto"""
    model = Lote
    extra = 0
    fields = ('numero_lote', 'quantidade', 'custo_unitario', 'data_validade', 'status_validade')
    readonly_fields = ('status_validade',)

    def status_validade(self, obj):
        if not obj or not obj.id or not obj.data_validade:
            return "-"
        if obj.is_vencido():
            return mark_safe('<span style="color: #dc2626; font-weight: bold;">VENCIDO</span>')
        return format_html('<span style="color: #16a34a;">Válido ({} dias)</span>', obj.dias_para_vencer)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'categoria', 'unidade', 'preco_custo_display', 'margem_display', 'preco_venda_display', 'estoque_display', 'status_estoque')
    list_filter = ('categoria', 'unidade', 'ativo')
    search_fields = ('codigo', 'nome')
    inlines = [ProdutoLoteInline]
    fields = ('codigo', 'nome', 'categoria', 'unidade', 'estoque_minimo', 'preco_custo', 'margem_lucro', 'preco_venda', 'ativo')

    def preco_custo_display(self, obj):
        return f"R$ {obj.preco_custo:.2f}"
    preco_custo_display.short_description = 'Custo'

    def margem_display(self, obj):
        return f"{obj.margem_lucro:.1f}%"
    margem_display.short_description = 'Margem'

    def preco_venda_display(self, obj):
        return format_html('<strong>R$ {}</strong>', f'{obj.preco_venda:.2f}')
    preco_venda_display.short_description = 'Preço Venda'

    def estoque_display(self, obj):
        return f"{obj.estoque_atual} {obj.unidade}"
    estoque_display.short_description = 'Estoque Atual'

    def status_estoque(self, obj):
        if obj.precisa_alerta_estoque():
            return mark_safe('<span style="background-color: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-weight: bold;">Estoque Baixo</span>')
        return mark_safe('<span style="background-color: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px;">OK</span>')
    status_estoque.short_description = 'Situação'


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('numero_lote', 'produto', 'quantidade', 'custo_unitario', 'data_validade', 'status_validade')
    list_filter = ('data_validade', 'produto__categoria')
    search_fields = ('numero_lote', 'produto__nome', 'produto__codigo')
    fields = ('produto', 'entrada', 'numero_lote', 'quantidade', 'custo_unitario', 'data_validade')

    def status_validade(self, obj):
        if not obj or not obj.id or not obj.data_validade:
            return "-"
        if obj.is_vencido():
            return mark_safe('<span style="background-color: #dc2626; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;">VENCIDO</span>')
        elif obj.dias_para_vencer <= 15:
            return format_html('<span style="background-color: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;">Vence em {} dias</span>', obj.dias_para_vencer)
        return format_html('<span style="background-color: #10b981; color: white; padding: 2px 6px; border-radius: 4px;">Válido ({} dias)</span>', obj.dias_para_vencer)
    status_validade.short_description = 'Validade'


class EntradaLoteInline(admin.TabularInline):
    """Inline de Lotes dentro da Entrada de Mercadoria"""
    model = Lote
    extra = 0
    fields = ('produto', 'numero_lote', 'quantidade', 'custo_unitario', 'data_validade')


@admin.register(EntradaMercadoria)
class EntradaMercadoriaAdmin(admin.ModelAdmin):
    list_display = ('numero_nota_fiscal', 'fornecedor', 'data_entrada', 'responsavel', 'total_lotes')
    search_fields = ('numero_nota_fiscal', 'fornecedor')
    list_filter = ('data_entrada',)
    inlines = [EntradaLoteInline]
    fields = ('numero_nota_fiscal', 'fornecedor', 'data_entrada', 'responsavel', 'observacao')

    def total_lotes(self, obj):
        return obj.lotes_recebidos.count()
    total_lotes.short_description = 'Qtd Lotes'


class ItemVendaInline(admin.TabularInline):
    """Inline de Itens dentro da Venda"""
    model = ItemVenda
    extra = 0
    fields = ('produto', 'lote', 'quantidade', 'preco_unitario', 'subtotal_display')
    readonly_fields = ('subtotal_display',)

    def subtotal_display(self, obj):
        if not obj or not obj.id or obj.quantidade is None or obj.preco_unitario is None:
            return "R$ 0,00"
        return f"R$ {obj.subtotal:.2f}"
    subtotal_display.short_description = 'Subtotal'


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = ('id', 'operador', 'status_badge', 'data_abertura', 'data_fechamento', 'fundo_troco_display', 'total_vendas_display', 'valor_sistema_display', 'valor_fisico_display', 'diferenca_display')
    list_filter = ('aberto', 'data_abertura', 'operador')
    search_fields = ('id', 'operador__username')
    fields = ('operador', 'aberto', 'data_abertura', 'data_fechamento', 'fundo_troco_inicial', 'valor_sistema', 'valor_fisico_conferido', 'observacao')

    def status_badge(self, obj):
        if obj.aberto:
            return mark_safe('<span style="background-color: #16a34a; color: #fff; padding: 3px 8px; border-radius: 9999px; font-weight: bold;">ABERTO</span>')
        return mark_safe('<span style="background-color: #64748b; color: #fff; padding: 3px 8px; border-radius: 9999px;">FECHADO</span>')
    status_badge.short_description = 'Status'

    def fundo_troco_display(self, obj):
        return f"R$ {obj.fundo_troco_inicial:.2f}"
    fundo_troco_display.short_description = 'Fundo Inicial'

    def total_vendas_display(self, obj):
        return f"R$ {obj.total_vendas_periodo:.2f}"
    total_vendas_display.short_description = 'Total Vendas'

    def valor_sistema_display(self, obj):
        return f"R$ {obj.valor_sistema:.2f}"
    valor_sistema_display.short_description = 'Esperado no Caixa'

    def valor_fisico_display(self, obj):
        if obj.valor_fisico_conferido is None:
            return "-"
        return f"R$ {obj.valor_fisico_conferido:.2f}"
    valor_fisico_display.short_description = 'Conferido'

    def diferenca_display(self, obj):
        if obj.aberto or obj.valor_fisico_conferido is None:
            return "-"
        dif = obj.diferenca
        if abs(dif) < 0.01:
            return mark_safe('<span style="color: #16a34a; font-weight: bold;">R$ 0,00 (Exato)</span>')
        elif dif > 0:
            return format_html('<span style="color: #0284c7; font-weight: bold;">+ R$ {} (Sobra)</span>', f'{dif:.2f}')
        else:
            return format_html('<span style="color: #dc2626; font-weight: bold;">- R$ {} (Quebra)</span>', f'{abs(dif):.2f}')
    diferenca_display.short_description = 'Diferença'


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'operador', 'data_venda', 'meio_pagamento_display', 'total_display', 'caixa')
    list_filter = ('meio_pagamento', 'data_venda', 'operador')
    search_fields = ('id', 'operador__username')
    fields = ('caixa', 'operador', 'meio_pagamento', 'data_venda', 'sincronizado_offline', 'total')
    inlines = [ItemVendaInline]

    def meio_pagamento_display(self, obj):
        return obj.get_meio_pagamento_display()
    meio_pagamento_display.short_description = 'Pagamento'

    def total_display(self, obj):
        return format_html('<strong>R$ {}</strong>', f'{obj.total:.2f}')
    total_display.short_description = 'Total'


@admin.register(Perda)
class PerdaAdmin(admin.ModelAdmin):
    list_display = ('produto', 'quantidade', 'motivo_badge', 'responsavel', 'data_hora')
    list_filter = ('motivo', 'data_hora')
    search_fields = ('produto__nome', 'produto__codigo', 'responsavel__username')
    fields = ('produto', 'lote', 'quantidade', 'motivo', 'responsavel', 'data_hora', 'justificativa')

    def motivo_badge(self, obj):
        return format_html(
            '<span style="background-color: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{}</span>',
            obj.get_motivo_display()
        )
    motivo_badge.short_description = 'Motivo'


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tipo_badge', 'quantidade', 'justificativa', 'usuario', 'data_hora')
    list_filter = ('tipo', 'data_hora')
    search_fields = ('produto__nome', 'justificativa')
    fields = ('produto', 'tipo', 'quantidade', 'justificativa', 'usuario', 'data_hora')

    def tipo_badge(self, obj):
        cores = {
            'ENTRADA': '#dcfce7; color: #166534',
            'SAIDA_VENDA': '#e0e7ff; color: #3730a3',
            'PERDA': '#fee2e2; color: #991b1b',
            'AJUSTE': '#fef3c7; color: #92400e',
        }
        cor = cores.get(obj.tipo, '#f3f4f6; color: #1f2937')
        return format_html('<span style="background-color: {}; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{}</span>', cor, obj.get_tipo_display())
    tipo_badge.short_description = 'Tipo'


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('tipo_badge', 'mensagem_curta', 'status_badge', 'data_criacao', 'produto')
    list_filter = ('visto', 'tipo', 'data_criacao')
    search_fields = ('mensagem', 'produto__nome')
    fields = ('tipo', 'mensagem', 'visto', 'data_criacao', 'produto', 'lote')

    def tipo_badge(self, obj):
        return format_html('<strong>{}</strong>', obj.get_tipo_display())
    tipo_badge.short_description = 'Tipo'

    def mensagem_curta(self, obj):
        return obj.mensagem[:80] + ("..." if len(obj.mensagem) > 80 else "")
    mensagem_curta.short_description = 'Mensagem'

    def status_badge(self, obj):
        if obj.visto:
            return mark_safe('<span style="color: #6b7280;">Lido</span>')
        return mark_safe('<span style="background-color: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;">NOVO</span>')
    status_badge.short_description = 'Status'
