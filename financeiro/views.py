import csv
from datetime import date
from django.db import models
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden

from .models import Familiar, VinculoFamiliar, Transacao, Categoria
from .forms import CadastroUsuarioForm, FamiliarForm, EntrarFamiliaForm, TransacaoForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'financeiro/login.html', {'form': form})


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('onboarding')
    else:
        form = CadastroUsuarioForm()
    return render(request, 'financeiro/cadastro.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def onboarding_view(request):
    vinculo_aprovado = VinculoFamiliar.objects.filter(usuario=request.user, status='APROVADO').first()
    if vinculo_aprovado:
        return redirect('meus_familiares')
        
    vinculo_pendente = VinculoFamiliar.objects.filter(usuario=request.user, status='PENDENTE').first()
    if vinculo_pendente:
        return render(request, 'financeiro/pendente.html', {'vinculo': vinculo_pendente})

    form_familiar = FamiliarForm()
    form_entrar = EntrarFamiliaForm()

    if request.method == 'POST':
        if 'criar_familiar' in request.POST:
            form_familiar = FamiliarForm(request.POST)
            if form_familiar.is_valid():
                familiar = form_familiar.save()
                VinculoFamiliar.objects.create(
                    usuario=request.user,
                    familiar=familiar,
                    papel='GESTOR',
                    status='APROVADO'
                )
                request.session['familiar_ativo_id'] = familiar.id
                return redirect('index')
        elif 'entrar_familia' in request.POST:
            form_entrar = EntrarFamiliaForm(request.POST)
            if form_entrar.is_valid():
                codigo = form_entrar.cleaned_data['codigo_convite'].strip().upper()
                familiar = Familiar.objects.filter(codigo_convite=codigo).first()
                if familiar:
                    vinculo, _ = VinculoFamiliar.objects.get_or_create(
                        usuario=request.user,
                        familiar=familiar,
                        defaults={'papel': 'MEMBRO', 'status': 'PENDENTE'}
                    )
                    return render(request, 'financeiro/pendente.html', {'vinculo': vinculo})
                else:
                    form_entrar.add_error('codigo_convite', 'Código de convite não encontrado.')

    return render(request, 'financeiro/onboarding.html', {
        'form_familiar': form_familiar,
        'form_entrar': form_entrar
    })


@login_required
def meus_familiares_view(request):
    vinculos = VinculoFamiliar.objects.filter(
        usuario=request.user, status='APROVADO'
    ).select_related('familiar')

    if not vinculos.exists():
        return redirect('onboarding')

    familiares_gestor = vinculos.filter(papel='GESTOR').values_list('familiar_id', flat=True)
    solicitacoes_pendentes = VinculoFamiliar.objects.filter(
        familiar_id__in=familiares_gestor, status='PENDENTE'
    ).select_related('usuario', 'familiar')

    form_familiar = FamiliarForm()
    form_entrar = EntrarFamiliaForm()

    if request.method == 'POST':
        if 'criar_familiar' in request.POST:
            form_familiar = FamiliarForm(request.POST)
            if form_familiar.is_valid():
                familiar = form_familiar.save()
                VinculoFamiliar.objects.create(
                    usuario=request.user,
                    familiar=familiar,
                    papel='GESTOR',
                    status='APROVADO'
                )
                request.session['familiar_ativo_id'] = familiar.id
                return redirect('index')
        elif 'entrar_familia' in request.POST:
            form_entrar = EntrarFamiliaForm(request.POST)
            if form_entrar.is_valid():
                codigo = form_entrar.cleaned_data['codigo_convite'].strip().upper()
                familiar = Familiar.objects.filter(codigo_convite=codigo).first()
                if familiar:
                    vinculo, _ = VinculoFamiliar.objects.get_or_create(
                        usuario=request.user,
                        familiar=familiar,
                        defaults={'papel': 'MEMBRO', 'status': 'PENDENTE'}
                    )
                    return render(request, 'financeiro/pendente.html', {'vinculo': vinculo})
                else:
                    form_entrar.add_error('codigo_convite', 'Código de convite não encontrado.')

    return render(request, 'financeiro/meus_familiares.html', {
        'vinculos': vinculos,
        'form_familiar': form_familiar,
        'form_entrar': form_entrar,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'total_solicitacoes': solicitacoes_pendentes.count(),
    })


@login_required
def selecionar_familiar(request, familiar_id):
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar_id=familiar_id, status='APROVADO').first()
    if vinculo:
        request.session['familiar_ativo_id'] = vinculo.familiar.id
    return redirect('index')


@login_required
def criar_categoria(request, familiar_id):
    familiar = get_object_or_404(Familiar, id=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, papel='GESTOR', status='APROVADO').first()
    if not vinculo:
        return HttpResponseForbidden("Apenas o Gestor pode criar novas categorias.")

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', 'SAIDA')
        if nome:
            Categoria.objects.create(nome=nome, tipo=tipo, familiar=familiar)
            messages.success(request, f'Categoria "{nome}" criada com sucesso!')
    return redirect('index')


