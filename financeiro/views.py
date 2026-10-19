import csv
import json
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CadastroForm, FamiliarForm, EntrarFamiliaForm, TransacaoForm, EditarPerfilForm
from .models import (
    Categoria,
    Familiar,
    FechamentoCompetencia,
    LogAuditoriaTransacao,
    PerfilUsuario,
    Transacao,
    VinculoFamiliar,
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('meus_familiares')

    if request.method == 'POST':
        identificador = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not identificador or not password:
            messages.error(request, "Por favor, preencha o e-mail/utilizador e a senha.")
            return render(request, 'financeiro/login.html')

        usuario_obj = User.objects.filter(
            Q(email__iexact=identificador) | Q(username__iexact=identificador)
        ).first()

        if usuario_obj:
            user = authenticate(request, username=usuario_obj.username, password=password)
            if user is not None:
                login(request, user)
                request.session.pop('familiar_ativo_id', None)
                return redirect('meus_familiares')

        messages.error(request, "E-mail/utilizador ou senha incorretos.")

    return render(request, 'financeiro/login.html')


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect('meus_familiares')

    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Conta criada com sucesso!")
            return redirect('onboarding')
    else:
        form = CadastroForm()

    return render(request, 'financeiro/cadastro.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def perfil_view(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
    form_perfil = EditarPerfilForm(instance=request.user)
    form_senha = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'atualizar_perfil' in request.POST:
            form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=request.user)
            if form_perfil.is_valid():
                form_perfil.save()
                messages.success(request, "Dados do perfil atualizados com sucesso!")
                return redirect('perfil')

        elif 'alterar_senha' in request.POST:
            form_senha = PasswordChangeForm(user=request.user, data=request.POST)
            if form_senha.is_valid():
                user = form_senha.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Palavra-passe alterada com sucesso!")
                return redirect('perfil')

    return render(request, 'financeiro/perfil.html', {
        'perfil': perfil,
        'form_perfil': form_perfil,
        'form_senha': form_senha,
    })


@login_required
def remover_foto_perfil(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.foto:
        request.user.perfil.foto.delete(save=True)
        messages.success(request, "Foto de perfil removida com sucesso!")
    return redirect('perfil')


@login_required
def onboarding_view(request):
    vinculos = VinculoFamiliar.objects.filter(usuario=request.user)
    if vinculos.filter(status='APROVADO').exists():
        return redirect('meus_familiares')

    if vinculos.filter(status='PENDENTE').exists():
        return render(request, 'financeiro/pendente.html')

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
                messages.success(request, f"Familiar '{familiar.nome}' criado com sucesso!")
                return redirect('index')

        elif 'entrar_familia' in request.POST:
            form_entrar = EntrarFamiliaForm(request.POST)
            if form_entrar.is_valid():
                codigo = form_entrar.cleaned_data['codigo_convite'].strip().upper()
                familiar = Familiar.objects.filter(codigo_convite=codigo, ativo=True).first()

                if not familiar:
                    messages.error(request, "Código de convite inválido ou familiar inativo.")
                else:
                    ja_vinculado = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar).first()
                    if ja_vinculado:
                        if ja_vinculado.status == 'APROVADO':
                            request.session['familiar_ativo_id'] = familiar.id
                            return redirect('index')
                        else:
                            messages.info(request, "Já possui uma solicitação pendente para este familiar.")
                            return render(request, 'financeiro/pendente.html')
                    else:
                        VinculoFamiliar.objects.create(
                            usuario=request.user,
                            familiar=familiar,
                            papel='MEMBRO',
                            status='PENDENTE'
                        )
                        messages.success(request, "Solicitação enviada! Aguarde a aprovação do Gestor.")
                        return render(request, 'financeiro/pendente.html')

    return render(request, 'financeiro/onboarding.html', {
        'form_familiar': form_familiar,
        'form_entrar': form_entrar,
    })


@login_required
def meus_familiares_view(request):
    vinculos = VinculoFamiliar.objects.filter(usuario=request.user, status='APROVADO').select_related('familiar')

    if not vinculos.exists():
        return redirect('onboarding')

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
                messages.success(request, f"Familiar '{familiar.nome}' cadastrado com sucesso!")
                return redirect('index')

        elif 'entrar_familia' in request.POST:
            form_entrar = EntrarFamiliaForm(request.POST)
            if form_entrar.is_valid():
                codigo = form_entrar.cleaned_data['codigo_convite'].strip().upper()
                familiar = Familiar.objects.filter(codigo_convite=codigo, ativo=True).first()

                if not familiar:
                    messages.error(request, "Código de convite inválido ou familiar arquivado.")
                else:
                    ja_vinculado = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar).first()
                    if ja_vinculado:
                        if ja_vinculado.status == 'APROVADO':
                            request.session['familiar_ativo_id'] = familiar.id
                            return redirect('index')
                        messages.info(request, "Solicitação pendente para este familiar.")
                    else:
                        VinculoFamiliar.objects.create(
                            usuario=request.user,
                            familiar=familiar,
                            papel='MEMBRO',
                            status='PENDENTE'
                        )
                        messages.success(request, "Solicitação enviada ao Gestor com sucesso!")
                        return redirect('meus_familiares')

    solicitacoes_pendentes = VinculoFamiliar.objects.filter(
        familiar__vinculos__usuario=request.user,
        familiar__vinculos__papel='GESTOR',
        familiar__vinculos__status='APROVADO',
        status='PENDENTE'
    ).select_related('usuario', 'familiar').distinct()

    total_solicitacoes_pendentes = solicitacoes_pendentes.count()

    return render(request, 'financeiro/meus_familiares.html', {
        'vinculos': vinculos,
        'form_familiar': form_familiar,
        'form_entrar': form_entrar,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'total_solicitacoes_pendentes': total_solicitacoes_pendentes,
    })


