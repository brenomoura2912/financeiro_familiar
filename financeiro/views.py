import csv
import io
import json
import random
import string
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.html import strip_tags

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import (
    CadastroForm,
    EditarPerfilForm,
    EntrarFamiliaForm,
    FamiliarForm,
    TransacaoForm,
)
from .models import (
    Categoria,
    CodigoVerificacaoEmail,
    Familiar,
    FechamentoMes,
    LogAuditoria,
    PerfilUsuario,
    Transacao,
    VinculoFamiliar,
)


def enviar_email_codigo_verificacao(usuario, email_destino, finalidade):
    codigo_obj = CodigoVerificacaoEmail.gerar_codigo(usuario, email_destino, finalidade)
    assunto = "Código de verificação - Gestão Financeira Familiar"
    if finalidade == 'ALTERACAO_EMAIL':
        assunto = "Confirmação de alteração de e-mail - Gestão Financeira Familiar"

    contexto = {
        'usuario': usuario,
        'codigo': codigo_obj.codigo,
        'finalidade': finalidade,
    }
    html_mensagem = render_to_string('financeiro/emails/email_codigo.html', contexto)
    mensagem_plana = strip_tags(html_mensagem)

    send_mail(
        subject=assunto,
        message=mensagem_plana,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email_destino],
        html_message=html_mensagem,
        fail_silently=False,
    )
    return codigo_obj


def login_view(request):
    if request.user.is_authenticated:
        return redirect('meus_familiares')

    if request.method == 'POST':
        identificador = (
            request.POST.get('identificador') or 
            request.POST.get('username') or 
            request.POST.get('email') or 
            ''
        ).strip()

        senha = request.POST.get('senha') or request.POST.get('password') or ''

        usuario_obj = User.objects.filter(
            Q(email__iexact=identificador) | Q(username__iexact=identificador),
            is_active=True
        ).first()

        if usuario_obj:
            user = authenticate(request, username=usuario_obj.username, password=senha)
            if user is not None:
                login(request, user)
                return redirect('meus_familiares')

        usuario_inativo = User.objects.filter(
            Q(email__iexact=identificador) | Q(username__iexact=identificador),
            is_active=False
        ).first()

        if usuario_inativo and usuario_inativo.check_password(senha):
            request.session['usuario_verificacao_id'] = usuario_inativo.id
            enviar_email_codigo_verificacao(usuario_inativo, usuario_inativo.email, 'CADASTRO')
            messages.info(request, "A sua conta ainda não foi ativada. Enviámos um novo código para o seu e-mail.")
            return redirect('verificar_email')

        messages.error(request, "Nome de utilizador/e-mail ou palavra-passe incorretos.")

    return render(request, 'financeiro/login.html')


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect('meus_familiares')

    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    PerfilUsuario.objects.get_or_create(usuario=user)
                    enviar_email_codigo_verificacao(user, user.email, 'CADASTRO')

                request.session['usuario_verificacao_id'] = user.id
                messages.success(request, f"Código de ativação enviado para {user.email}!")
                return redirect('verificar_email')
            except Exception as e:
                messages.error(request, f"Falha no registo: {str(e)}")
        else:
            for campo, erros in form.errors.items():
                for erro in erros:
                    messages.error(request, erro)
    else:
        form = CadastroForm()

    return render(request, 'financeiro/cadastro.html', {'form': form})


def verificar_email_view(request):
    usuario_id = request.session.get('usuario_verificacao_id')
    if not usuario_id:
        messages.error(request, "Sessão de verificação expirada. Inicie sessão novamente.")
        return redirect('login')

    usuario = get_object_or_404(User, pk=usuario_id)

    if request.method == 'POST':
        codigo_digitado = request.POST.get('codigo', '').strip()
        codigo_obj = CodigoVerificacaoEmail.objects.filter(
            usuario=usuario,
            codigo=codigo_digitado,
            finalidade='CADASTRO',
            utilizado=False
        ).order_by('-criado_em').first()

        if codigo_obj and codigo_obj.esta_valido():
            codigo_obj.utilizado = True
            codigo_obj.save()

            usuario.is_active = True
            usuario.save()

            del request.session['usuario_verificacao_id']
            login(request, usuario)
            messages.success(request, "Conta ativada com sucesso!")
            return redirect('meus_familiares')
        else:
            messages.error(request, "Código incorreto ou expirado. Tente novamente.")

    return render(request, 'financeiro/verificar_email.html', {'email': usuario.email})