@login_required
def excluir_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=categoria.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not vinculo:
        return HttpResponseForbidden("Apenas o Gestor pode excluir categorias.")

    if categoria.transacoes.exists():
        messages.error(request, f'A categoria "{categoria.nome}" já possui lançamentos vinculados e não pode ser removida.')
    else:
        categoria.delete()
        messages.success(request, f'Categoria "{categoria.nome}" excluída.')

    return redirect('index')


@login_required
def index(request):
    vinculos = VinculoFamiliar.objects.filter(usuario=request.user, status='APROVADO').select_related('familiar')
    if not vinculos.exists():
        return redirect('onboarding')

    familiar_ativo_id = request.session.get('familiar_ativo_id')
    familiar_atual = None
    if familiar_ativo_id:
        vinculo_atual = vinculos.filter(familiar_id=familiar_ativo_id).first()
        if vinculo_atual:
            familiar_atual = vinculo_atual.familiar

    if not familiar_atual:
        familiar_atual = vinculos.first().familiar
        request.session['familiar_ativo_id'] = familiar_atual.id

    vinculo_corrente = vinculos.get(familiar=familiar_atual)
    eh_gestor = (vinculo_corrente.papel == 'GESTOR')

    solicitacoes_pendentes = []
    membros_aprovados = []
    if eh_gestor:
        solicitacoes_pendentes = VinculoFamiliar.objects.filter(
            familiar=familiar_atual, status='PENDENTE'
        ).select_related('usuario')
        membros_aprovados = VinculoFamiliar.objects.filter(
            familiar=familiar_atual, status='APROVADO'
        ).select_related('usuario').order_by('-papel', 'usuario__first_name')

    hoje = date.today()
    mes = int(request.GET.get('mes', hoje.month))
    ano = int(request.GET.get('ano', hoje.year))

    if request.method == 'POST':
        form = TransacaoForm(request.POST, request.FILES, familiar=familiar_atual)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.familiar = familiar_atual
            transacao.criado_por = request.user
            transacao.save()
            messages.success(request, 'Lançamento registrado com sucesso!')
            return redirect(f'/?mes={mes}&ano={ano}')
    else:
        form = TransacaoForm(initial={'data': hoje}, familiar=familiar_atual)

    transacoes = Transacao.objects.para_familiar(familiar_atual).filter(
        data__year=ano, data__month=mes
    ).select_related('categoria', 'criado_por')

    categorias_qs = Categoria.objects.filter(
        models.Q(familiar__isnull=True) | models.Q(familiar=familiar_atual)
    ).order_by('nome')
    categorias_json = [
        {'id': c.id, 'nome': c.nome, 'tipo': c.tipo} for c in categorias_qs
    ]

    total_entradas = transacoes.filter(tipo='ENTRADA').aggregate(total=Sum('valor'))['total'] or 0
    total_saidas = transacoes.filter(tipo='SAIDA').aggregate(total=Sum('valor'))['total'] or 0
    saldo = total_entradas - total_saidas

    gastos_por_comprador = transacoes.filter(tipo='SAIDA').values('comprador').annotate(total=Sum('valor')).order_by('-total')

    # Dados para o Gráfico de Rosca de Gastos do Mês
    gastos_por_categoria_qs = transacoes.filter(tipo='SAIDA').values('categoria__nome').annotate(total=Sum('valor')).order_by('-total')
    grafico_labels = [item['categoria__nome'] or 'Sem Categoria' for item in gastos_por_categoria_qs]
    grafico_valores = [float(item['total']) for item in gastos_por_categoria_qs]

    context = {
        'familiar_atual': familiar_atual,
        'vinculos': vinculos,
        'eh_gestor': eh_gestor,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'membros_aprovados': membros_aprovados,
        'total_solicitacoes': len(solicitacoes_pendentes),
        'form': form,
        'transacoes': transacoes,
        'categorias_do_familiar': Categoria.objects.filter(familiar=familiar_atual).order_by('tipo', 'nome'),
        'categorias_json': categorias_json,
        'grafico_labels': grafico_labels,
        'grafico_valores': grafico_valores,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo': saldo,
        'mes_selecionado': mes,
        'ano_selecionado': ano,
        'gastos_por_comprador': gastos_por_comprador,
        'meses': [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
    }
    return render(request, 'financeiro/index.html', context)


@login_required
def editar_transacao(request, transacao_id):
    transacao = get_object_or_404(Transacao, id=transacao_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=transacao.familiar, status='APROVADO'
    ).first()

    if not vinculo:
        return HttpResponseForbidden("Acesso negado.")

    # Regra de Segurança: Gestor edita qualquer um; Membro só edita o próprio
    if vinculo.papel != 'GESTOR' and transacao.criado_por != request.user:
        return HttpResponseForbidden("Você só pode editar lançamentos criados por você.")

    if request.method == 'POST':
        form = TransacaoForm(request.POST, request.FILES, instance=transacao, familiar=transacao.familiar)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lançamento atualizado com sucesso!')
            return redirect(f'/?mes={transacao.data.month}&ano={transacao.data.year}')
    else:
        form = TransacaoForm(instance=transacao, familiar=transacao.familiar)

    categorias_qs = Categoria.objects.filter(
        models.Q(familiar__isnull=True) | models.Q(familiar=transacao.familiar)
    ).order_by('nome')
    categorias_json = [{'id': c.id, 'nome': c.nome, 'tipo': c.tipo} for c in categorias_qs]

    return render(request, 'financeiro/editar_transacao.html', {
        'form': form,
        'transacao': transacao,
        'categorias_json': categorias_json,
    })


@login_required
def excluir_transacao(request, transacao_id):
    transacao = get_object_or_404(Transacao, id=transacao_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=transacao.familiar, status='APROVADO'
    ).first()

    if not vinculo:
        return HttpResponseForbidden("Acesso negado.")

    if vinculo.papel == 'GESTOR' or transacao.criado_por == request.user:
        transacao.delete()
        messages.success(request, 'Lançamento excluído com sucesso.')
        return redirect('index')
    else:
        return HttpResponseForbidden("Você só pode excluir lançamentos criados por você.")


@login_required
def exportar_csv(request, familiar_id):
    familiar = get_object_or_404(Familiar, id=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, status='APROVADO'
    ).first()

    if not vinculo:
        return HttpResponseForbidden("Acesso negado.")

    hoje = date.today()
    mes = int(request.GET.get('mes', hoje.month))
    ano = int(request.GET.get('ano', hoje.year))

    transacoes = Transacao.objects.para_familiar(familiar).filter(
        data__year=ano, data__month=mes
    ).select_related('categoria', 'criado_por')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="extrato_{familiar.nome.lower().replace(" ", "_")}_{mes}_{ano}.csv"'
    response.write(u'\ufeff'.encode('utf8'))  # BOM UTF-8 para Excel abrir sem caracteres quebrados

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Data', 'Tipo', 'Descrição', 'Categoria', 'Valor (R$)', 'Comprador/Responsável', 'Forma Pagamento', 'Criado Por'])

    for t in transacoes:
        writer.writerow([
            t.data.strftime('%d/%m/%Y'),
            t.get_tipo_display(),
            t.descricao,
            t.categoria.nome if t.categoria else 'Geral',
            f"{t.valor:.2f}".replace('.', ','),
            t.comprador,
            t.get_forma_pagamento_display(),
            t.criado_por.username if t.criado_por else '-'
        ])

    return response


@login_required
def alterar_papel_membro(request, vinculo_id, papel):
    vinculo = get_object_or_404(VinculoFamiliar, id=vinculo_id)
    gestor_vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=vinculo.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not gestor_vinculo:
        return HttpResponseForbidden("Apenas o Gestor pode alterar papéis de membros.")

    if papel in ['GESTOR', 'MEMBRO']:
        vinculo.papel = papel
        vinculo.save()
        messages.success(request, f'Papel de {vinculo.usuario.first_name or vinculo.usuario.username} alterado para {papel}.')

    return redirect('index')


@login_required
def remover_membro(request, vinculo_id):
    vinculo = get_object_or_404(VinculoFamiliar, id=vinculo_id)
    gestor_vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=vinculo.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not gestor_vinculo:
        return HttpResponseForbidden("Apenas o Gestor pode remover membros.")

    if vinculo.usuario == request.user:
        messages.error(request, "Você não pode remover seu próprio acesso de gestor por aqui.")
        return redirect('index')

    nome_removido = vinculo.usuario.first_name or vinculo.usuario.username
    vinculo.delete()
    messages.success(request, f'Acesso de {nome_removido} revogado com sucesso.')
    return redirect('index')


@login_required
def responder_solicitacao(request, vinculo_id, acao):
    vinculo = get_object_or_404(VinculoFamiliar, id=vinculo_id)
    gestor_vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=vinculo.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not gestor_vinculo:
        return HttpResponseForbidden("Apenas o Gestor pode responder a solicitações.")

    if acao == 'aprovar':
        vinculo.status = 'APROVADO'
        vinculo.save()
        messages.success(request, f'Membro {vinculo.usuario.first_name or vinculo.usuario.username} aprovado!')
    elif acao == 'recusar':
        vinculo.status = 'RECUSADO'
        vinculo.save()
        messages.info(request, 'Solicitação recusada.')

    return redirect(request.META.get('HTTP_REFERER', 'index'))