@login_required
def selecionar_familiar(request, familiar_id):
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar_id=familiar_id, status='APROVADO').first()
    if vinculo:
        request.session['familiar_ativo_id'] = familiar_id
    else:
        messages.error(request, "Não possui acesso a este familiar.")
    return redirect('index')


@login_required
def index(request):
    vinculos = VinculoFamiliar.objects.filter(usuario=request.user, status='APROVADO').select_related('familiar')
    if not vinculos.exists():
        return redirect('onboarding')

    familiar_id = request.session.get('familiar_ativo_id')
    vinculo_atual = None

    if familiar_id:
        vinculo_atual = vinculos.filter(familiar_id=familiar_id).first()

    if not vinculo_atual:
        vinculo_atual = vinculos.first()
        request.session['familiar_ativo_id'] = vinculo_atual.familiar.id

    familiar_atual = vinculo_atual.familiar
    eh_gestor = (vinculo_atual.papel == 'GESTOR')

    hoje = date.today()
    try:
        mes_selecionado = int(request.GET.get('mes', hoje.month))
        ano_selecionado = int(request.GET.get('ano', hoje.year))
    except (ValueError, TypeError):
        mes_selecionado = hoje.month
        ano_selecionado = hoje.year

    fechamento = FechamentoCompetencia.objects.filter(
        familiar=familiar_atual,
        ano=ano_selecionado,
        mes=mes_selecionado
    ).first()
    mes_travado = bool(fechamento and fechamento.fechado)

    if request.method == 'POST':
        if not familiar_atual.ativo:
            messages.error(request, "Este familiar está arquivado em modo de leitura.")
            return redirect('index')

        if mes_travado:
            messages.error(request, "Esta competência está fechada para novas movimentações.")
            return redirect('index')

        form = TransacaoForm(request.POST, request.FILES, familiar=familiar_atual)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.familiar = familiar_atual
            transacao.criado_por = request.user
            transacao.save()

            LogAuditoriaTransacao.objects.create(
                familiar=familiar_atual,
                transacao_id_ref=transacao.id,
                usuario=request.user,
                acao='CRIACAO',
                detalhes=f"Lançamento '{transacao.descricao}' de R$ {transacao.valor} criado."
            )

            messages.success(request, "Lançamento adicionado com sucesso!")
            return redirect(f'/?mes={mes_selecionado}&ano={ano_selecionado}')
    else:
        form = TransacaoForm(familiar=familiar_atual)

    transacoes_qs = Transacao.objects.filter(
        familiar=familiar_atual,
        data__year=ano_selecionado,
        data__month=mes_selecionado
    ).select_related('categoria', 'criado_por')

    total_registros_mes = transacoes_qs.count()

    busca_texto = request.GET.get('q', '').strip()
    filtro_tipo = request.GET.get('tipo', '').strip()
    filtro_categoria = request.GET.get('categoria', '').strip()
    filtro_comprador = request.GET.get('comprador', '').strip()
    filtro_forma_pgto = request.GET.get('forma_pagamento', '').strip()

    filtros_ativos = bool(busca_texto or filtro_tipo or filtro_categoria or filtro_comprador or filtro_forma_pgto)

    if busca_texto:
        transacoes_qs = transacoes_qs.filter(
            Q(descricao__icontains=busca_texto) | Q(observacoes__icontains=busca_texto)
        )
    if filtro_tipo:
        transacoes_qs = transacoes_qs.filter(tipo=filtro_tipo)
    if filtro_categoria:
        transacoes_qs = transacoes_qs.filter(categoria_id=filtro_categoria)
    if filtro_comprador:
        transacoes_qs = transacoes_qs.filter(comprador__iexact=filtro_comprador)
    if filtro_forma_pgto:
        transacoes_qs = transacoes_qs.filter(forma_pagamento=filtro_forma_pgto)

    transacoes = transacoes_qs.order_by('-data', '-criado_em')

    total_entradas = transacoes.filter(tipo='ENTRADA').aggregate(s=Sum('valor'))['s'] or Decimal('0.00')
    total_saidas = transacoes.filter(tipo='SAIDA').aggregate(s=Sum('valor'))['s'] or Decimal('0.00')
    saldo = total_entradas - total_saidas

    despesas_por_cat = (
        transacoes.filter(tipo='SAIDA')
        .values('categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )
    grafico_labels = [item['categoria__nome'] or 'Sem Categoria' for item in despesas_por_cat]
    grafico_valores = [float(item['total']) for item in despesas_por_cat]

    gastos_por_comprador = (
        transacoes.filter(tipo='SAIDA')
        .values('comprador')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )

    todas_categorias = Categoria.objects.filter(familiar=familiar_atual).order_by('nome')
    categorias_json = [{'id': c.id, 'nome': c.nome, 'tipo': c.tipo} for c in todas_categorias]
    compradores_disponiveis = (
        Transacao.objects.filter(familiar=familiar_atual)
        .values_list('comprador', flat=True)
        .distinct()
        .order_by('comprador')
    )
    formas_pagamento_disponiveis = Transacao.FORMAS_PAGAMENTO

    membros_aprovados = VinculoFamiliar.objects.filter(
        familiar=familiar_atual,
        status='APROVADO'
    ).select_related('usuario')

    solicitacoes_pendentes = []
    total_solicitacoes = 0
    logs_auditoria = []

    if eh_gestor:
        solicitacoes_pendentes = VinculoFamiliar.objects.filter(
            familiar=familiar_atual,
            status='PENDENTE'
        ).select_related('usuario')
        total_solicitacoes = solicitacoes_pendentes.count()
        logs_auditoria = LogAuditoriaTransacao.objects.filter(
            familiar=familiar_atual
        ).select_related('usuario').order_by('-data_hora')[:30]

    meses = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]

    contexto = {
        'familiar_atual': familiar_atual,
        'vinculos': vinculos,
        'eh_gestor': eh_gestor,
        'form': form,
        'transacoes': transacoes,
        'total_registros': transacoes.count(),
        'total_registros_mes': total_registros_mes,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo': saldo,
        'mes_selecionado': mes_selecionado,
        'ano_selecionado': ano_selecionado,
        'mes_travado': mes_travado,
        'meses': meses,
        'filtros_ativos': filtros_ativos,
        'busca_texto': busca_texto,
        'filtro_tipo': filtro_tipo,
        'filtro_categoria': filtro_categoria,
        'filtro_comprador': filtro_comprador,
        'filtro_forma_pgto': filtro_forma_pgto,
        'todas_categorias': todas_categorias,
        'categorias_do_familiar': todas_categorias,
        'categorias_json': categorias_json,
        'compradores_disponiveis': compradores_disponiveis,
        'formas_pagamento_disponiveis': formas_pagamento_disponiveis,
        'grafico_labels': grafico_labels,
        'grafico_valores': grafico_valores,
        'gastos_por_comprador': gastos_por_comprador,
        'membros_aprovados': membros_aprovados,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'total_solicitacoes': total_solicitacoes,
        'logs_auditoria': logs_auditoria,
    }
    return render(request, 'financeiro/index.html', contexto)


@login_required
def alternar_fechamento_mes(request, familiar_id, ano, mes):
    familiar = get_object_or_404(Familiar, id=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem fechar ou reabrir competências.")
        return redirect('index')

    fechamento, created = FechamentoCompetencia.objects.get_or_create(
        familiar=familiar,
        ano=ano,
        mes=mes,
        defaults={'fechado': True, 'fechado_por': request.user}
    )

    if not created:
        fechamento.fechado = not fechamento.fechado
        fechamento.fechado_por = request.user
        fechamento.save()

    status_str = "fechada" if fechamento.fechado else "reaberta"

    LogAuditoriaTransacao.objects.create(
        familiar=familiar,
        transacao_id_ref=0,
        usuario=request.user,
        acao='EDICAO',
        detalhes=f"Competência {mes:02d}/{ano} {status_str} por {request.user.username}."
    )

    messages.success(request, f"Competência {mes:02d}/{ano} {status_str} com sucesso.")
    return redirect(f'/?mes={mes}&ano={ano}')


@login_required
def editar_transacao(request, transacao_id):
    transacao = get_object_or_404(Transacao, id=transacao_id)
    familiar = transacao.familiar

    if not familiar.ativo:
        messages.error(request, "Familiar arquivado em modo de leitura.")
        return redirect('index')

    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, status='APROVADO'
    ).first()
    if not vinculo:
        messages.error(request, "Acesso não permitido.")
        return redirect('meus_familiares')

    eh_gestor = (vinculo.papel == 'GESTOR')
    pode_editar = eh_gestor or (transacao.criado_por == request.user)

    if not pode_editar:
        messages.error(request, "Permissão negada para editar este lançamento.")
        return redirect('index')

    fechamento = FechamentoCompetencia.objects.filter(
        familiar=familiar, ano=transacao.data.year, mes=transacao.data.month, fechado=True
    ).exists()
    if fechamento:
        messages.error(request, "A competência referente a este lançamento está fechada.")
        return redirect('index')

    if request.method == 'POST':
        form = TransacaoForm(request.POST, request.FILES, instance=transacao, familiar=familiar)
        if form.is_valid():
            form.save()
            LogAuditoriaTransacao.objects.create(
                familiar=familiar,
                transacao_id_ref=transacao.id,
                usuario=request.user,
                acao='EDICAO',
                detalhes=f"Lançamento '{transacao.descricao}' atualizado."
            )
            messages.success(request, "Lançamento atualizado com sucesso!")
            return redirect(f'/?mes={transacao.data.month}&ano={transacao.data.year}')
    else:
        form = TransacaoForm(instance=transacao, familiar=familiar)

    return render(request, 'financeiro/editar_transacao.html', {
        'form': form,
        'transacao': transacao,
        'familiar': familiar,
    })


@login_required
def excluir_transacao(request, transacao_id):
    transacao = get_object_or_404(Transacao, id=transacao_id)
    familiar = transacao.familiar

    if not familiar.ativo:
        messages.error(request, "Familiar arquivado em modo de leitura.")
        return redirect('index')

    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, status='APROVADO'
    ).first()
    if not vinculo:
        messages.error(request, "Acesso não permitido.")
        return redirect('meus_familiares')

    eh_gestor = (vinculo.papel == 'GESTOR')
    pode_excluir = eh_gestor or (transacao.criado_por == request.user)

    if not pode_excluir:
        messages.error(request, "Permissão negada para excluir este lançamento.")
        return redirect('index')

    fechamento = FechamentoCompetencia.objects.filter(
        familiar=familiar, ano=transacao.data.year, mes=transacao.data.month, fechado=True
    ).exists()
    if fechamento:
        messages.error(request, "A competência referente a este lançamento está fechada.")
        return redirect('index')

    descricao = transacao.descricao
    valor = transacao.valor
    mes = transacao.data.month
    ano = transacao.data.year

    LogAuditoriaTransacao.objects.create(
        familiar=familiar,
        transacao_id_ref=transacao.id,
        usuario=request.user,
        acao='EXCLUSAO',
        detalhes=f"Lançamento '{descricao}' de R$ {valor} excluído."
    )
    transacao.delete()

    messages.success(request, f"Lançamento '{descricao}' removido com sucesso!")
    return redirect(f'/?mes={mes}&ano={ano}')


