from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum, Count, Q

from .models import (
    Usuario, Produto, Lote, EntradaMercadoria,
    Caixa, Venda, ItemVenda, Perda, MovimentacaoEstoque, Alerta
)
from .services import (
    ControladorProduto, ControladorEntradaMercadoria,
    ControladorCaixa, ControladorVenda, ControladorPerda,
    ControladorAlertas, ControladorAutenticacao
)


def login_view(request):
    """
    recebe requisição do nav e retorna a tela de login, caso o usuário já esteja logado, redireciona para o dashboard
    <<boundary>> TelaLogin
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            messages.success(request, f"Bem-vindo(a) ao sistema, {user.first_name or user.username}!")
            # Se for operador de caixa direto, direciona para o PDV se o caixa estiver aberto
            if user.papel == 'OPERADOR':
                caixa = Caixa.objects.filter(operador=user, aberto=True).first()
                if caixa:
                    return redirect('pdv')
                return redirect('caixa_status')
            return redirect('dashboard')
        else:
            messages.error(request, "Credenciais inválidas. Verifique usuário e senha.")

    return render(request, 'mercado/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, "Sessão encerrada com sucesso.")
    return redirect('login')


@login_required
def dashboard_view(request):
    """
    Painel Principal do Dono do Mercado com métricas em tempo real
    """
    hoje = timezone.now().date()
    
    # Executa verificação periódica de alertas
    ControladorAlertas.verificar_alertas()

    # Métricas
    vendas_hoje = Venda.objects.filter(data_venda__date=hoje)
    total_faturado_hoje = vendas_hoje.aggregate(total=Sum('total'))['total'] or Decimal('0')
    qtd_vendas_hoje = vendas_hoje.count()

    total_produtos = Produto.objects.filter(ativo=True).count()
    produtos_estoque_baixo = [p for p in Produto.objects.filter(ativo=True) if p.precisa_alerta_estoque()]
    
    lotes_vencendo = Lote.objects.filter(
        quantidade__gt=0,
        data_validade__lte=hoje + timezone.timedelta(days=15),
        data_validade__gte=hoje
    ).count()
    lotes_vencidos = Lote.objects.filter(
        quantidade__gt=0,
        data_validade__lt=hoje
    ).count()

    ultimas_vendas = Venda.objects.select_related('operador', 'caixa').order_by('-data_venda')[:6]
    alertas_recentes = Alerta.objects.filter(visto=False).order_by('-data_criacao')[:5]

    # Caixa do operador logado
    caixa_atual = Caixa.objects.filter(operador=request.user, aberto=True).first()
    caixas_abertos = Caixa.objects.filter(aberto=True)

    context = {
        'total_faturado_hoje': total_faturado_hoje,
        'qtd_vendas_hoje': qtd_vendas_hoje,
        'total_produtos': total_produtos,
        'qtd_estoque_baixo': len(produtos_estoque_baixo),
        'lotes_vencendo': lotes_vencendo,
        'lotes_vencidos': lotes_vencidos,
        'ultimas_vendas': ultimas_vendas,
        'alertas_recentes': alertas_recentes,
        'caixa_atual': caixa_atual,
        'caixas_abertos': caixas_abertos,
    }
    return render(request, 'mercado/dashboard.html', context)


# ==========================================
# PRODUTOS (<<boundary>> TelaCadastroProduto)
# ==========================================
@login_required
def produto_lista_view(request):
    query = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '')
    filtro_status = request.GET.get('status', '')

    produtos = Produto.objects.filter(ativo=True).prefetch_related('lotes')

    if query:
        produtos = produtos.filter(Q(nome__icontains=query) | Q(codigo__icontains=query))
    if categoria:
        produtos = produtos.filter(categoria=categoria)

    lista_final = []
    for p in produtos:
        alerta_baixo = p.precisa_alerta_estoque()
        if filtro_status == 'baixo' and not alerta_baixo:
            continue
        lista_final.append({
            'obj': p,
            'estoque': p.estoque_atual,
            'alerta_baixo': alerta_baixo
        })

    context = {
        'produtos': lista_final,
        'categorias': Produto.CATEGORIAS,
        'query': query,
        'categoria_selecionada': categoria,
        'status_selecionado': filtro_status,
    }
    return render(request, 'mercado/produtos/lista.html', context)


@login_required
def produto_criar_view(request):
    if not ControladorAutenticacao.verificar_permissao(request.user, 'cadastrar_produto'):
        messages.error(request, "Acesso negado: seu papel não permite cadastrar produtos.")
        return redirect('produto_lista')

    if request.method == 'POST':
        try:
            codigo = request.POST.get('codigo')
            nome = request.POST.get('nome')
            categoria = request.POST.get('categoria')
            unidade = request.POST.get('unidade')
            estoque_minimo = request.POST.get('estoque_minimo') or 5
            preco_custo = request.POST.get('preco_custo') or 0
            margem_lucro = request.POST.get('margem_lucro') or 30

            ControladorProduto.cadastrar_produto(
                codigo=codigo,
                nome=nome,
                categoria=categoria,
                unidade=unidade,
                estoque_minimo=Decimal(str(estoque_minimo)),
                preco_custo=Decimal(str(preco_custo)),
                margem_lucro=Decimal(str(margem_lucro)),
                usuario=request.user
            )
            messages.success(request, f"Produto '{nome}' cadastrado com sucesso!")
            return redirect('produto_lista')
        except Exception as e:
            messages.error(request, f"Erro ao cadastrar produto: {str(e)}")

    context = {
        'categorias': Produto.CATEGORIAS,
        'unidades': Produto.UNIDADES,
    }
    return render(request, 'mercado/produtos/form.html', context)


@login_required
def produto_alterar_preco_view(request, produto_id):
    if not ControladorAutenticacao.verificar_permissao(request.user, 'alterar_preco'):
        messages.error(request, "Acesso negado: seu papel não permite alterar preços.")
        return redirect('produto_lista')

    produto = get_object_or_404(Produto, id=produto_id)

    if request.method == 'POST':
        try:
            novo_preco = Decimal(str(request.POST.get('novo_preco')))
            ControladorProduto.atualizar_preco(produto.codigo, novo_preco, request.user)
            messages.success(request, f"Preço de venda do produto '{produto.nome}' atualizado para R$ {novo_preco:.2f}!")
            return redirect('produto_lista')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar preço: {str(e)}")

    context = {'produto': produto}
    return render(request, 'mercado/produtos/alterar_preco.html', context)


# ========================================================
# ENTRADA DE MERCADORIA (<<boundary>> TelaEntradaMercadoria)
# ========================================================
@login_required
def entrada_mercadoria_view(request):
    if not ControladorAutenticacao.verificar_permissao(request.user, 'entrada_mercadoria'):
        messages.error(request, "Acesso negado: seu papel não permite registrar entrada de mercadoria.")
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            numero_nota = request.POST.get('numero_nota_fiscal')
            fornecedor = request.POST.get('fornecedor')
            produto_id = request.POST.get('produto_id')
            numero_lote = request.POST.get('numero_lote')
            quantidade = request.POST.get('quantidade')
            custo_unitario = request.POST.get('custo_unitario')
            data_validade = request.POST.get('data_validade')

            produto = get_object_or_404(Produto, id=produto_id)

            lotes_dados = [{
                'produto': produto,
                'numero_lote': numero_lote,
                'quantidade': Decimal(str(quantidade)),
                'custo_unitario': Decimal(str(custo_unitario)),
                'data_validade': data_validade,
            }]

            entrada = ControladorEntradaMercadoria.processar_entrada(
                numero_nota=numero_nota,
                fornecedor=fornecedor,
                lotes_dados=lotes_dados,
                responsavel=request.user
            )

            messages.success(request, f"Entrada NF {entrada.numero_nota_fiscal} registrada com sucesso para o produto '{produto.nome}'!")
            return redirect('entrada_lista')
        except Exception as e:
            messages.error(request, f"Erro ao registrar entrada: {str(e)}")

    produtos = Produto.objects.filter(ativo=True)
    context = {'produtos': produtos}
    return render(request, 'mercado/entradas/form.html', context)


@login_required
def entrada_lista_view(request):
    entradas = EntradaMercadoria.objects.prefetch_related('lotes_recebidos__produto').order_by('-data_entrada')[:50]
    return render(request, 'mercado/entradas/lista.html', {'entradas': entradas})


# ==========================================
# FRENTE DE CAIXA (<<boundary>> TelaCaixa)
# ==========================================
@login_required
def caixa_status_view(request):
    caixa_atual = Caixa.objects.filter(operador=request.user, aberto=True).first()
    caixas_historico = Caixa.objects.filter(operador=request.user).order_by('-data_abertura')[:10]
    
    if request.user.papel in ['DONO', 'GERENTE']:
        caixas_historico = Caixa.objects.all().order_by('-data_abertura')[:15]

    context = {
        'caixa_atual': caixa_atual,
        'caixas_historico': caixas_historico,
    }
    return render(request, 'mercado/caixa/status.html', context)


@login_required
def caixa_abrir_view(request):
    if request.method == 'POST':
        try:
            fundo = Decimal(str(request.POST.get('fundo_troco_inicial') or '0'))
            caixa = ControladorCaixa.abrir_caixa(request.user, fundo)
            messages.success(request, f"Caixa #{caixa.id} aberto com sucesso com fundo de R$ {fundo:.2f}!")
            return redirect('pdv')
        except Exception as e:
            messages.error(request, f"Erro ao abrir caixa: {str(e)}")

    return render(request, 'mercado/caixa/abertura.html')


@login_required
def caixa_fechar_view(request, caixa_id):
    caixa = get_object_or_404(Caixa, id=caixa_id)
    if caixa.operador != request.user and request.user.papel not in ['DONO', 'GERENTE']:
        messages.error(request, "Você não tem permissão para fechar este caixa.")
        return redirect('caixa_status')

    if request.method == 'POST':
        try:
            valor_fisico = Decimal(str(request.POST.get('valor_fisico_conferido') or '0'))
            observacao = request.POST.get('observacao', '')
            ControladorCaixa.fechar_caixa(caixa, valor_fisico, observacao)
            
            dif = caixa.diferenca
            if abs(dif) < Decimal('0.01'):
                messages.success(request, f"Caixa #{caixa.id} fechado com sucesso! Valores conferidos perfeitamente.")
            elif dif > 0:
                messages.warning(request, f"Caixa #{caixa.id} fechado com SOBRA de R$ {dif:.2f}.")
            else:
                messages.error(request, f"Caixa #{caixa.id} fechado com QUEBRA (falta) de R$ {abs(dif):.2f}.")
                
            return redirect('caixa_status')
        except Exception as e:
            messages.error(request, f"Erro ao fechar caixa: {str(e)}")

    caixa.atualizar_valor_sistema()
    context = {'caixa': caixa}
    return render(request, 'mercado/caixa/fechamento.html', context)


# ==========================================
# PONTO DE VENDA (<<boundary>> TelaPDV)
# ==========================================
@login_required
def pdv_view(request):
    caixa_atual = Caixa.objects.filter(operador=request.user, aberto=True).first()
    if not caixa_atual:
        messages.warning(request, "Você precisa abrir o caixa antes de operar o Ponto de Venda (PDV).")
        return redirect('caixa_abrir')

    produtos = Produto.objects.filter(ativo=True)
    context = {
        'caixa': caixa_atual,
        'produtos': produtos,
    }
    return render(request, 'mercado/pdv/index.html', context)


@login_required
def pdv_buscar_produto_api(request):
    """API para busca rápida por código ou nome no PDV"""
    termo = request.GET.get('termo', '').strip()
    if not termo:
        return JsonResponse({'sucesso': False, 'mensagem': 'Termo vazio'})

    produto = Produto.objects.filter(Q(codigo=termo) | Q(codigo__iexact=termo), ativo=True).first()
    if not produto:
        # Busca por nome
        produto = Produto.objects.filter(nome__icontains=termo, ativo=True).first()

    if produto:
        return JsonResponse({
            'sucesso': True,
            'produto': {
                'id': produto.id,
                'codigo': produto.codigo,
                'nome': produto.nome,
                'preco_venda': float(produto.preco_venda),
                'unidade': produto.unidade,
                'estoque': float(produto.estoque_atual),
            }
        })
    return JsonResponse({'sucesso': False, 'mensagem': 'Produto não encontrado'})


@login_required
def pdv_finalizar_venda_api(request):
    """API para processar a venda enviada pelo PDV"""
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'mensagem': 'Método inválido'})

    import json
    try:
        dados = json.loads(request.body)
        meio_pagamento = dados.get('meio_pagamento', 'DINHEIRO')
        itens_dados = dados.get('itens', [])

        if not itens_dados:
            return JsonResponse({'sucesso': False, 'mensagem': 'Carrinho de compras vazio.'})

        caixa = Caixa.objects.filter(operador=request.user, aberto=True).first()
        if not caixa:
            return JsonResponse({'sucesso': False, 'mensagem': 'Nenhum caixa aberto para este operador.'})

        itens_processar = []
        for it in itens_dados:
            p = Produto.objects.get(id=it['produto_id'])
            itens_processar.append({
                'produto': p,
                'quantidade': Decimal(str(it['quantidade'])),
                'preco_unitario': Decimal(str(it['preco_unitario']))
            })

        venda = ControladorVenda.processar_venda(
            operador=request.user,
            meio_pagamento=meio_pagamento,
            itens=itens_processar,
            caixa=caixa
        )

        return JsonResponse({
            'sucesso': True,
            'venda_id': venda.id,
            'total': float(venda.total),
            'meio_pagamento': venda.get_meio_pagamento_display(),
            'data_venda': venda.data_venda.strftime('%d/%m/%Y %H:%M:%S'),
            'mensagem': 'Venda finalizada com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'sucesso': False, 'mensagem': str(e)})


# ==========================================
# PERDAS (<<boundary>> TelaRegistroPerda)
# ==========================================
@login_required
def perda_registrar_view(request):
    if not ControladorAutenticacao.verificar_permissao(request.user, 'registrar_perda'):
        messages.error(request, "Acesso negado: seu papel não permite registrar perdas.")
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            produto_id = request.POST.get('produto_id')
            quantidade = request.POST.get('quantidade')
            motivo = request.POST.get('motivo')
            numero_lote = request.POST.get('numero_lote') or None
            justificativa = request.POST.get('justificativa', '')

            produto = get_object_or_404(Produto, id=produto_id)

            perda = ControladorPerda.registrar_perda(
                codigo_produto=produto.codigo,
                quantidade=Decimal(str(quantidade)),
                motivo=motivo,
                responsavel=request.user,
                numero_lote=numero_lote,
                justificativa=justificativa
            )

            messages.success(request, f"Perda de {perda.quantidade} {produto.unidade} do produto '{produto.nome}' registrada com sucesso.")
            return redirect('perda_lista')
        except Exception as e:
            messages.error(request, f"Erro ao registrar perda: {str(e)}")

    produtos = Produto.objects.filter(ativo=True)
    context = {
        'produtos': produtos,
        'motivos': Perda.MOTIVOS,
    }
    return render(request, 'mercado/perdas/form.html', context)


@login_required
def perda_lista_view(request):
    perdas = Perda.objects.select_related('produto', 'lote', 'responsavel').order_by('-data_hora')[:50]
    return render(request, 'mercado/perdas/lista.html', {'perdas': perdas})


# ==========================================
# ALERTAS (<<boundary>> TelaAlertas)
# ==========================================
@login_required
def alerta_lista_view(request):
    ControladorAlertas.verificar_alertas()
    
    status_filtro = request.GET.get('filtro', 'pendentes')
    if status_filtro == 'todos':
        alertas = Alerta.objects.all().order_by('visto', '-data_criacao')
    else:
        alertas = Alerta.objects.filter(visto=False).order_by('-data_criacao')

    context = {
        'alertas': alertas,
        'filtro': status_filtro,
    }
    return render(request, 'mercado/alertas/lista.html', context)


@login_required
def alerta_marcar_visto_view(request, alerta_id):
    ControladorAlertas.marcar_como_visto(alerta_id)
    messages.success(request, "Alerta marcado como visto.")
    return redirect('alerta_lista')
