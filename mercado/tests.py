from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from mercado.models import Usuario, Produto, Lote, Caixa, Venda, Alerta
from mercado.services import ControladorProduto, ControladorVenda, ControladorCaixa, ControladorAlertas


class AdminProdutoTest(TestCase):
    def test_cadastrar_produto_no_admin_carrega_lista(self):
        admin = Usuario.objects.create_superuser(
            username='admin_teste',
            email='admin@example.com',
            password='123'
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse('admin:mercado_produto_add'),
            {
                'codigo': '7890002',
                'nome': 'Produto criado no admin',
                'categoria': 'MERCEARIA',
                'unidade': 'UN',
                'estoque_minimo': '5.00',
                'preco_custo': '10.00',
                'margem_lucro': '30.00',
                'preco_venda': '0.00',
                'ativo': 'on',
                '_save': 'Salvar',
                'lotes-TOTAL_FORMS': '0',
                'lotes-INITIAL_FORMS': '0',
                'lotes-MIN_NUM_FORMS': '0',
                'lotes-MAX_NUM_FORMS': '1000',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Produto.objects.filter(codigo='7890002').exists())
        self.assertContains(response, 'Produto criado no admin')


class MercadoBCEEngenhariaSoftwareTest(TestCase):
    """
    Testes unitários e de integração validando os conceitos de Engenharia de Software
    e o padrão BCE (Boundary, Control, Entity) extraídos do Astah.
    """

    def setUp(self):
        # 1. Usuários
        self.dono = Usuario.objects.create_user(
            username='dono_teste',
            password='123',
            papel='DONO'
        )
        self.operador = Usuario.objects.create_user(
            username='operador_teste',
            password='123',
            papel='OPERADOR'
        )

        # 2. Produto e Lotes
        self.produto = ControladorProduto.cadastrar_produto(
            codigo='7890001',
            nome='Arroz 5kg Teste',
            categoria='MERCEARIA',
            unidade='PCT',
            estoque_minimo=Decimal('10'),
            preco_custo=Decimal('20.00'),
            margem_lucro=Decimal('25.00'),
            usuario=self.dono
        )

        hoje = timezone.now().date()
        # Lote 1: Vence em 10 dias (deve sair primeiro no FEFO)
        self.lote1 = Lote.objects.create(
            produto=self.produto,
            numero_lote='LOTE-01',
            quantidade=Decimal('15'),
            custo_unitario=Decimal('20.00'),
            data_validade=hoje + timedelta(days=10)
        )
        # Lote 2: Vence em 60 dias
        self.lote2 = Lote.objects.create(
            produto=self.produto,
            numero_lote='LOTE-02',
            quantidade=Decimal('20'),
            custo_unitario=Decimal('20.00'),
            data_validade=hoje + timedelta(days=60)
        )

        # 3. Caixa
        self.caixa = ControladorCaixa.abrir_caixa(self.operador, Decimal('100.00'))

    def test_calculo_preco_venda_e_margem(self):
        """Testa regra de negócio de formação de preço de venda (ControladorProduto / Produto)"""
        # Custo 20.00 + 25% de margem = 25.00
        self.assertEqual(self.produto.preco_venda, Decimal('25.00'))
        
        # Atualiza preço para 30.00 e verifica recálculo da margem
        self.produto.atualizar_preco_venda(Decimal('30.00'))
        self.assertEqual(self.produto.preco_venda, Decimal('30.00'))
        # Margem: (30 - 20) / 20 = 50%
        self.assertEqual(self.produto.margem_lucro, Decimal('50.00'))

    def test_permissao_papeis(self):
        """Testa se os papéis de usuários (Dono vs Operador) respeitam a matriz de permissões"""
        self.assertTrue(self.dono.tem_permissao('cadastrar_produto'))
        self.assertTrue(self.dono.tem_permissao('alterar_preco'))
        self.assertFalse(self.operador.tem_permissao('cadastrar_produto'))
        self.assertFalse(self.operador.tem_permissao('alterar_preco'))
        self.assertTrue(self.operador.tem_permissao('vender'))

    def test_venda_pdv_baixa_estoque_fefo(self):
        """
        Testa processamento de venda pelo ControladorVenda e método FEFO:
        O lote mais próximo da validade (lote1) deve ter sua quantidade consumida primeiro.
        """
        itens = [{
            'produto': self.produto,
            'quantidade': Decimal('18'),  # 15 do lote1 + 3 do lote2
            'preco_unitario': self.produto.preco_venda
        }]

        venda = ControladorVenda.processar_venda(
            operador=self.operador,
            meio_pagamento='DINHEIRO',
            itens=itens,
            caixa=self.caixa
        )

        self.assertEqual(venda.total, Decimal('450.00'))  # 18 * 25.00 = 450.00
        self.lote1.refresh_from_db()
        self.lote2.refresh_from_db()

        # Lote 1 foi totalmente consumido
        self.assertEqual(self.lote1.quantidade, Decimal('0'))
        # Lote 2 teve 3 unidades baixadas (20 - 3 = 17)
        self.assertEqual(self.lote2.quantidade, Decimal('17'))
        # Estoque total do produto agora é 17
        self.assertEqual(self.produto.estoque_atual, Decimal('17'))

    def test_fechamento_caixa_e_diferenca(self):
        """Testa conciliação e fechamento de caixa pelo ControladorCaixa"""
        # Caixa iniciou com 100. Realizamos uma venda de 50 em dinheiro.
        itens = [{
            'produto': self.produto,
            'quantidade': Decimal('2'),
            'preco_unitario': Decimal('25.00')
        }]
        ControladorVenda.processar_venda(
            operador=self.operador,
            meio_pagamento='DINHEIRO',
            itens=itens,
            caixa=self.caixa
        )

        self.caixa.refresh_from_db()
        self.assertEqual(self.caixa.valor_sistema, Decimal('150.00'))  # 100 fundo + 50 dinheiro

        # Fechamento com valor físico conferido de 145 (quebra de 5.00)
        ControladorCaixa.fechar_caixa(self.caixa, Decimal('145.00'), "Quebra de R$ 5,00")
        self.assertFalse(self.caixa.aberto)
        self.assertEqual(self.caixa.diferenca, Decimal('-5.00'))

        # Deve ter sido gerado um alerta de diferença de caixa
        alerta = Alerta.objects.filter(tipo='DIFERENCA_CAIXA').first()
        self.assertIsNotNone(alerta)
        self.assertIn("QUEBRA", alerta.mensagem)