def reenviar_codigo_email_view(request):
    usuario_id = request.session.get('usuario_verificacao_id')
    if not usuario_id:
        messages.error(request, "Sessão expirada. Inicie o registo novamente.")
        return redirect('login')

    usuario = get_object_or_404(User, pk=usuario_id)
    try:
        enviar_email_codigo_verificacao(usuario, usuario.email, 'CADASTRO')
        messages.success(request, f"Novo código enviado para {usuario.email}!")
    except Exception as e:
        messages.error(request, f"Erro ao reenviar o código: {str(e)}")

    return redirect('verificar_email')


def logout_view(request):
    logout(request)
    messages.success(request, "Sessão encerrada com sucesso.")
    return redirect('login')


def gerar_codigo_convite():
    caracteres = string.ascii_uppercase + string.digits
    while True:
        codigo = ''.join(random.choices(caracteres, k=6))
        if not Familiar.objects.filter(codigo_convite=codigo).exists():
            return codigo


@login_required
def meus_familiares_view(request):
    if request.method == 'POST':
        acao = request.POST.get('acao')

        # 1. Criar novo familiar (Torna-se Gestor já APROVADO)
        if acao == 'criar_familiar' or 'criar_familiar' in request.POST:
            nome = request.POST.get('nome', '').strip()
            if not nome:
                messages.error(request, "Por favor, informe o nome do familiar.")
                return redirect('meus_familiares')

            codigo = gerar_codigo_convite()
            familiar = Familiar.objects.create(
                nome=nome,
                codigo_convite=codigo
            )

            VinculoFamiliar.objects.create(
                familiar=familiar,
                usuario=request.user,
                papel='GESTOR',
                status='APROVADO'
            )

            messages.success(request, f"Familiar '{nome}' registado com sucesso! Você é o gestor.")
            return redirect('meus_familiares')

        # 2. Solicitar acesso com código de convite
        elif acao == 'solicitar_acesso' or 'solicitar_acesso' in request.POST:
            codigo = request.POST.get('codigo_convite', '').strip().upper()
            try:
                familiar = Familiar.objects.get(codigo_convite=codigo)
            except Familiar.DoesNotExist:
                messages.error(request, "Código de convite inválido ou não encontrado.")
                return redirect('meus_familiares')

            vinculo_existente = VinculoFamiliar.objects.filter(familiar=familiar, usuario=request.user).first()
            if vinculo_existente:
                if vinculo_existente.status == 'PENDENTE':
                    messages.info(request, "Já possui uma solicitação pendente para este familiar.")
                else:
                    messages.warning(request, "Você já possui acesso a este familiar.")
                return redirect('meus_familiares')

            VinculoFamiliar.objects.create(
                familiar=familiar,
                usuario=request.user,
                papel='MEMBRO',
                status='PENDENTE'
            )
            messages.success(request, f"Solicitação enviada ao gestor de '{familiar.nome}'. Aguarde a aprovação.")
            return redirect('meus_familiares')

        # 3. Ações de Aprovar ou Recusar Membros
        elif acao == 'aprovar_membro':
            solicitacao_id = request.POST.get('solicitacao_id')
            solicitacao = get_object_or_404(VinculoFamiliar, pk=solicitacao_id)
            eh_gestor = VinculoFamiliar.objects.filter(familiar=solicitacao.familiar, usuario=request.user, papel='GESTOR').exists()
            if eh_gestor:
                solicitacao.status = 'APROVADO'
                solicitacao.save()
                messages.success(request, f"Acesso de @{solicitacao.usuario.username} aprovado!")
            else:
                messages.error(request, "Não possui permissão para aprovar membros.")
            return redirect('meus_familiares')

        elif acao == 'recusar_membro':
            solicitacao_id = request.POST.get('solicitacao_id')
            solicitacao = get_object_or_404(VinculoFamiliar, pk=solicitacao_id)
            eh_gestor = VinculoFamiliar.objects.filter(familiar=solicitacao.familiar, usuario=request.user, papel='GESTOR').exists()
            if eh_gestor:
                solicitacao.delete()
                messages.info(request, f"Solicitação de @{solicitacao.usuario.username} recusada.")
            else:
                messages.error(request, "Não possui permissão para recusar membros.")
            return redirect('meus_familiares')

    # Apenas vínculos onde o usuário é GESTOR ou MEMBRO APROVADO aparecem na lista de cartões
    familiares = VinculoFamiliar.objects.filter(
        usuario=request.user, 
        status='APROVADO'
    ).select_related('familiar')

    fam_gerenciados_ids = VinculoFamiliar.objects.filter(
        usuario=request.user, 
        papel='GESTOR'
    ).values_list('familiar_id', flat=True)

    # Solicitações pendentes aguardando aprovação deste gestor
    solicitacoes_pendentes = VinculoFamiliar.objects.filter(
        familiar_id__in=fam_gerenciados_ids,
        status='PENDENTE'
    ).select_related('familiar', 'usuario')

    contexto = {
        'familiares': familiares,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'total_pendentes': solicitacoes_pendentes.count(),
    }
    return render(request, 'financeiro/meus_familiares.html', contexto)


