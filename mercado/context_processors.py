from .models import Alerta, Caixa

def alertas_context(request):
    """
    Disponibiliza alertas pendentes e status do caixa globalmente para os templates
    """
    if request.user.is_authenticated:
        alertas_pendentes = Alerta.objects.filter(visto=False).order_by('-data_criacao')[:10]
        total_alertas = Alerta.objects.filter(visto=False).count()
        # Caixa atualmente aberto pelo operador ou último caixa aberto no sistema
        caixa_aberto = Caixa.objects.filter(aberto=True, operador=request.user).first()
        if not caixa_aberto and request.user.papel in ['DONO', 'GERENTE']:
            caixa_aberto = Caixa.objects.filter(aberto=True).first()

        return {
            'alertas_pendentes': alertas_pendentes,
            'total_alertas': total_alertas,
            'caixa_aberto_usuario': caixa_aberto,
        }
    return {
        'alertas_pendentes': [],
        'total_alertas': 0,
        'caixa_aberto_usuario': None,
    }
