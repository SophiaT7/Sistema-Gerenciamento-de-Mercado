from django.urls import path
from . import views

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard Principal
    path('', views.dashboard_view, name='dashboard'),
    
    # Produtos (<<boundary>> TelaCadastroProduto)
    path('produtos/', views.produto_lista_view, name='produto_lista'),
    path('produtos/novo/', views.produto_criar_view, name='produto_criar'),
    path('produtos/<int:produto_id>/preco/', views.produto_alterar_preco_view, name='produto_alterar_preco'),
    
    # Entrada de Mercadorias (<<boundary>> TelaEntradaMercadoria)
    path('entradas/', views.entrada_lista_view, name='entrada_lista'),
    path('entradas/nova/', views.entrada_mercadoria_view, name='entrada_mercadoria'),
    
    # Caixa (<<boundary>> TelaCaixa)
    path('caixa/', views.caixa_status_view, name='caixa_status'),
    path('caixa/abrir/', views.caixa_abrir_view, name='caixa_abrir'),
    path('caixa/<int:caixa_id>/fechar/', views.caixa_fechar_view, name='caixa_fechar'),
    
    # PDV - Ponto de Venda (<<boundary>> TelaPDV)
    path('pdv/', views.pdv_view, name='pdv'),
    path('api/pdv/buscar/', views.pdv_buscar_produto_api, name='pdv_buscar_api'),
    path('api/pdv/finalizar/', views.pdv_finalizar_venda_api, name='pdv_finalizar_api'),
    
    # Perdas (<<boundary>> TelaRegistroPerda)
    path('perdas/', views.perda_lista_view, name='perda_lista'),
    path('perdas/nova/', views.perda_registrar_view, name='perda_registrar'),
    
    # Alertas (<<boundary>> TelaAlertas)
    path('alertas/', views.alerta_lista_view, name='alerta_lista'),
    path('alertas/<int:alerta_id>/visto/', views.alerta_marcar_visto_view, name='alerta_marcar_visto'),
]