@login_required
def dashboard_view(request, familiar_id):
    familiar = get_object_or_404(Familiar, pk=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO').first()
    

    if not vinculo:
        messages.error(request, "Não possui permissão para aceder a este familiar.")
        return redirect('meus_familiares')

    hoje = date.today()
    try:
        mes_filtro = int(request.GET.get('mes', hoje.month))
    except (ValueError, TypeError):
        mes_filtro = hoje.month

    try:
        ano_filtro = int(request.GET.get('ano', hoje.year))
    except (ValueError, TypeError):
        ano_filtro = hoje.year

    fechamento = FechamentoMes.objects.filter(familiar=familiar, mes=mes_filtro, ano=ano_filtro).first()
    esta_fechado = fechamento.fechado if fechamento else False

    transacoes = Transacao.objects.filter(
        familiar=familiar,
        ativo=True,
        data__year=ano_filtro,
        data__month=mes_filtro
    ).select_related('categoria', 'usuario').order_by('-data', '-criado_em')

    busca_texto = request.GET.get('q', '').strip()
    filtro_tipo = request.GET.get('tipo', '').strip()
    filtro_categoria = request.GET.get('categoria', '').strip()
    filtro_comprador = request.GET.get('comprador', '').strip()
    filtro_forma_pgto = request.GET.get('forma_pagamento', '').strip()

    filtros_ativos = any([busca_texto, filtro_tipo, filtro_categoria, filtro_comprador, filtro_forma_pgto])

    if busca_texto:
        transacoes = transacoes.filter(Q(descricao__icontains=busca_texto) | Q(observacoes__icontains=busca_texto))
    if filtro_tipo:
        transacoes = transacoes.filter(tipo=filtro_tipo)
    if filtro_categoria:
        transacoes = transacoes.filter(categoria_id=filtro_categoria)
    if filtro_comprador:
        transacoes = transacoes.filter(comprador__iexact=filtro_comprador)
    if filtro_forma_pgto:
        transacoes = transacoes.filter(forma_pagamento=filtro_forma_pgto)

    res_receitas = transacoes.filter(tipo__in=['RECEITA', 'ENTRADA']).aggregate(s=Sum('valor'))['s']
    total_receitas = res_receitas if res_receitas is not None else Decimal('0.00')

    res_despesas = transacoes.filter(tipo__in=['DESPESA', 'SAIDA']).aggregate(s=Sum('valor'))['s']
    total_despesas = res_despesas if res_despesas is not None else Decimal('0.00')

    saldo = total_receitas - total_despesas

    despesas_por_cat = (
        transacoes.filter(tipo__in=['DESPESA', 'SAIDA'])
        .values('categoria__nome', 'categoria__cor')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )

    chart_labels = []
    chart_values = []
    chart_colors = []
    for item in despesas_por_cat:
        chart_labels.append(item['categoria__nome'] or 'Sem Categoria')
        chart_values.append(float(item['total']))
        chart_colors.append(item['categoria__cor'] or '#6366f1')

    compradores_disponiveis = list(
        Transacao.objects.filter(familiar=familiar, ativo=True)
        .exclude(comprador__isnull=True)
        .exclude(comprador__exact='')
        .values_list('comprador', flat=True)
        .distinct()
    )

    formas_pagamento_disponiveis = getattr(Transacao, 'FORMA_PAGAMENTO_CHOICES', [
        ('DINHEIRO', 'Dinheiro'),
        ('PIX', 'PIX'),
        ('DEBITO', 'Cartão de Débito'),
        ('CREDITO', 'Cartão de Crédito'),
    ])

    lista_meses = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]

    membros = VinculoFamiliar.objects.filter(familiar=familiar).select_related('usuario')
    categorias = Categoria.objects.filter(familiar=familiar)
    # Mapeamento seguro das categorias
    categorias_dict = {str(cat.id): cat.tipo for cat in categorias}

    transacoes_excluidas = []
    if vinculo.papel == 'GESTOR':
        transacoes_excluidas = Transacao.objects.filter(
            familiar=familiar,
            ativo=False
        ).select_related('categoria', 'usuario').order_by('-data')

    form_transacao = TransacaoForm(familiar=familiar)

    if request.method == 'POST':
        if esta_fechado or not familiar.ativo:
            messages.error(request, "Este período ou familiar encontra-se fechado/arquivado.")
            return redirect(f"{request.path}?mes={mes_filtro}&ano={ano_filtro}")

        form_transacao = TransacaoForm(request.POST, request.FILES, familiar=familiar)
        if form_transacao.is_valid():
            transacao = form_transacao.save(commit=False)
            transacao.familiar = familiar
            transacao.usuario = request.user
            transacao.ativo = True
            transacao.save()

            LogAuditoria.objects.create(
                transacao=transacao,
                usuario=request.user,
                acao='CRIACAO',
                detalhes=f"Lançamento de {transacao.tipo}: R$ {transacao.valor}"
            )

            messages.success(request, "Lançamento registado com sucesso!")
            return redirect(f"{request.path}?mes={mes_filtro}&ano={ano_filtro}")

    logs_auditoria = LogAuditoria.objects.filter(transacao__familiar=familiar).select_related('usuario').order_by('-data_hora')[:50]

    contexto = {
        'familiar': familiar,
        'familiar_atual': familiar,
        'vinculo': vinculo,
        'eh_gestor': (vinculo.papel == 'GESTOR'),
        'transacoes': transacoes,
        'transacoes_excluidas': transacoes_excluidas,
        'form_transacao': form_transacao,
        'total_receitas': total_receitas,
        'total_despesas': total_despesas,
        'saldo': saldo,
        'mes_selecionado': mes_filtro,
        'ano_selecionado': ano_filtro,
        'mes_travado': esta_fechado,
        'membros': membros,
        'membros_aprovados': membros.filter(status='APROVADO'),
        'categorias': categorias,
        'lista_meses': lista_meses,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_values_json': json.dumps(chart_values),
        'chart_colors_json': json.dumps(chart_colors),
        'filtros_ativos': filtros_ativos,
        'busca_texto': busca_texto,
        'filtro_tipo': filtro_tipo,
        'filtro_categoria': filtro_categoria,
        'filtro_comprador': filtro_comprador,
        'filtro_forma_pgto': filtro_forma_pgto,
        'compradores_disponiveis': compradores_disponiveis,
        'formas_pagamento_disponiveis': formas_pagamento_disponiveis,
        'logs_auditoria': logs_auditoria,
        'categorias_dict': categorias_dict,
    }
    return render(request, 'financeiro/index.html', contexto)