@login_required
def criar_categoria(request, familiar_id):
    familiar = get_object_or_404(Familiar, id=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not vinculo or not familiar.ativo:
        messages.error(request, "Ação não permitida.")
        return redirect('index')

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', 'SAIDA').strip()
        if nome:
            Categoria.objects.get_or_create(familiar=familiar, nome=nome, defaults={'tipo': tipo})
            messages.success(request, f"Categoria '{nome}' criada com sucesso!")

    return redirect('index')


@login_required
def excluir_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=categoria.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not vinculo or not categoria.familiar.ativo:
        messages.error(request, "Ação não permitida.")
        return redirect('index')

    nome = categoria.nome
    categoria.delete()
    messages.success(request, f"Categoria '{nome}' removida!")
    return redirect('index')


@login_required
def responder_solicitacao(request, vinculo_id, acao):
    vinculo = get_object_or_404(VinculoFamiliar, id=vinculo_id, status='PENDENTE')
    gestor_vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=vinculo.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not gestor_vinculo:
        messages.error(request, "Apenas gestores podem aprovar ou recusar solicitações.")
        return redirect('index')

    if acao == 'aprovar':
        vinculo.status = 'APROVADO'
        vinculo.save()
        messages.success(request, f"Acesso de {vinculo.usuario.username} aprovado!")
    elif acao == 'recusar':
        vinculo.delete()
        messages.info(request, "Solicitação recusada.")

    referer = request.META.get('HTTP_REFERER', '')
    if 'meus-familiares' in referer:
        return redirect('meus_familiares')

    return redirect('index')


@login_required
def alterar_papel_membro(request, vinculo_id, papel):
    vinculo = get_object_or_404(VinculoFamiliar, id=vinculo_id, status='APROVADO')
    gestor_vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=vinculo.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not gestor_vinculo or not vinculo.familiar.ativo:
        messages.error(request, "Ação não permitida.")
        return redirect('index')

    if papel in ['GESTOR', 'MEMBRO']:
        vinculo.papel = papel
        vinculo.save()
        messages.success(request, f"Papel de {vinculo.usuario.username} alterado para {papel}.")

    return redirect('index')


@login_required
def remover_membro(request, vinculo_id):
    vinculo = get_object_or_404(VinculoFamiliar, id=vinculo_id)
    gestor_vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=vinculo.familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not gestor_vinculo or vinculo.usuario == request.user:
        messages.error(request, "Ação não permitida.")
        return redirect('index')

    nome_usuario = vinculo.usuario.username
    vinculo.delete()
    messages.success(request, f"Acesso de {nome_usuario} revogado com sucesso.")
    return redirect('index')


@login_required
def alternar_arquivamento_familiar(request, familiar_id):
    familiar = get_object_or_404(Familiar, id=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem arquivar ou reativar familiares.")
        return redirect('meus_familiares')

    familiar.ativo = not familiar.ativo
    familiar.save()
    status_str = "reativado" if familiar.ativo else "arquivado em modo de leitura"
    messages.success(request, f"Familiar '{familiar.nome}' {status_str}.")

    referer = request.META.get('HTTP_REFERER', '')
    if 'meus-familiares' in referer:
        return redirect('meus_familiares')
    return redirect('index')


@login_required
def sair_da_familia(request, familiar_id):
    vinculo = get_object_or_404(VinculoFamiliar, usuario=request.user, familiar_id=familiar_id)
    familiar_nome = vinculo.familiar.nome
    vinculo.delete()

    if request.session.get('familiar_ativo_id') == familiar_id:
        request.session.pop('familiar_ativo_id', None)

    messages.success(request, f"Saiu do grupo familiar '{familiar_nome}'.")
    return redirect('meus_familiares')


@login_required
def excluir_familiar_definitivo(request, familiar_id):
    familiar = get_object_or_404(Familiar, id=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, papel='GESTOR', status='APROVADO'
    ).first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem excluir permanentemente um familiar.")
        return redirect('meus_familiares')

    nome = familiar.nome
    familiar.delete()

    if request.session.get('familiar_ativo_id') == familiar_id:
        request.session.pop('familiar_ativo_id', None)

    messages.success(request, f"Familiar '{nome}' e todos os seus lançamentos foram excluídos definitivamente.")
    return redirect('meus_familiares')


@login_required
def exportar_csv(request, familiar_id):
    familiar = get_object_or_404(Familiar, id=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(
        usuario=request.user, familiar=familiar, status='APROVADO'
    ).first()

    if not vinculo:
        messages.error(request, "Acesso não permitido.")
        return redirect('meus_familiares')

    hoje = date.today()
    try:
        mes = int(request.GET.get('mes', hoje.month))
        ano = int(request.GET.get('ano', hoje.year))
    except (ValueError, TypeError):
        mes = hoje.month
        ano = hoje.year

    transacoes = Transacao.objects.filter(
        familiar=familiar, data__year=ano, data__month=mes
    ).select_related('categoria', 'criado_por')

    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    comprador = request.GET.get('comprador', '').strip()
    forma_pgto = request.GET.get('forma_pagamento', '').strip()

    if q:
        transacoes = transacoes.filter(Q(descricao__icontains=q) | Q(observacoes__icontains=q))
    if tipo:
        transacoes = transacoes.filter(tipo=tipo)
    if categoria:
        transacoes = transacoes.filter(categoria_id=categoria)
    if comprador:
        transacoes = transacoes.filter(comprador__iexact=comprador)
    if forma_pgto:
        transacoes = transacoes.filter(forma_pagamento=forma_pgto)

    transacoes = transacoes.order_by('data')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="extrato_{familiar.nome}_{mes:02d}_{ano}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Data', 'Tipo', 'Descrição', 'Categoria', 'Comprador', 'Forma Pagamento', 'Valor (R$)', 'Observações'])

    for t in transacoes:
        writer.writerow([
            t.data.strftime('%d/%m/%Y'),
            t.get_tipo_display(),
            t.descricao,
            t.categoria.nome if t.categoria else 'Geral',
            t.comprador,
            t.get_forma_pagamento_display(),
            f"{t.valor:.2f}".replace('.', ','),
            t.observacoes or '',
        ])

    return response