from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from mercado.models import Usuario, Produto, Lote, EntradaMercadoria, Caixa, Alerta
from mercado.services import ControladorProduto, ControladorAlertas, ControladorCaixa


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados iniciais para testes e apresentação'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando população de dados...")

        # 1. Usuários
        dono, created = Usuario.objects.get_or_create(
            username='dono',
            defaults={
                'first_name': 'Carlos',
                'last_name': 'Menezes (Dono)',
                'email': 'dono@mercadocentral.com',
                'papel': 'DONO',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            dono.set_password('dono123')
            dono.save()
            self.stdout.write(self.style.SUCCESS("Criado usuário Dono: dono / dono123"))

        operador, created = Usuario.objects.get_or_create(
            username='operador',
            defaults={
                'first_name': 'Juliana',
                'last_name': 'Silva (Caixa)',
                'email': 'operador@mercadocentral.com',
                'papel': 'OPERADOR',
                'is_staff': True
            }
        )
        if created:
            operador.set_password('caixa123')
            operador.save()
            self.stdout.write(self.style.SUCCESS("Criado usuário Operador: operador / caixa123"))

        gerente, created = Usuario.objects.get_or_create(
            username='gerente',
            defaults={
                'first_name': 'Roberto',
                'last_name': 'Almeida (Gerente)',
                'email': 'gerente@mercadocentral.com',
                'papel': 'GERENTE',
                'is_staff': True
            }
        )
        if created:
            gerente.set_password('gerente123')
            gerente.save()

        # 2. Entrada de Mercadoria e Produtos
        entrada, _ = EntradaMercadoria.objects.get_or_create(
            numero_nota_fiscal='NF-984321',
            defaults={
                'fornecedor': 'Distribuidora Alimentos Brasil S/A',
                'responsavel': dono,
                'observacao': 'Carga inicial do estoque'
            }
        )

        produtos_dados = [
            {
                'codigo': '7891000100101', 'nome': 'Arroz Branco Tipo 1 5kg',
                'categoria': 'MERCEARIA', 'unidade': 'PCT', 'minimo': 15,
                'custo': Decimal('18.50'), 'margem': Decimal('35.00'),
                'lotes': [
                    {'num': 'L-ARR-2026-A', 'qtd': Decimal('50'), 'dias_val': 180},
                ]
            },
            {
                'codigo': '7891000200202', 'nome': 'Feijão Carioca 1kg',
                'categoria': 'MERCEARIA', 'unidade': 'PCT', 'minimo': 20,
                'custo': Decimal('6.20'), 'margem': Decimal('40.00'),
                'lotes': [
                    {'num': 'L-FEJ-2026-01', 'qtd': Decimal('45'), 'dias_val': 120},
                ]
            },
            {
                'codigo': '7891000300303', 'nome': 'Leite Integral 1L',
                'categoria': 'FRIOS', 'unidade': 'L', 'minimo': 30,
                'custo': Decimal('3.80'), 'margem': Decimal('30.00'),
                'lotes': [
                    {'num': 'L-LEI-URGENTE', 'qtd': Decimal('8'), 'dias_val': 5},  # Vencimento próximo (dispara alerta)
                    {'num': 'L-LEI-NOVO', 'qtd': Decimal('20'), 'dias_val': 60},
                ]
            },
            {
                'codigo': '7891000400404', 'nome': 'Óleo de Soja 900ml',
                'categoria': 'MERCEARIA', 'unidade': 'UN', 'minimo': 25,
                'custo': Decimal('4.90'), 'margem': Decimal('32.00'),
                'lotes': [
                    {'num': 'L-OLE-001', 'qtd': Decimal('40'), 'dias_val': 150},
                ]
            },
            {
                'codigo': '7891000500505', 'nome': 'Café Torrado e Moído 500g',
                'categoria': 'MERCEARIA', 'unidade': 'PCT', 'minimo': 15,
                'custo': Decimal('12.50'), 'margem': Decimal('35.00'),
                'lotes': [
                    {'num': 'L-CAF-01', 'qtd': Decimal('30'), 'dias_val': 90},
                ]
            },
            {
                'codigo': '7891000600606', 'nome': 'Detergente Líquido 500ml',
                'categoria': 'LIMPEZA', 'unidade': 'UN', 'minimo': 20,
                'custo': Decimal('1.80'), 'margem': Decimal('50.00'),
                'lotes': [
                    {'num': 'L-DET-01', 'qtd': Decimal('60'), 'dias_val': 365},
                ]
            },
            {
                'codigo': '7891000700707', 'nome': 'Refrigerante Cola 2L',
                'categoria': 'BEBIDAS', 'unidade': 'UN', 'minimo': 20,
                'custo': Decimal('5.50'), 'margem': Decimal('45.00'),
                'lotes': [
                    {'num': 'L-REF-99', 'qtd': Decimal('4'), 'dias_val': 45},  # Estoque baixo (4 < 20) -> dispara alerta
                ]
            },
            {
                'codigo': '7891000800808', 'nome': 'Pão de Forma Tradicional 500g',
                'categoria': 'PADARIA', 'unidade': 'PCT', 'minimo': 10,
                'custo': Decimal('4.20'), 'margem': Decimal('40.00'),
                'lotes': [
                    {'num': 'L-PAO-VENCIDO', 'qtd': Decimal('2'), 'dias_val': -2},  # Lote já vencido -> dispara alerta de perda
                ]
            },
        ]

        hoje = timezone.now().date()
        for p_data in produtos_dados:
            produto, _ = Produto.objects.get_or_create(
                codigo=p_data['codigo'],
                defaults={
                    'nome': p_data['nome'],
                    'categoria': p_data['categoria'],
                    'unidade': p_data['unidade'],
                    'estoque_minimo': p_data['minimo'],
                    'preco_custo': p_data['custo'],
                    'margem_lucro': p_data['margem'],
                    'preco_venda': (p_data['custo'] * (Decimal('1') + (p_data['margem'] / Decimal('100')))).quantize(Decimal('0.01'))
                }
            )

            for l_data in p_data['lotes']:
                data_val = hoje + timedelta(days=l_data['dias_val'])
                Lote.objects.get_or_create(
                    produto=produto,
                    numero_lote=l_data['num'],
                    defaults={
                        'entrada': entrada,
                        'quantidade': l_data['qtd'],
                        'custo_unitario': p_data['custo'],
                        'data_validade': data_val
                    }
                )

        # 3. Caixa inicial aberto para o operador
        caixa_aberto = Caixa.objects.filter(aberto=True, operador=operador).first()
        if not caixa_aberto:
            caixa_aberto = Caixa.objects.create(
                operador=operador,
                fundo_troco_inicial=Decimal('150.00'),
                valor_sistema=Decimal('150.00'),
                aberto=True
            )
            self.stdout.write(self.style.SUCCESS("Caixa inicial aberto para operador com fundo de R$ 150,00"))

        # 4. Gerar Alertas Automáticos
        ControladorAlertas.verificar_alertas()
        total_alertas = Alerta.objects.count()
        self.stdout.write(self.style.SUCCESS(f"População finalizada com sucesso! {total_alertas} alertas gerados."))