@login_required
def alternar_fechamento_mes_view(request, familiar_id, ano, mes):
    familiar = get_object_or_404(Familiar, pk=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO', papel='GESTOR').first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem bloquear ou reabrir competências.")
        return redirect('dashboard', familiar_id=familiar.id)

    fechamento, _ = FechamentoMes.objects.get_or_create(
        familiar=familiar,
        mes=mes,
        ano=ano
    )
    fechamento.fechado = not fechamento.fechado
    fechamento.fechado_por = request.user
    fechamento.fechado_em = timezone.now() if fechamento.fechado else None
    fechamento.save()

    status_str = "fechada" if fechamento.fechado else "reaberta"
    messages.success(request, f"Competência {mes:02d}/{ano} {status_str} com sucesso.")
    return redirect(f"/dashboard/{familiar.id}/?mes={mes}&ano={ano}")


@login_required
def alternar_arquivamento_familiar_view(request, familiar_id):
    familiar = get_object_or_404(Familiar, pk=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO', papel='GESTOR').first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem arquivar ou desarquivar.")
        return redirect('dashboard', familiar_id=familiar.id)

    familiar.ativo = not familiar.ativo
    familiar.save()

    estado = "arquivado" if not familiar.ativo else "desarquivado"
    messages.success(request, f"Familiar '{familiar.nome}' {estado} com sucesso.")
    return redirect('dashboard', familiar_id=familiar.id)


@login_required
def exportar_csv_view(request, familiar_id):
    familiar = get_object_or_404(Familiar, pk=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO').first()

    if not vinculo:
        messages.error(request, "Acesso não autorizado.")
        return redirect('meus_familiares')

    hoje = date.today()
    try:
        mes_filtro = int(request.GET.get('mes', hoje.month))
    except (ValueError, TypeError):
        mes_filtro = hoje.month

    try:
        ano_filtro = int(request.GET.get('ano', hoje.year))
    except (ValueError, TypeError):
        ano_filtro = hoje.year

    transacoes = Transacao.objects.filter(
        familiar=familiar,
        ativo=True,
        data__year=ano_filtro,
        data__month=mes_filtro
    ).select_related('categoria', 'usuario').order_by('data')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="extrato_{familiar.nome}_{mes_filtro:02d}_{ano_filtro}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Data', 'Tipo', 'Descrição', 'Categoria', 'Valor (R$)', 'Comprador', 'Forma de Pagamento'])

    for t in transacoes:
        writer.writerow([
            t.data.strftime('%d/%m/%Y'),
            t.get_tipo_display(),
            t.descricao,
            t.categoria.nome if t.categoria else '-',
            f"{t.valor:.2f}".replace('.', ','),
            t.comprador or '-',
            t.get_forma_pagamento_display(),
        ])

    return response


@login_required
def exportar_pdf_view(request, familiar_id):
    familiar = get_object_or_404(Familiar, pk=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO').first()

    if not vinculo:
        messages.error(request, "Acesso não autorizado.")
        return redirect('meus_familiares')

    hoje = date.today()
    try:
        mes_filtro = int(request.GET.get('mes', hoje.month))
    except (ValueError, TypeError):
        mes_filtro = hoje.month

    try:
        ano_filtro = int(request.GET.get('ano', hoje.year))
    except (ValueError, TypeError):
        ano_filtro = hoje.year

    transacoes = Transacao.objects.filter(
        familiar=familiar,
        ativo=True,
        data__year=ano_filtro,
        data__month=mes_filtro
    ).select_related('categoria', 'usuario').order_by('data')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    styles = getSampleStyleSheet()

    titulo = Paragraph(f"<b>Extrato Financeiro - {familiar.nome}</b>", styles['Title'])
    subtitulo = Paragraph(f"Competência: {mes_filtro:02d}/{ano_filtro} | Emitido em: {hoje.strftime('%d/%m/%Y')}", styles['Normal'])
    elementos.extend([titulo, subtitulo, Spacer(1, 15)])

    dados_tabela = [['Data', 'Tipo', 'Descrição', 'Categoria', 'Valor (R$)', 'Comprador']]
    for t in transacoes:
        dados_tabela.append([
            t.data.strftime('%d/%m/%Y'),
            t.get_tipo_display(),
            t.descricao[:25],
            t.categoria.nome if t.categoria else '-',
            f"{t.valor:.2f}".replace('.', ','),
            t.comprador or '-'
        ])

    tabela = Table(dados_tabela, colWidths=[65, 60, 150, 95, 75, 95])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e1b4b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    elementos.append(tabela)

    doc.build(elementos)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_{familiar.nome}_{mes_filtro:02d}_{ano_filtro}.pdf"'
    return response


@login_required
def criar_categoria_view(request, familiar_id):
    familiar = get_object_or_404(Familiar, pk=familiar_id)
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO').first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem gerir categorias.")
        return redirect('dashboard', familiar_id=familiar.id)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', 'DESPESA')
        cor = request.POST.get('cor', '#6366f1')
        icone = request.POST.get('icone', 'tag')

        if nome:
            Categoria.objects.create(
                familiar=familiar,
                nome=nome,
                tipo=tipo,
                cor=cor,
                icone=icone
            )
            messages.success(request, f"Categoria '{nome}' criada com sucesso!")
        else:
            messages.error(request, "O nome da categoria não pode estar vazio.")

    return redirect('dashboard', familiar_id=familiar.id)


@login_required
def excluir_categoria_view(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    familiar = categoria.familiar
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO' ).first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem remover categorias.")
        return redirect('dashboard', familiar_id=familiar.id)

    if request.method == 'POST':
        categoria.delete()
        messages.success(request, "Categoria removida com sucesso!")

    return redirect('dashboard', familiar_id=familiar.id)


@login_required
def editar_transacao_view(request, transacao_id):
    transacao = get_object_or_404(Transacao, pk=transacao_id)
    familiar = transacao.familiar
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO').first()

    if not vinculo:
        messages.error(request, "Acesso não autorizado.")
        return redirect('meus_familiares')

    fechamento = FechamentoMes.objects.filter(
        familiar=familiar,
        mes=transacao.data.month,
        ano=transacao.data.year
    ).first()

    if fechamento and fechamento.fechado:
        messages.error(request, "Esta competência está fechada. A transação não pode ser modificada.")
        return redirect('dashboard', familiar_id=familiar.id)

    if request.method == 'POST':
        form = TransacaoForm(request.POST, request.FILES, instance=transacao, familiar=familiar)
        if form.is_valid():
            form.save()
            LogAuditoria.objects.create(
                transacao=transacao,
                usuario=request.user,
                acao='EDICAO',
                detalhes="Transação editada."
            )
            messages.success(request, "Transação atualizada com sucesso!")
            return redirect(f"/dashboard/{familiar.id}/?mes={transacao.data.month}&ano={transacao.data.year}")
    else:
        form = TransacaoForm(instance=transacao, familiar=familiar)

    return render(request, 'financeiro/editar_transacao.html', {'form': form, 'transacao': transacao})


@login_required
def excluir_transacao_view(request, transacao_id):
    transacao = get_object_or_404(Transacao, pk=transacao_id)
    familiar = transacao.familiar
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO').first()

    if not vinculo:
        messages.error(request, "Acesso não autorizado.")
        return redirect('meus_familiares')

    mes = transacao.data.month
    ano = transacao.data.year

    fechamento = FechamentoMes.objects.filter(familiar=familiar, mes=mes, ano=ano).first()
    if fechamento and fechamento.fechado:
        messages.error(request, "Esta competência está fechada. A transação não pode ser removida.")
        return redirect(f"/dashboard/{familiar.id}/?mes={mes}&ano={ano}")

    if request.method == 'POST':
        transacao.ativo = False
        transacao.save()

        LogAuditoria.objects.create(
            transacao=transacao,
            usuario=request.user,
            acao='EXCLUSAO',
            detalhes=f"Lançamento '{transacao.descricao}' (R$ {transacao.valor}) movido para a lixeira."
        )
        messages.success(request, "Lançamento movido para a lixeira com sucesso!")

    return redirect(f"/dashboard/{familiar.id}/?mes={mes}&ano={ano}")


@login_required
def restaurar_transacao_view(request, transacao_id):
    transacao = get_object_or_404(Transacao, pk=transacao_id)
    familiar = transacao.familiar
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO', papel='GESTOR').first()

    if not vinculo:
        messages.error(request, "Apenas gestores podem restaurar lançamentos eliminados.")
        return redirect('dashboard', familiar_id=familiar.id)

    transacao.ativo = True
    transacao.save()

    LogAuditoria.objects.create(
        transacao=transacao,
        usuario=request.user,
        acao='EDICAO',
        detalhes=f"Lançamento '{transacao.descricao}' restaurado pelo gestor."
    )
    messages.success(request, f"Lançamento '{transacao.descricao}' restaurado com sucesso!")
    return redirect(f"/dashboard/{familiar.id}/?mes={transacao.data.month}&ano={transacao.data.year}")


@login_required
def perfil_view(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
    form_perfil = EditarPerfilForm(instance=request.user)
    form_senha = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'atualizar_perfil' in request.POST:
            email_banco = User.objects.filter(pk=request.user.pk).values_list('email', flat=True).first() or ''
            email_banco = email_banco.strip().lower()

            form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=request.user)
            if form_perfil.is_valid():
                novo_email = form_perfil.cleaned_data.get('email', '').strip().lower()

                usuario_salvo = form_perfil.save(commit=False)
                usuario_salvo.email = email_banco
                usuario_salvo.save()

                foto = form_perfil.cleaned_data.get('foto')
                if foto:
                    perfil.foto = foto
                    perfil.save()

                if novo_email and novo_email != email_banco:
                    request.session['novo_email_pendente'] = novo_email
                    try:
                        enviar_email_codigo_verificacao(request.user, novo_email, 'ALTERACAO_EMAIL')
                        messages.info(request, f"Enviamos um código de 6 dígitos para {novo_email}. Digite-o abaixo para confirmar a alteração.")
                        return redirect('confirmar_novo_email')
                    except Exception as e:
                        messages.error(request, f"Não foi possível enviar o código para o novo e-mail: {str(e)}")
                        return redirect('perfil')

                messages.success(request, "Perfil atualizado com sucesso!")
                return redirect('perfil')
            else:
                for campo, erros in form_perfil.errors.items():
                    for erro in erros:
                        messages.error(request, erro)

        elif 'remover_foto' in request.POST:
            if perfil.foto:
                perfil.foto.delete(save=True)
                messages.success(request, "Fotografia removida com sucesso!")
            return redirect('perfil')

        elif 'alterar_senha' in request.POST:
            form_senha = PasswordChangeForm(user=request.user, data=request.POST)
            if form_senha.is_valid():
                user = form_senha.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Palavra-passe alterada com sucesso!")
                return redirect('perfil')
            else:
                for erros in form_senha.errors.values():
                    for erro in erros:
                        messages.error(request, erro)

    contexto = {
        'form_perfil': form_perfil,
        'form_senha': form_senha,
        'perfil': perfil,
    }
    return render(request, 'financeiro/perfil.html', contexto)


@login_required
def detalhes_transacao_excluida_view(request, transacao_id):
    transacao = get_object_or_404(Transacao, pk=transacao_id)
    familiar = transacao.familiar
    vinculo = VinculoFamiliar.objects.filter(usuario=request.user, familiar=familiar, status='APROVADO', papel='GESTOR').first()

    if not vinculo:
        return JsonResponse({'erro': 'Acesso não autorizado.'}, status=403)

    dados = {
        'id': transacao.id,
        'descricao': transacao.descricao,
        'valor': f"{transacao.valor:.2f}".replace('.', ','),
        'tipo': transacao.get_tipo_display(),
        'tipo_raw': transacao.tipo,
        'data': transacao.data.strftime('%d/%m/%Y'),
        'categoria': transacao.categoria.nome if transacao.categoria else 'Sem Categoria',
        'comprador': transacao.comprador or 'Não informado',
        'forma_pagamento': transacao.get_forma_pagamento_display(),
        'observacoes': transacao.observacoes or 'Nenhuma observação informada.',
        'usuario': transacao.usuario.first_name or transacao.usuario.username,
        'comprovante_url': transacao.comprovante.url if hasattr(transacao, 'comprovante') and transacao.comprovante else None,
        'url_restaurar': f"/transacao/{transacao.id}/restaurar/",
    }
    return JsonResponse(dados)


@login_required
def confirmar_novo_email_view(request):
    novo_email = request.session.get('novo_email_pendente')
    if not novo_email:
        messages.error(request, "Nenhuma solicitação de alteração de e-mail pendente.")
        return redirect('perfil')

    if request.method == 'POST':
        codigo_digitado = request.POST.get('codigo', '').strip()
        
        codigo_obj = CodigoVerificacaoEmail.objects.filter(
            usuario=request.user,
            email=novo_email,
            codigo=codigo_digitado,
            finalidade='ALTERACAO_EMAIL',
            utilizado=False
        ).order_by('-criado_em').first()

        if codigo_obj and codigo_obj.esta_valido():
            codigo_obj.utilizado = True
            codigo_obj.save()

            request.user.email = novo_email
            request.user.save()

            del request.session['novo_email_pendente']
            messages.success(request, "E-mail alterado e validado com sucesso!")
            return redirect('perfil')
        else:
            messages.error(request, "Código incorreto ou expirado. Verifique e tente novamente.")

    return render(request, 'financeiro/confirmar_novo_email.html', {'novo_email': novo_email})


@login_required
def reenviar_codigo_novo_email_view(request):
    novo_email = request.session.get('novo_email_pendente')
    if not novo_email:
        messages.error(request, "Nenhuma solicitação pendente.")
        return redirect('perfil')

    try:
        enviar_email_codigo_verificacao(request.user, novo_email, 'ALTERACAO_EMAIL')
        messages.success(request, f"Novo código reenviado para {novo_email}!")
    except Exception as e:
        messages.error(request, f"Erro ao reenviar o código: {str(e)}")

    return redirect('confirmar_novo_email')